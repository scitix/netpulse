"""
Manager enqueues these functions into RQ,
then they are executed by Workers.
"""

import logging
from typing import Callable, Optional

from pydantic import ValidationError
from rq.job import Callback, Job

from ..models import JobAdditionalData
from ..models.driver import DriverExecutionResult
from ..models.request import ExecutionRequest
from ..plugins import drivers, parsers, renderers, webhooks
from ..worker.node import start_pinned_worker

log = logging.getLogger(__name__)


def execute(req: ExecutionRequest):
    """
    Execute command on device.
    """
    if not drivers.get(req.driver):
        raise NotImplementedError(f"Unknown 'driver' {req.driver}")

    has_command = req.command is not None
    payload = req.config if req.config is not None else req.command

    # Render before execution if specified
    if req.rendering:
        try:
            if req.rendering.context is None:
                req.rendering.context = {}

            template_source = req.rendering.template

            if isinstance(payload, dict):
                # Merge payload into context (payload takes precedence)
                req.rendering.context.update(payload)
            elif template_source is None:
                # If payload is str/list, and rendering.template is missing, use payload as template
                if isinstance(payload, list):
                    template_source = "\n".join(payload)
                else:
                    template_source = payload

            if template_source is None:
                raise ValueError("Template source is required for rendering.")

            # Do the rendering
            # Pass the template_source to the renderer if it was missing in req.rendering
            render_req = req.rendering.model_copy(update={"template": template_source})
            render = renderers[req.rendering.name].from_rendering_request(render_req)
            payload = render.render(req.rendering.context)

            # Persist rendered payload back to request so downstream validation sees a concrete
            # command/config instead of the original dict + rendering metadata.
            if has_command:
                req.command = payload
            else:
                req.config = payload

            if req.driver_args:
                script_content = getattr(req.driver_args, "script_content", None)
                if isinstance(script_content, str) and script_content:
                    script_render_req = req.rendering.model_copy(
                        update={"template": script_content}
                    )
                    script_render = renderers[req.rendering.name].from_rendering_request(
                        script_render_req
                    )
                    req.driver_args.script_content = script_render.render(req.rendering.context)

            # After payload is rendered, payload should be a str or list[str]
            # Besides, we need to delete the rendering field
            req.rendering = None
        except Exception as e:
            log.error(f"Error in rendering: {e}")
            raise e

    if isinstance(payload, str):
        payload = [payload]
    assert isinstance(payload, list), "Config/command must be str/list[str] after rendering."

    # Keep the request payload in sync after normalization
    if has_command:
        req.command = payload
    else:
        req.config = payload

    # Init the driver
    try:
        dobj = drivers[req.driver].from_execution_request(req)
    except Exception as e:
        log.error(f"Error in initializing driver: {e}")
        raise e

    # Depend command or config, do config or send.
    session = None
    try:
        session = dobj.connect()
        if has_command:
            result = dobj.send(session, payload)
        else:
            result = dobj.config(session, payload)
        dobj.disconnect(session)
    except Exception as e:
        log.error(f"Error in connection or execution: {e}")
        error_key = "\n".join(payload) if isinstance(payload, list) else str(payload)
        result_data = {
            "pid": None,
            "running": False,
            "exit_code": None,
            "output_tail": None,
            "runtime_seconds": 0.0,
            "killed": False,
            "cleaned": False,
        }
        return {
            error_key: DriverExecutionResult(
                output="",
                error=str(e),
                exit_status=1,
                telemetry={"duration_seconds": 0.0},
                **result_data,
            )
        }
    finally:
        if session:
            try:
                dobj.disconnect(session)
            except Exception:
                pass

    # Parsing after result is obtained
    if req.parsing:
        try:
            if not isinstance(result, dict):
                raise ValueError("Result must be a dict for parsing.")

            if req.parsing.context:
                req.parsing.context = None
                log.warning("Context in request is overridden by output.")

            parser = parsers[req.parsing.name].from_parsing_request(req.parsing)
            for cmd, val in result.items():
                # If it's a rich object (output, error, etc.), parse only the output
                if hasattr(val, "output"):
                    val.parsed = parser.parse(val.output)
                elif isinstance(val, dict) and "output" in val:
                    val["parsed"] = parser.parse(val["output"])
                else:
                    # Backward compatibility for primitive drivers
                    result[cmd] = parser.parse(val)
        except Exception as e:
            log.error(f"Error in parsing: {e}")
            raise e

    return result


def spawn(q_name: str, host: str):
    """
    Start a worker that is pinned to a specific queue.
    """
    start_pinned_worker(q_name=q_name, host=host)


def rpc_callback_factory(func: Optional[Callable], timeout: Optional[float] = None):
    """
    NOTE: `rq` wraps callable into Callback object.
    When serialized, the function is lost, only the name is stored.
    The function is **solely** looked up by **name** in Worker.

    Besides, `rq` does not support passing arguments to the Callback.
    And it does not support chaining Callbacks. This limits the flexibility.
    """
    return (
        Callback(
            func=func,
            timeout=timeout,
        )
        if func
        else None
    )


def rpc_webhook_callback(*args):
    """
    If job has a webhook, this function is called when job succeeded / failed.

    This is called in two cases:
    - failed: args = (job, conn, exc_type, exc_value, tb)
    - succeeded: args = (job, conn, return_value)
    """
    if len(args) == 3:
        # succeeded
        job, _, ret = args
        result = ret
    elif len(args) == 5:
        # failed, will call rpc_exception_handler at first
        job = args[0]
        result = rpc_exception_callback(*args)
        result = result.error if result else "Unknown Error"
    else:
        # Should never happen
        log.warning("Webhook handler is called with unexpected args.")
        return

    # To cut down Redis memory usage, we get req from job.kwargs,
    # which is not elegant, but it is a trade-off.
    req: ExecutionRequest = job.kwargs.get("req", None)
    if req is None:
        log.warning("Webhook handler is called without `req` in job.kwargs.")
        return

    if req.webhook is None:
        log.error("Webhook handler is called without any webhook in request.")
        return

    try:
        wobj = webhooks[req.webhook.name](req.webhook)
        wobj.call(req=req, job=job, result=result)
    except Exception as e:
        log.warning(f"Error in initializing webhooks: {e}")
        raise e


def rpc_exception_callback(
    job: Job, conn, exc_type: type[BaseException], exc_value: BaseException, tb
) -> JobAdditionalData | None:
    """
    Handle exceptions that occur during RPC job execution.

    NOTE: If custom handler (e.g. webhook) is needed, it should
    call this handler first (See `rpc_callback_factory` ).
    """
    # rq.job.Result only record exc_string, which is undesirable.
    # We use job.meta to store exc_value.
    meta = None
    try:
        meta = JobAdditionalData.model_validate(job.meta)
    except ValidationError as e:
        log.error(f"Error in validating job metadata: {e}, skipping exception.")
        return None

    meta.error = (exc_type.__name__, str(exc_value))

    job.meta = meta.model_dump()
    job.save_meta()

    return meta
