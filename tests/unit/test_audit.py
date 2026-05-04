from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from pymongo.errors import OperationFailure

from netpulse.models import DriverConnectionArgs, DriverName
from netpulse.models.request import ExecutionRequest
from netpulse.services.audit import rpc_audit_callback
from netpulse.worker.archiver import (
    _ensure_ttl_index,
    _prune_collection_by_count,
    process_audit_log,
    process_detached_audit,
)


@pytest.fixture
def mock_mongo(monkeypatch):
    mock_client = MagicMock()
    mock_db = MagicMock()
    mock_collection = MagicMock()

    mock_client.__getitem__.return_value = mock_db
    mock_db.__getitem__.return_value = mock_collection
    mock_collection.estimated_document_count.return_value = 0

    # Patch the module-level client so _get_mongo_client() returns the mock,
    # and enable MongoDB so _write_to_mongo() doesn't short-circuit.
    with patch("netpulse.worker.archiver.MongoClient", return_value=mock_client), \
         patch("netpulse.worker.archiver._mongo_client", mock_client), \
         patch("netpulse.worker.archiver.g_config.mongodb.enabled", True):
        yield mock_collection


def test_rpc_audit_callback_enqueues(monkeypatch, unit_runtime):
    from rq import Queue

    class SimpleJob:
        id = "test-job-id"

    mock_job = SimpleJob()

    # Use unit_runtime.redis (the reloaded fakeredis conn) — the module-level g_rdb
    # import is stale after unit_runtime reloads netpulse.services.rediz.
    conn = unit_runtime.redis
    # Enable MongoDB so rpc_audit_callback doesn't short-circuit.
    with patch("netpulse.services.audit.g_config.mongodb.enabled", True):
        rpc_audit_callback(mock_job, conn, "test-result")

    # Verify it enqueued to AuditLogQ
    q = Queue("AuditLogQ", connection=conn)
    jobs = q.get_jobs()
    assert len(jobs) == 1
    job = jobs[0]
    assert job.func_name == "netpulse.worker.archiver.process_audit_log"

    # Check values — job_id and result are passed as positional args
    assert "test-job-id" in job.args
    assert "test-result" in job.args
    assert "full" in job.args


def test_execution_request_default_audit_mode_is_full(app_config):
    req = ExecutionRequest(
        driver=DriverName.PARAMIKO,
        connection_args=DriverConnectionArgs(host="10.0.0.1"),
        command="show version",
    )

    assert req.audit_mode == "full"


def test_rpc_audit_callback_skips_when_audit_mode_none(unit_runtime):
    from rq import Queue

    class SimpleJob:
        id = "test-job-id"
        kwargs = {"req": MagicMock(audit_mode="none")}

    conn = unit_runtime.redis
    with patch("netpulse.services.audit.g_config.mongodb.enabled", True):
        rpc_audit_callback(SimpleJob(), conn, "test-result")

    assert Queue("AuditLogQ", connection=conn).count == 0

def test_process_audit_log_persists(mock_mongo, monkeypatch, unit_runtime):
    # Mock Job.fetch
    mock_job = MagicMock()
    mock_job.id = "test-job-id"
    mock_job.origin = "test-q"
    mock_job.worker_name = "test-worker"
    mock_job.created_at = datetime(2024, 1, 1, 12, 0)
    mock_job.started_at = datetime(2024, 1, 1, 12, 1)
    mock_job.ended_at = datetime(2024, 1, 1, 12, 2)
    mock_job.get_status.return_value = "finished"
    mock_job.latest_result.return_value = "ok"
    mock_job.meta = {"device_name": "1.2.3.4", "command": "show version"}

    # Handle the fact that req might be in kwargs
    mock_req = MagicMock()
    mock_req.audit_mode = "full"
    mock_req.model_dump.return_value = {"host": "1.2.3.4"}
    mock_job.kwargs = {"req": mock_req}

    with patch("rq.job.Job.fetch", return_value=mock_job):
        process_audit_log(job_id="test-job-id", result="test-result")

    # Verify mongo insert_one was called
    assert mock_mongo.insert_one.called
    args, _ = mock_mongo.insert_one.call_args
    doc = args[0]
    assert doc["job_id"] == "test-job-id"
    assert doc["status"] == "finished"
    assert doc["device_name"] == "1.2.3.4"
    assert doc["result"] == "test-result"
    assert "duration_seconds" in doc["metrics"]


