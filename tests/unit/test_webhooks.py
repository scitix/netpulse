from typing import Any

from pydantic import HttpUrl

from netpulse.models import DriverConnectionArgs, DriverName
from netpulse.models.common import WebHook
from netpulse.models.driver import DriverExecutionResult
from netpulse.models.request import ExecutionRequest
from netpulse.plugins.webhooks import basic as webhook_basic
from netpulse.plugins.webhooks.basic import BasicWebHookCaller


class MockJob:
    def __init__(self, id, status="finished"):
        self.id = id
        self._status = status

    def get_status(self):
        return self._status


def test_basic_webhook_calls_requests(monkeypatch):
    """BasicWebHookCaller should send JSON payload with job id, result, device info, and command."""
    hook = WebHook(name="basic", url=HttpUrl("http://example.com/hook"))
    captured: dict[str, Any] = {}

    class DummyResponse:
        def raise_for_status(self):
            captured["raised"] = True

    def fake_request(**kwargs):
        captured.update(kwargs)
        return DummyResponse()

    monkeypatch.setattr(webhook_basic.requests, "request", fake_request)

    # Create a mock ExecutionRequest with device and command info
    req = ExecutionRequest(
        driver=DriverName.NETMIKO,
        connection_args=DriverConnectionArgs(host="192.168.1.1", device_type="cisco_ios"),
        command="show version",
    )

    caller = BasicWebHookCaller(hook)
    caller = BasicWebHookCaller(hook)
    # Use a DriverExecutionResult object that simulates command output
    result = {"show version": DriverExecutionResult(output="Cisco IOS Software", exit_status=0)}
    caller.call(req=req, job=MockJob(id="job-1"), result=result)

    assert captured["method"] == hook.method.value
    assert captured["url"] == hook.url.unicode_string()

    payload: dict = captured["json"]
    assert payload["id"] == "job-1"
    assert "Command: show version" in payload["result"]
    assert "Cisco IOS Software" in payload["result"]
    assert payload["status"] == "success"
    assert payload["driver"] == "netmiko"
    assert payload["device"]["host"] == "192.168.1.1"
    assert payload["device"]["device_type"] == "cisco_ios"
    assert payload["command"] == "show version"
    assert captured["raised"] is True


def test_basic_webhook_swallows_request_errors(monkeypatch):
    """HTTP errors from webhook should be logged, not raised."""
    hook = WebHook(name="basic", url=HttpUrl("http://example.com/hook"))
    calls: list[int] = []

    def failing_request(**_kwargs):
        calls.append(1)
        raise RuntimeError("boom")

    monkeypatch.setattr(webhook_basic.requests, "request", failing_request)

    caller = BasicWebHookCaller(hook)
    # Should not raise even if the HTTP call fails
    caller = BasicWebHookCaller(hook)
    # Should not raise even if the HTTP call fails
    caller.call(req=None, job=MockJob(id="job-2"), result="done")

    assert calls == [1]


def test_basic_webhook_handles_failure_status(monkeypatch):
    """BasicWebHookCaller should mark status as failed for error tuples."""
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

    caller = BasicWebHookCaller(hook)
    # Simulate failure with error tuple
    error_tuple = ("ConnectionError", "Unable to connect to device")
    caller.call(req=req, job=MockJob(id="job-3", status="failed"), result=error_tuple)

    payload: dict = captured["json"]
    assert payload["status"] == "failed"
    assert payload["id"] == "job-3"
    assert "ConnectionError" in payload["result"]


def test_basic_webhook_formats_multiple_commands(monkeypatch):
    """BasicWebHookCaller should format multiple commands result correctly."""
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

    caller = BasicWebHookCaller(hook)
    caller = BasicWebHookCaller(hook)
    # Simulate result with multiple commands
    multi_cmd_result = {
        "show version": DriverExecutionResult(
            output="Cisco IOS Software, Version 15.1", exit_status=0
        ),
        "show interfaces": DriverExecutionResult(output="GigabitEthernet0/0 is up", exit_status=0),
    }
    caller.call(req=req, job=MockJob(id="job-4"), result=multi_cmd_result)

    payload: dict = captured["json"]
    assert payload["status"] == "success"
    assert payload["id"] == "job-4"
    assert "Command: show version" in payload["result"]
    assert "Command: show interfaces" in payload["result"]
    assert "Cisco IOS Software" in payload["result"]
    assert "GigabitEthernet0/0 is up" in payload["result"]
    assert payload["command"] == "show version\nshow interfaces"


def test_basic_webhook_formats_nested_dict_result(monkeypatch):
    """BasicWebHookCaller should format nested dict result (paramiko format) correctly."""
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
        connection_args=DriverConnectionArgs(host="192.168.1.1"),
        command="show version",
    )

    caller = BasicWebHookCaller(hook)
    # Simulate paramiko nested dict result using DriverExecutionResult model
    nested_result = {
        "show version": DriverExecutionResult(
            output="Cisco IOS Software, Version 15.1", error="", exit_status=0
        )
    }
    caller.call(req=req, job=MockJob(id="job-5"), result=nested_result)

    payload: dict = captured["json"]
    assert payload["status"] == "success"
    assert "Command: show version" in payload["result"]
    assert "Output:" in payload["result"]
    assert "Cisco IOS Software" in payload["result"]
    assert "Exit Status: 0" in payload["result"]
