from datetime import datetime, timedelta, timezone
from typing import ClassVar

import pytest
from pydantic import ValidationError

from netpulse.models import DriverConnectionArgs, DriverName
from netpulse.models.request import ExecutionRequest
from netpulse.models.response import JobInResponse


def _base_request(**kwargs) -> dict:
    return {
        "driver": DriverName.PARAMIKO,
        "connection_args": DriverConnectionArgs(host="10.0.0.1"),
        **kwargs,
    }


def test_execution_request_requires_one_payload(app_config):
    """ExecutionRequest must include exactly one of command/config."""
    with pytest.raises(ValidationError):
        ExecutionRequest(**_base_request())

    with pytest.raises(ValidationError):
        ExecutionRequest(**_base_request(command="show version", config="hostname router"))


def test_execution_request_queue_strategy_defaults(app_config):
    """Queue strategy defaults: netmiko=pinned, paramiko=fifo (can manually select pinned)."""
    req_netmiko = ExecutionRequest(
        driver=DriverName.NETMIKO,
        connection_args=DriverConnectionArgs(host="10.0.0.1"),
        command="show version",
    )
    assert req_netmiko.queue_strategy is not None
    assert req_netmiko.queue_strategy.value == "pinned"

    req_paramiko = ExecutionRequest(
        driver=DriverName.PARAMIKO,
        connection_args=DriverConnectionArgs(host="10.0.0.2"),
        command="uname -a",
    )
    assert req_paramiko.queue_strategy is not None
    assert req_paramiko.queue_strategy.value == "fifo"  # Default fifo, can manually select pinned


def test_execution_request_dict_payload_requires_rendering(app_config):
    """Dict payload requires rendering section to be valid."""
    with pytest.raises(ValidationError):
        ExecutionRequest(**_base_request(config={"cmd": "show version"}))

    req = ExecutionRequest(
        **_base_request(
            config={"cmd": "show version"},
            rendering={"name": "jinja2", "template": "{{ cmd }}"},
        )
    )
    assert req.rendering is not None


def test_execution_request_ttl_bounds(app_config):
    """TTL must fall inside configured bounds."""
    with pytest.raises(ValidationError):
        ExecutionRequest(**_base_request(command="show version", ttl=0))

    with pytest.raises(ValidationError):
        ExecutionRequest(**_base_request(command="show version", ttl=90000))  # Exceeds max 86400


def test_job_in_response_serialization(monkeypatch):
    """JobInResponse.from_job should populate timing, result, and error data."""

    class DummyResult:
        def __init__(self):
            from rq.results import Result

            self.type = Result.Type.SUCCESSFUL
            self.return_value = {"ok": True}

    class DummyJob:
        id = "job-1"
        origin = "fifo"
        worker_name = "worker-1"
        meta: ClassVar = {"error": ("ValueError", "bad")}

        created_at = datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc)
        enqueued_at = created_at + timedelta(seconds=1)
        started_at = enqueued_at + timedelta(seconds=1)
        ended_at = started_at + timedelta(seconds=2)

        def get_status(self):
            from rq.job import JobStatus

            return JobStatus.FINISHED

        def latest_result(self):
            return DummyResult()

    monkeypatch.setenv("TZ", "UTC")
    resp = JobInResponse.from_job(DummyJob())  # type: ignore

    assert resp.id == "job-1"
    assert resp.status == "finished"
    assert resp.queue == "fifo"
    assert resp.worker == "worker-1"
    assert resp.duration == 2.0
    assert resp.queue_time == 1.0
    assert resp.result is not None
    assert resp.result.error == {"type": "ValueError", "message": "bad"}
    assert resp.created_at is not None
    assert resp.created_at.tzinfo == timezone.utc
    assert resp.created_at.isoformat().endswith("+00:00")
