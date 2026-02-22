"""
Manager enqueues these functions into RQ,
then they are executed by Workers.
"""

import logging
import os
import time
import uuid
from typing import Callable, Optional

from pydantic import ValidationError
from rq import get_current_job
from rq.job import Callback, Job

from ..models import JobAdditionalData, QueueStrategy
from ..models.driver import DriverExecutionResult
from ..models.request import ExecutionRequest
from ..plugins import drivers, parsers, renderers, webhooks
from ..services.rediz import g_detached_task_registry
from ..worker.node import start_pinned_worker

log = logging.getLogger(__name__)


def manage_detached_task(
    task_id: str, action: str, params: Optional[dict] = None, req: Optional[ExecutionRequest] = None
):
    """
    Synchronous detached task management RPC.
    Actions: query, kill
    """
    from .rediz import g_detached_task_registry

    meta = g_detached_task_registry.get(task_id)
    if not meta:
        raise ValueError(f"Task {task_id} not found in registry")

    # Reconstruct request to init driver
    req = ExecutionRequest(
        driver=meta["driver"],
        connection_args=meta["connection_args"],
        command="",  # Placeholder
        queue_strategy=QueueStrategy.FIFO,  # management is usually FIFO
    )

    dobj = drivers[req.driver].from_execution_request(req)
    session = None
    try:
        session = dobj.connect()
        if action == "query":
            offset = params.get("offset", 0) if params else 0
            return dobj._read_logs(session, task_id, offset)
        elif action == "kill":
            return dobj.kill_task(session, task_id)
        else:
            raise ValueError(f"Unknown management action: {action}")
    finally:
        if session:
            try:
                dobj.disconnect(session)
            except Exception:
                pass


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

    # Pass Job ID to request for driver use
    job = get_current_job()
    if job:
        # Pydantic models with extra="allow" allow setting new attributes
        req.id = job.id
    else:
        req.id = str(uuid.uuid4())

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

        # Detached lifecycle
        if req.detach and not req.config:
            # Check if task_id is pre-allocated in job meta
            job = get_current_job()
            task_id = job.meta.get("task_id") if job else None

            if not task_id:
                task_id = str(uuid.uuid4())[:12]

            log.info(f"Launching detached task {task_id} on {req.connection_args.host}")

            if not hasattr(dobj, "launch_detached"):
                raise NotImplementedError(f"Driver {req.driver} does not support detached mode.")

            # Driver launches the process independently
            # If command list is empty, pass empty string;
            # driver may check args (script_content, etc.)
            primary_cmd = payload[0] if (payload and isinstance(payload, list)) else ""
            result = dobj.launch_detached(session, primary_cmd, task_id)

            is_running = True
            if "launch" in result and result["launch"].telemetry:
                is_running = result["launch"].telemetry.get("running", True)

            # Register in Redis for global tracking
            meta = {
                "task_id": task_id,
                "command": req.command,
                "host": req.connection_args.host,
                "driver": req.driver,
                "worker_id": None,  # Will be updated if push_interval is set
                "push_interval": req.push_interval,
                "webhook": req.webhook.model_dump(mode="json") if req.webhook else None,
                "connection_args": req.connection_args.model_dump(mode="json"),
                "last_sync": time.time(),
                "created_at": time.time(),
                "status": "running" if is_running else "completed",
            }
            g_detached_task_registry.register(task_id, meta)
            return result

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


def rpc_cleanup_handler(job: Job):
    """
    Cleanup staged files associated with the job.
    """
    req = job.kwargs.get("req")
    if not req:
        return

    # staged_file_id could be in model or dict
    staged_file_id = getattr(req, "staged_file_id", None)
    if not staged_file_id and isinstance(req, dict):
        staged_file_id = req.get("staged_file_id")

    if staged_file_id and os.path.exists(staged_file_id):
        try:
            os.remove(staged_file_id)
            log.info(f"Success/Failure: Cleaned up staged file: {staged_file_id}")
        except Exception as e:
            log.warning(f"Failed to cleanup staged file {staged_file_id}: {e}")


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
    job = args[0]
    rpc_cleanup_handler(job)

    if len(args) == 3:
        # succeeded
        job, _, ret = args
        result = ret
        is_success = True
    elif len(args) == 5:
        # failed, will call rpc_exception_handler at first
        job = args[0]
        result = rpc_exception_callback(*args)
        result = result.error if result else "Unknown Error"
        is_success = False
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

    if req.webhook is not None:
        try:
            wobj = webhooks[req.webhook.name](req.webhook)
            # For detached tasks, we want the Webhook ID to be the Task ID for consistency
            if req.detach:
                from ..models.response import JobInResponse

                job_resp = JobInResponse.from_job(job)

                # The task_id is stored in job.meta
                task_id = job.meta.get("task_id") if job.meta else None
                job_resp.id = task_id or job.id

                wobj.call(req=req, job=job_resp, result=result, is_success=is_success)
            else:
                wobj.call(req=req, job=job, result=result, is_success=is_success)
        except Exception as e:
            log.warning(f"Error in webhook execution: {e}")
            raise e

    # --- New: Transform Local Paths to Download URLs ---
    if is_success and isinstance(result, dict):
        from ..utils import g_config

        staging_dir = str(g_config.storage.staging)
        download_base = os.path.join(staging_dir, "downloads")

        for res in result.values():
            if hasattr(res, "telemetry") and isinstance(res.telemetry, dict):
                xfer = res.telemetry.get("transfer_result")
                if isinstance(xfer, dict) and "local_path" in xfer:
                    local_path = xfer["local_path"]
                    if local_path.startswith(download_base):
                        # It's a staged download, generate a URL
                        file_id = os.path.relpath(local_path, download_base)
                        # We use the host from the request or config
                        base_url = f"http://{g_config.server.host}:{g_config.server.port}"
                        xfer["download_url"] = f"{base_url}/storage/fetch/{file_id}"
                        log.info(f"Generated download URL for job {job.id}: {xfer['download_url']}")

    # --- New Detach Registry Sync ---
    # If this was a detached task query/execution, update the registry with next_offset
    if req.detach:
        try:
            from .rediz import g_detached_task_registry

            # result is a dict of {cmd: DriverExecutionResult}
            # For management query, it has only one key
            for val in result.values():
                if hasattr(val, "telemetry") and "task_id" in val.telemetry:
                    task_id = val.telemetry["task_id"]
                    next_offset = val.telemetry.get("next_offset")
                    completed = val.telemetry.get("completed", False)

                    meta = g_detached_task_registry.get(task_id)
                    if meta:
                        if next_offset is not None:
                            meta["last_offset"] = next_offset
                        meta["last_sync"] = time.time()

                        if completed:
                            meta["status"] = "completed"
                        else:
                            meta["status"] = "running"

                        g_detached_task_registry.register(task_id, meta)
                    break
        except Exception as e:
            log.warning(f"Error in updating detach registry: {e}")
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
