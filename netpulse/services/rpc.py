"""
Manager enqueues these functions into RQ,
then they are executed by Workers.
"""

import logging
from typing import Callable, Optional

from pydantic import ValidationError
from rq.job import Callback, Job

from ..models import JobAdditionalData
from ..models.request import PullingRequest, PushingRequest
from ..plugins import drivers, parsers, renderers, webhooks
from ..worker.node import start_pinned_worker

log = logging.getLogger(__name__)


def pull(req: PullingRequest):
    if isinstance(req.command, str):
        cmds = [req.command]
    else:
        cmds = req.command

    if not drivers.get(req.driver):
        raise NotImplementedError(f"Unknown 'driver' {req.driver}")

    # Init the driver
    try:
        dobj = drivers[req.driver].from_pulling_request(req)
    except Exception as e:
        log.error(f"Error in initializing driver: {e}")
        raise e

    # Do the work
    session = None
    try:
        session = dobj.connect()
        result = dobj.send(session, cmds)
        dobj.disconnect(session)
    except Exception as e:
        log.error(f"Error in sending command: {e}")
        raise e
    finally:
        if session:
            dobj.disconnect(session)

    if req.parsing:
        try:
            if not isinstance(result, dict):
                raise ValueError("Result must be a dict for parsing.")

            if req.parsing.context:
                req.parsing.context = None
                log.warning("Context in request is discarded.")

            parser = parsers[req.parsing.name].from_parsing_request(req.parsing)
            for cmd in result.keys():
                result[cmd] = parser.parse(result[cmd])
        except Exception as e:
            log.error(f"Error in parsing: {e}")
            raise e

    return result


def push(req: PushingRequest):
    if not drivers.get(req.driver):
        raise NotImplementedError(f"Unknown 'driver' {req.driver}")

    # Handle template rendering if specified
    if req.rendering:
        try:
            if not isinstance(req.config, dict):
                raise ValueError("Config must be a dict for rendering.")

            if req.rendering.context:
                req.rendering.context = None
                log.warning("Context in request is discarded")

            render = renderers[req.rendering.name].from_rendering_request(req.rendering)
            req.config = render.render(req.config)

            # After req.config is rendered, we need to delete the rendering field
            req.rendering = None
        except Exception as e:
            log.error(f"Error in rendering: {e}")
            raise e

    if isinstance(req.config, dict):
        raise ValueError("Config must be a list[str] or str when not using rendering.")

    if isinstance(req.config, str):
        config = [req.config]
    else:
        config = req.config

    # Init the driver
    try:
        dobj = drivers[req.driver].from_pushing_request(req)
    except Exception as e:
        log.error(f"Error in initializing driver: {e}")
        raise e

    session = None
    try:
        session = dobj.connect()
        result = dobj.config(session, config)
        dobj.disconnect(session)
    except Exception as e:
        log.error(f"Error in sending config: {e}")
        raise e
    finally:
        if session:
            dobj.disconnect(session)

    return result


def spawn(q_name: str, host: str):
    """
    Start a worker that is pinned to a specific queue.
    """
    start_pinned_worker(q_name=q_name, host=host)


def rpc_callback_factory(func: Callable, timeout: Optional[float] = None):
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
        result = result.error
    else:
        # Should never happen
        log.warning("Webhook handler is called with unexpected args.")
        return

    # To cut down Redis memory usage, we get req from job.kwargs,
    # which is not elegant, but it is a trade-off.
    req = job.kwargs.get("req", None)  # type: PullingRequest | PushingRequest
    if req is None:
        log.warning("Webhook handler is called without `req` in job.kwargs.")
        return

    try:
        wobj = webhooks[req.webhook.name](req.webhook)
        wobj.call(req=req, job=job, result=result)
    except Exception as e:
        log.warning(f"Error in initializing webhooks: {e}")
        raise e


def rpc_exception_callback(
    job: Job, conn, exc_type: type[BaseException], exc_value: BaseException, tb
) -> JobAdditionalData:
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

    assert meta is not None
    meta.error = (exc_type.__name__, str(exc_value))

    job.meta = meta.model_dump()
    job.save_meta()

    return meta
