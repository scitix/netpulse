from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from netpulse.services.audit import rpc_audit_callback
from netpulse.worker.archiver import process_audit_log, process_detached_audit


@pytest.fixture
def mock_mongo(monkeypatch):
    mock_client = MagicMock()
    mock_db = MagicMock()
    mock_collection = MagicMock()

    mock_client.__getitem__.return_value = mock_db
    mock_db.__getitem__.return_value = mock_collection

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