def test_process_audit_log_metadata_omits_result(mock_mongo, unit_runtime):
    mock_job = MagicMock()
    mock_job.id = "metadata-job-id"
    mock_job.started_at = datetime(2024, 1, 1, 12, 1)
    mock_job.ended_at = datetime(2024, 1, 1, 12, 2)
    mock_job.enqueued_at = datetime(2024, 1, 1, 12, 0)
    mock_job.get_status.return_value = "finished"
    mock_job.meta = {"device_name": "1.2.3.4", "command": "show version"}
    mock_req = MagicMock()
    mock_req.audit_mode = "metadata"
    mock_req.model_dump.return_value = {"host": "1.2.3.4", "audit_mode": "metadata"}
    mock_job.kwargs = {"req": mock_req}

    with patch("rq.job.Job.fetch", return_value=mock_job):
        process_audit_log(job_id="metadata-job-id", result={"stdout": "large output"})

    args, _ = mock_mongo.insert_one.call_args
    doc = args[0]
    assert doc["job_id"] == "metadata-job-id"
    assert doc["audit_mode"] == "metadata"
    assert "result" not in doc
    assert doc["device_name"] == "1.2.3.4"


def test_process_audit_log_full_keeps_complete_result(mock_mongo, unit_runtime):
    mock_job = MagicMock()
    mock_job.id = "full-job-id"
    mock_job.started_at = datetime(2024, 1, 1, 12, 1)
    mock_job.ended_at = datetime(2024, 1, 1, 12, 2)
    mock_job.enqueued_at = datetime(2024, 1, 1, 12, 0)
    mock_job.get_status.return_value = "finished"
    mock_job.meta = {}
    mock_req = MagicMock()
    mock_req.audit_mode = "full"
    mock_req.model_dump.return_value = {"host": "1.2.3.4", "audit_mode": "full"}
    mock_job.kwargs = {"req": mock_req}
    result = {"stdout": "x" * 70000}

    with patch("rq.job.Job.fetch", return_value=mock_job):
        process_audit_log(job_id="full-job-id", result=result)

    args, _ = mock_mongo.insert_one.call_args
    doc = args[0]
    assert doc["audit_mode"] == "full"
    assert doc["result"] == result

def test_process_detached_audit(mock_mongo, unit_runtime):
    task_id = "detach-123"
    metadata = {"status": "running", "foo": "bar"}

    process_detached_audit(task_id=task_id, metadata=metadata)

    assert mock_mongo.insert_one.called
    args, _ = mock_mongo.insert_one.call_args
    doc = args[0]
    assert doc["task_id"] == "detach-123"
    assert doc["metadata"]["status"] == "running"
    assert doc["metadata"]["foo"] == "bar"
    assert "recorded_at" in doc

def test_prune_collection_by_count_deletes_oldest_records():
    collection = MagicMock()
    old_docs = [{"_id": "old-1"}, {"_id": "old-2"}]

    collection.name = "audit_jobs"
    collection.estimated_document_count.return_value = 5
    collection.find.return_value.sort.return_value.limit.return_value = old_docs
    collection.delete_many.return_value.deleted_count = 2

    _prune_collection_by_count(collection, max_documents=3)

    collection.find.assert_called_once_with({}, {"_id": 1})
    collection.find.return_value.sort.assert_called_once_with("created_at", 1)
    collection.find.return_value.sort.return_value.limit.assert_called_once_with(2)
    collection.delete_many.assert_called_once_with({"_id": {"$in": ["old-1", "old-2"]}})


def test_prune_collection_by_count_deletes_in_batches():
    collection = MagicMock()
    old_docs = [{"_id": f"old-{idx}"} for idx in range(3)]

    collection.name = "audit_jobs"
    collection.estimated_document_count.return_value = 20
    collection.find.return_value.sort.return_value.limit.return_value = old_docs
    collection.delete_many.return_value.deleted_count = 3

    _prune_collection_by_count(collection, max_documents=3, batch_size=3)

    collection.find.return_value.sort.return_value.limit.assert_called_once_with(3)
    collection.delete_many.assert_called_once_with(
        {"_id": {"$in": ["old-0", "old-1", "old-2"]}}
    )


def test_ensure_ttl_index_failure_does_not_raise():
    collection = MagicMock()
    collection.name = "audit_jobs"
    collection.list_indexes.side_effect = OperationFailure("not authorized")

    assert _ensure_ttl_index(collection, "created_at", retention_days=7) is False
