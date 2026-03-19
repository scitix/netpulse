import logging
from datetime import datetime, timezone
from typing import Any

from pymongo import MongoClient
from rq.job import Job

from ..services.rediz import g_rdb
from ..utils import g_config, mask_sensitive_data
from ..utils.logger import setup_logging
from .common import RedisWorker

log = logging.getLogger(__name__)

# Module-level MongoDB client shared across all archiver functions in this process.
# Initialized lazily on first use; validated eagerly by ArchiverWorker before listening.
_mongo_client: MongoClient | None = None


def _get_mongo_client() -> MongoClient:
    """Return the module-level MongoDB client, creating it if needed."""
    global _mongo_client
    if _mongo_client is None:
        _mongo_client = MongoClient(g_config.mongodb.uri, serverSelectionTimeoutMS=5000)
    return _mongo_client


def _write_to_mongo(doc: dict, collection_name: str | None = None) -> None:
    client = _get_mongo_client()
    db = client[g_config.mongodb.database]
    c_name = collection_name or g_config.mongodb.collection
    db[c_name].insert_one(doc)


class ArchiverWorker(RedisWorker):
    def __init__(self):
        super().__init__()
        self.name = f"archiver-{self.hostname}"

    def _init_mongo(self):
        """Validate MongoDB connectivity and ensure indexes before the worker starts listening."""
        try:
            log.info(f"Connecting to MongoDB at {g_config.mongodb.uri}")
            client = _get_mongo_client()
            client.server_info()

            # Ensure indexes
            db = client[g_config.mongodb.database]
            db[g_config.mongodb.collection].create_index("job_id", unique=True)
            db[g_config.mongodb.collection].create_index("created_at")
            db[g_config.mongodb.detached_collection].create_index("task_id")
            db[g_config.mongodb.detached_collection].create_index("recorded_at")

            log.info("Successfully connected to MongoDB and ensured indexes.")
        except Exception as e:
            log.error(f"Failed to connect to MongoDB or ensure indexes: {e}")
            raise

    def listen(self):
        if not g_config.mongodb.enabled:
            log.info("MongoDB is disabled — archiver-worker exiting cleanly.")
            return
        try:
            self._init_mongo()
        except Exception:
            log.info("MongoDB is unreachable — archiver-worker exiting cleanly.")
            return
        super().listen("AuditLogQ")


def process_audit_log(job_id: str, result: Any):
    """
    Called by the ArchiverWorker to persist a job audit record to MongoDB.
    `result` is already serialized to plain Python types by rpc_audit_callback.
    """
    try:
        job = Job.fetch(job_id, connection=g_rdb.conn)

        doc = {
            "job_id": job.id,
            "status": str(job.get_status()),
            "created_at": datetime.now(timezone.utc),
            "result": mask_sensitive_data(result),
            "metrics": {
                "enqueued_at": job.enqueued_at,
                "started_at": job.started_at,
                "ended_at": job.ended_at,
            },
        }

        if job.meta:
            doc["device_name"] = job.meta.get("device_name")
            doc["command"] = job.meta.get("command")

        req = job.kwargs.get("req")
        if req:
            req_dict = req.model_dump(mode="json") if hasattr(req, "model_dump") else req
            doc["request"] = mask_sensitive_data(req_dict)

        if job.started_at and job.ended_at:
            doc["metrics"]["duration_seconds"] = (job.ended_at - job.started_at).total_seconds()

        _write_to_mongo(doc)
        log.info(f"Audit log for job {job_id} persisted to MongoDB.")

    except Exception as e:
        log.error(f"Error processing audit log for job {job_id}: {e}")
        raise


def process_detached_audit(task_id: str, metadata: dict, **kwargs):
    """
    Called by ArchiverWorker to record a detached task lifecycle event.
    Only invoked on meaningful status transitions (not every offset update).
    """
    try:
        doc = {
            "task_id": task_id,
            "type": "detached_lifecycle",
            "metadata": mask_sensitive_data(metadata),
            "recorded_at": datetime.now(timezone.utc),
        }
        if "job_id" in kwargs:
            doc["job_id"] = kwargs["job_id"]
        _write_to_mongo(doc, collection_name=g_config.mongodb.detached_collection)
        log.info(f"Detached task audit for {task_id} saved (status: {metadata.get('status')}).")
    except Exception as e:
        log.error(f"Error processing detached audit for {task_id}: {e}")


def main():
    setup_logging(g_config.log.config, g_config.log.level)
    worker = ArchiverWorker()
    worker.listen()
