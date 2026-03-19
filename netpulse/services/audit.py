import logging
from typing import Any

from rq import Queue
from rq.job import Job

from ..utils import g_config

log = logging.getLogger(__name__)


def rpc_audit_callback(job: Job, connection: Any, *args, **kwargs):
    """
    Hook executed when an RPC job finishes (success or failure).
    Pushes a serialized audit record to AuditLogQ for async persistence to MongoDB.

    RQ success signature: callback(job, connection, return_value)
    RQ failure signature: callback(job, connection, exc_type, exc_value, traceback)
    """
    if not g_config.mongodb.enabled:
        return

    try:
        if len(args) == 1:
            # Success path — args[0] is the job return value
            raw_result = args[0]
            is_success = True
        elif len(args) == 3:
            # Failure path — args are (exc_type, exc_value, traceback)
            exc_type, exc_value, _ = args
            raw_result = f"{exc_type.__name__}: {exc_value}"
            is_success = False
        else:
            raw_result = None
            is_success = True

        # Serialize result to plain Python types so it survives RQ pickle transport
        # and BSON insertion in the archiver.
        if is_success and isinstance(raw_result, list):
            serialized_result = [
                r.model_dump(mode="json") if hasattr(r, "model_dump") else str(r)
                for r in raw_result
            ]
        elif is_success and hasattr(raw_result, "model_dump"):
            serialized_result = raw_result.model_dump(mode="json")
        else:
            # str (failure message) or None
            serialized_result = raw_result

        # Use the connection provided by RQ, not the global g_rdb singleton.
        # Pass job_id and result as positional args — NOT kwargs — because RQ
        # treats `job_id` as a special enqueue parameter that sets the job's Redis key.
        audit_queue = Queue("AuditLogQ", connection=connection)
        audit_queue.enqueue(
            "netpulse.worker.archiver.process_audit_log",
            job.id,
            serialized_result,
        )
        log.debug(f"Job {job.id} audit log enqueued to AuditLogQ (success={is_success})")
    except Exception as e:
        log.error(f"Failed to enqueue audit log for job {job.id}: {e}")
