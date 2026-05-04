import logging
from datetime import datetime, timezone
from typing import Any

from pymongo import MongoClient
from pymongo.errors import PyMongoError
from rq.job import Job

from ..services.rediz import g_rdb
from ..utils import g_config, mask_sensitive_data
from ..utils.logger import setup_logging
from .common import RedisWorker

log = logging.getLogger(__name__)

# Module-level MongoDB client shared across all archiver functions in this process.
# Initialized lazily on first use; validated eagerly by ArchiverWorker before listening.
_mongo_client: MongoClient | None = None
PRUNE_BATCH_SIZE = 1000


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
    collection = db[c_name]
    collection.insert_one(doc)
    if c_name == g_config.mongodb.collection:
        _prune_collection_by_count(collection, g_config.mongodb.max_documents)


def _ensure_ttl_index(collection, field: str, retention_days: int) -> bool:
    """Create or update a TTL index without requiring operators to drop indexes manually."""
    if retention_days <= 0:
        return True

    expire_after_seconds = retention_days * 24 * 60 * 60
    index_name = f"{field}_1"
    try:
        existing = next(
            (idx for idx in collection.list_indexes() if idx.get("key") == {field: 1}),
            None,
        )

        if existing:
            if existing.get("expireAfterSeconds") == expire_after_seconds:
                return True
            collection.database.command(
                {
                    "collMod": collection.name,
                    "index": {
                        "keyPattern": {field: 1},
                        "expireAfterSeconds": expire_after_seconds,
                    },
                }
            )
            return True

        collection.create_index(field, name=index_name, expireAfterSeconds=expire_after_seconds)
        return True
    except PyMongoError as e:
        log.warning(
            "Could not ensure TTL index %s on %s: %s. Audit writes will continue.",
            index_name,
            collection.name,
            e,
        )
        return False


def _ensure_index(collection, keys: str, **kwargs) -> bool:
    try:
        collection.create_index(keys, **kwargs)
        return True
    except PyMongoError as e:
        log.warning(
            "Could not ensure MongoDB index on %s.%s: %s. Audit writes will continue.",
            collection.name,
            keys,
            e,
        )
        return False


def _prune_collection_by_count(
    collection,
    max_documents: int,
    batch_size: int = PRUNE_BATCH_SIZE,
) -> None:
    """Keep the newest audit records when a collection grows beyond its configured cap."""
    if max_documents <= 0 or batch_size <= 0:
        return

    try:
        count = collection.estimated_document_count()
    except PyMongoError as e:
        log.warning("Could not count MongoDB audit records for pruning: %s", e)
        return

    overage = count - max_documents
    if overage <= 0:
        return

    limit = min(overage, batch_size)
    try:
        ids = [
            doc["_id"]
            for doc in collection.find({}, {"_id": 1})
            .sort("created_at", 1)
            .limit(limit)
        ]
        if ids:
            result = collection.delete_many({"_id": {"$in": ids}})
            log.warning(
                "Pruned %s old MongoDB audit records from %s to enforce max_documents=%s.",
                result.deleted_count,
                collection.name,
                max_documents,
            )
    except PyMongoError as e:
        log.warning("Could not prune MongoDB audit records from %s: %s", collection.name, e)


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
            audit_collection = db[g_config.mongodb.collection]
            detached_collection = db[g_config.mongodb.detached_collection]
            _ensure_index(audit_collection, "job_id", unique=True)
            _ensure_ttl_index(
                audit_collection,
                "created_at",
                g_config.mongodb.retention_days,
            )
            _ensure_index(detached_collection, "task_id")
            _ensure_ttl_index(
                detached_collection,
                "recorded_at",
                g_config.mongodb.detached_retention_days,
            )

            log.info("Successfully connected to MongoDB and checked indexes.")
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


def _get_job_audit_mode(job: Job, audit_mode: str | None = None) -> str:
    if audit_mode:
        return audit_mode

    req = job.kwargs.get("req") if getattr(job, "kwargs", None) else None
    if req is not None:
        return getattr(req, "audit_mode", "full")

    if isinstance(getattr(job, "meta", None), dict):
        req_payload = job.meta.get("req_payload")
        if isinstance(req_payload, dict):
            return req_payload.get("audit_mode", "full")

    return "full"


def process_audit_log(job_id: str, result: Any, audit_mode: str | None = None):
    """
    Called by the ArchiverWorker to persist a job audit record to MongoDB.
    `result` is already serialized to plain Python types by rpc_audit_callback.
    """
    try:
        job = Job.fetch(job_id, connection=g_rdb.conn)
        effective_audit_mode = _get_job_audit_mode(job, audit_mode)
        if effective_audit_mode == "none":
            log.info(f"Audit log for job {job_id} skipped by audit_mode=none.")
            return

        doc = {
            "job_id": job.id,
            "status": str(job.get_status()),
            "created_at": datetime.now(timezone.utc),
            "audit_mode": effective_audit_mode,
            "metrics": {
                "enqueued_at": job.enqueued_at,
                "started_at": job.started_at,
                "ended_at": job.ended_at,
            },
        }

        if effective_audit_mode == "full":
            doc["result"] = mask_sensitive_data(result)

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
