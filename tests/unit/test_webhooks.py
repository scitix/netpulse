from datetime import datetime, timezone
from typing import Any

import pytest
from pydantic import HttpUrl

from netpulse.models import DriverConnectionArgs, DriverName
from netpulse.models.common import JobResult, WebHook
from netpulse.models.driver import DriverExecutionResult
from netpulse.models.request import ExecutionRequest
from netpulse.models.response import JobInResponse
from netpulse.plugins.webhooks import basic as webhook_basic
from netpulse.plugins.webhooks.basic import BasicWebHookCaller


def _make_job_response(
    job_id="job-1",
    status="finished",
    result_type=JobResult.ResultType.SUCCESSFUL,
    retval=None,
    error=None,
    task_id=None,
    device_name=None,
    command=None,
    started_at=None,
    ended_at=None,
) -> JobInResponse:
    """Helper to create a JobInResponse for testing."""
    result = JobResult(type=result_type, retval=retval, error=error)
    return JobInResponse(
        id=job_id,
        status=status,
        queue="fifo",
        result=result,
        task_id=task_id,
        device_name=device_name,
        command=command,
        started_at=started_at or datetime(2024, 2, 23, 10, 0, 0, tzinfo=timezone.utc),
        ended_at=ended_at or datetime(2024, 2, 23, 10, 0, 1, tzinfo=timezone.utc),
    )


def test_basic_webhook_payload_structure(monkeypatch):
    """Webhook payload should be aligned with JobInResponse but with string result.type."""
    hook = WebHook(name="basic", url=HttpUrl("http://example.com/hook"))
    captured: dict[str, Any] = {}

    class DummyResponse:
        def raise_for_status(self):
            pass

    def fake_request(**kwargs):
        captured.update(kwargs)
        return DummyResponse()

    monkeypatch.setattr(webhook_basic.requests, "request", fake_request)

    req = ExecutionRequest(
        driver=DriverName.NETMIKO,
        connection_args=DriverConnectionArgs(host="192.168.1.1", device_type="cisco_ios"),
        command="show version",
    )

    retval = [
        DriverExecutionResult(command="show version", stdout="Cisco IOS Software", exit_status=0)
    ]
    job_resp = _make_job_response(
        job_id="job-1",
        retval=retval,
        device_name="switch-01",
        command=["show version"],
    )

    caller = BasicWebHookCaller(hook)
    caller.call(req=req, job=job_resp, result=retval, is_success=True, event_type="job.completed")

    payload: dict = captured["json"]

    # Core fields
    assert payload["id"] == "job-1"
    assert payload["status"] == "finished"
    assert payload["event_type"] == "job.completed"
    assert payload["timestamp"] is not None
    assert payload["final"] is True

    # Timing
    assert payload["started_at"] is not None
    assert payload["ended_at"] is not None
    assert payload["duration"] == pytest.approx(1.0, abs=0.1)

    # Structured result with string type
    assert payload["result"]["type"] == "successful"
    assert len(payload["result"]["retval"]) == 1
    assert payload["result"]["retval"][0]["command"] == "show version"
    assert payload["result"]["retval"][0]["stdout"] == "Cisco IOS Software"
    assert payload["result"]["retval"][0]["exit_status"] == 0
    assert payload["result"]["error"] is None

    # Device info from request
    assert payload["device"]["host"] == "192.168.1.1"
    assert payload["device"]["device_type"] == "cisco_ios"

    # Meta fields
    assert payload["device_name"] == "switch-01"
    assert payload["command"] == ["show version"]
    assert payload["task_id"] is None

    # HTTP request details
    assert captured["method"] == hook.method.value
    assert captured["url"] == hook.url.unicode_string()


def test_basic_webhook_raises_on_request_errors(monkeypatch):
    """HTTP errors from BasicWebHookCaller.call() should propagate for retry scheduling."""
    hook = WebHook(name="basic", url=HttpUrl("http://example.com/hook"))
    calls: list[int] = []

    def failing_request(**_kwargs):
        calls.append(1)
        raise RuntimeError("boom")

    monkeypatch.setattr(webhook_basic.requests, "request", failing_request)

    job_resp = _make_job_response(job_id="job-2")
    caller = BasicWebHookCaller(hook)
    with pytest.raises(RuntimeError, match="boom"):
        caller.call(req=None, job=job_resp, result="done")

    assert calls == [1]


def test_basic_webhook_failure_status(monkeypatch):
    """Webhook should report failed status with structured error for failed jobs."""
    hook = WebHook(name="basic", url=HttpUrl("http://example.com/hook"))
    captured: dict[str, Any] = {}

    class DummyResponse:
        def raise_for_status(self):
            pass

    def fake_request(**kwargs):
        captured.update(kwargs)
        return DummyResponse()

    monkeypatch.setattr(webhook_basic.requests, "request", fake_request)

    req = ExecutionRequest(
        driver=DriverName.NETMIKO,
        connection_args=DriverConnectionArgs(host="192.168.1.1"),
        command="show version",
    )

    job_resp = _make_job_response(
        job_id="job-3",
        status="failed",
        result_type=JobResult.ResultType.FAILED,
        error={"type": "ConnectionError", "message": "Unable to connect to device"},
    )

    caller = BasicWebHookCaller(hook)
    caller.call(req=req, job=job_resp, result=None, is_success=False, event_type="job.failed")

    payload: dict = captured["json"]
    assert payload["status"] == "failed"
    assert payload["event_type"] == "job.failed"
    assert payload["result"]["type"] == "failed"
    assert payload["result"]["error"]["type"] == "ConnectionError"
    assert payload["result"]["error"]["message"] == "Unable to connect to device"


