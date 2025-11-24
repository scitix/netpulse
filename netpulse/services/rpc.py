"""
Manager enqueues these functions into RQ,
then they are executed by Workers.
"""

import logging
from typing import Callable, Optional

from pydantic import ValidationError
from rq.job import Callback, Job

from ..models import JobAdditionalData
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
            if not isinstance(payload, dict):
                raise ValueError("Config/command must be a dict for rendering.")

            if req.rendering.context:
                req.rendering.context = None
                log.warning("Context in request is overridden by config/command.")

            # Do the rendering
            render = renderers[req.rendering.name].from_rendering_request(req.rendering)
            payload = render.render(payload)

            # After payload is rendered, payload should be a str or list[str]
            # Besides, we need to delete the rendering field
            req.rendering = None
        except Exception as e:
            log.error(f"Error in rendering: {e}")
            raise e

    if isinstance(payload, str):
        payload = [payload]
    assert isinstance(payload, list), "Config/command must be str/list[str] after rendering."

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
        log.error(f"Error in sending config/command: {e}")
        raise e
    finally:
        if session:
            dobj.disconnect(session)

    # Parsing after result is obtained
    if req.parsing:
        try:
            if not isinstance(result, dict):
                raise ValueError("Result must be a dict for parsing.")

            if req.parsing.context:
                req.parsing.context = None
                log.warning("Context in request is overridden by output.")

            parser = parsers[req.parsing.name].from_parsing_request(req.parsing)
            for cmd in result.keys():
                result[cmd] = parser.parse(result[cmd])
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