def test_basic_webhook_multiple_commands(monkeypatch):
    """Webhook should include structured retval for multiple commands."""
    hook = WebHook(name="basic", url=HttpUrl("http://example.com/hook"))
    captured: dict[str, Any] = {}

    class DummyResponse:
        def raise_for_status(self):
            pass

    def fake_request(**kwargs):
        captured.update(kwargs)
        return DummyResponse()

    monkeypatch.setattr(webhook_basic.requests, "request", fake_request)

    req = ExecutionRequest(
        driver=DriverName.NETMIKO,
        connection_args=DriverConnectionArgs(host="192.168.1.1"),
        command=["show version", "show interfaces"],
    )

    retval = [
        DriverExecutionResult(
            command="show version", stdout="Cisco IOS Software, Version 15.1", exit_status=0
        ),
        DriverExecutionResult(
            command="show interfaces", stdout="GigabitEthernet0/0 is up", exit_status=0
        ),
    ]
    job_resp = _make_job_response(
        job_id="job-4",
        retval=retval,
        command=["show version", "show interfaces"],
    )

    caller = BasicWebHookCaller(hook)
    caller.call(req=req, job=job_resp, result=retval, is_success=True)

    payload: dict = captured["json"]
    assert payload["status"] == "finished"
    assert payload["result"]["type"] == "successful"
    assert len(payload["result"]["retval"]) == 2
    assert payload["result"]["retval"][0]["command"] == "show version"
    assert payload["result"]["retval"][0]["stdout"] == "Cisco IOS Software, Version 15.1"
    assert payload["result"]["retval"][1]["command"] == "show interfaces"
    assert payload["result"]["retval"][1]["stdout"] == "GigabitEthernet0/0 is up"
    assert payload["command"] == ["show version", "show interfaces"]


def test_basic_webhook_detached_task_event_type(monkeypatch):
    """Webhook for detached tasks should use detached.completed event_type."""
    hook = WebHook(name="basic", url=HttpUrl("http://example.com/hook"))
    captured: dict[str, Any] = {}

    class DummyResponse:
        def raise_for_status(self):
            pass

    def fake_request(**kwargs):
        captured.update(kwargs)
        return DummyResponse()

    monkeypatch.setattr(webhook_basic.requests, "request", fake_request)

    req = ExecutionRequest(
        driver=DriverName.PARAMIKO,
        connection_args=DriverConnectionArgs(host="192.168.1.100"),
        command="stress --cpu 4",
        detach=True,
    )

    retval = [
        DriverExecutionResult(command="stress --cpu 4", stdout="stress: info: done", exit_status=0)
    ]
    job_resp = _make_job_response(
        job_id="task_abc789",
        retval=retval,
        task_id="task_abc789",
        device_name="gpu-node-01",
        command=["stress --cpu 4"],
    )

    caller = BasicWebHookCaller(hook)
    caller.call(
        req=req, job=job_resp, result=retval, is_success=True, event_type="detached.completed"
    )

    payload: dict = captured["json"]
    assert payload["id"] == "task_abc789"
    assert payload["event_type"] == "detached.completed"
    assert payload["final"] is True
    assert payload["task_id"] == "task_abc789"
    assert payload["device"]["host"] == "192.168.1.100"
    assert payload["result"]["type"] == "successful"


def test_basic_webhook_log_push_not_final(monkeypatch):
    """Webhook for detached log push should have final=False."""
    hook = WebHook(name="basic", url=HttpUrl("http://example.com/hook"))
    captured: dict[str, Any] = {}

    class DummyResponse:
        def raise_for_status(self):
            pass

    def fake_request(**kwargs):
        captured.update(kwargs)
        return DummyResponse()

    monkeypatch.setattr(webhook_basic.requests, "request", fake_request)

    req = ExecutionRequest(
        driver=DriverName.PARAMIKO,
        connection_args=DriverConnectionArgs(host="192.168.1.100"),
        command="tail -f /var/log/syslog",
        detach=True,
    )

    retval = [
        DriverExecutionResult(command="tail -f /var/log/syslog", stdout="log line 1\nlog line 2")
    ]
    job_resp = _make_job_response(
        job_id="task_push01",
        retval=retval,
        task_id="task_push01",
        command=["tail -f /var/log/syslog"],
    )

    caller = BasicWebHookCaller(hook)
    caller.call(
        req=req, job=job_resp, result=retval, is_success=True, event_type="detached.log_push"
    )

    payload: dict = captured["json"]
    assert payload["event_type"] == "detached.log_push"
    assert payload["final"] is False
    assert payload["task_id"] == "task_push01"


def test_basic_webhook_fallback_for_raw_error_tuple(monkeypatch):
    """When job has no structured result, fallback should handle error tuples."""
    hook = WebHook(name="basic", url=HttpUrl("http://example.com/hook"))
    captured: dict[str, Any] = {}

    class DummyResponse:
        def raise_for_status(self):
            pass

    def fake_request(**kwargs):
        captured.update(kwargs)
        return DummyResponse()

    monkeypatch.setattr(webhook_basic.requests, "request", fake_request)

    # Use a simple object without structured result
    class SimpleJob:
        id = "job-fallback"
        status = "failed"
        result = None
        task_id = None
        device_name = None
        command = None
        started_at = None
        ended_at = None
        duration = None

    caller = BasicWebHookCaller(hook)
    error_tuple = ("ConnectionError", "Unable to connect to device")
    caller.call(req=None, job=SimpleJob(), result=error_tuple, is_success=False)

    payload: dict = captured["json"]
    assert payload["status"] == "failed"
    assert payload["result"]["type"] == "failed"
    assert payload["result"]["error"]["type"] == "ConnectionError"
    assert payload["result"]["error"]["message"] == "Unable to connect to device"
