from importlib import import_module
from typing import Iterable

import pytest
from fastapi.testclient import TestClient

from netpulse import controller
from netpulse.models.request import (
    BulkExecutionRequest,
    ExecutionRequest,
    TemplateParseRequest,
    TemplateRenderRequest,
)
from netpulse.models.response import JobInResponse, WorkerInResponse

device_module = import_module("netpulse.routes.device")
template_module = import_module("netpulse.routes.template")
manage_module = import_module("netpulse.routes.manage")


pytestmark = [pytest.mark.api]


class _StubDriver:
    driver_name: str = "netmiko"

    @classmethod
    def validate(cls, req: ExecutionRequest | BulkExecutionRequest) -> None:
        return None


class _StubManager:
    def execute_on_device(self, req: ExecutionRequest) -> JobInResponse:
        return JobInResponse(id="job1", status="queued", queue="q1")

    def execute_on_bulk_devices(
        self, reqs: Iterable[ExecutionRequest]
    ) -> tuple[list[JobInResponse], list[str]]:
        job = JobInResponse(id="job-bulk", status="queued", queue="q1")
        return [job], ["failed-host"]


class _StubRenderer:
    @classmethod
    def from_rendering_request(cls, req: TemplateRenderRequest) -> "_StubRenderer":
        return cls()

    def render(self, context: dict | None) -> str:
        return "rendered"


class _StubParser:
    @classmethod
    def from_parsing_request(cls, req: TemplateParseRequest) -> "_StubParser":
        return cls()

    def parse(self, context: str | None) -> dict:
        return {"parsed": True}


def _client_with_stubs(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    import importlib

    importlib.reload(controller)
    monkeypatch.setattr(device_module, "drivers", {"netmiko": _StubDriver})
    monkeypatch.setattr(device_module, "g_mgr", _StubManager())
    monkeypatch.setattr(template_module, "renderers", {"stub": _StubRenderer})
    monkeypatch.setattr(template_module, "parsers", {"stub": _StubParser})
    return TestClient(controller.app)


class _ManageStub:
    def __init__(self):
        self.calls: dict[str, object] = {}

    def get_job_list_by_ids(self, ids: list[str]):
        self.calls["get_job_list_by_ids"] = ids
        return [JobInResponse(id=ids[0], status="queued", queue="q1")]

    def get_job_list(self, q_name=None, status=None, limit=None):
        self.calls["get_job_list"] = (q_name, status, limit)
        return [JobInResponse(id="job-list", status=status or "queued", queue=q_name or "q1")]

    def cancel_job(self, id=None, q_name=None):
        self.calls["cancel_job"] = (id, q_name)
        return [id] if id else ["c1"]

    def get_worker_list(self, q_name=None):
        self.calls["get_worker_list"] = q_name
        return [
            WorkerInResponse(
                name="w1",
                status="busy",
                queues=[q_name] if q_name else None,
            )
        ]

    def kill_worker(self, name=None, q_name=None):
        self.calls["kill_worker"] = (name, q_name)
        if name:
            return [name]
        if q_name:
            return [f"{q_name}-w"]
        return []


def _client_with_manage_stub(monkeypatch: pytest.MonkeyPatch) -> tuple[TestClient, _ManageStub]:
    stub = _ManageStub()
    monkeypatch.setattr(manage_module, "g_mgr", stub)
    return TestClient(controller.app), stub


def test_device_exec_missing_host(monkeypatch, app_config):
    """POST /device/exec should 400 when required host missing."""
    client = _client_with_stubs(monkeypatch)
    payload = {"driver": "netmiko", "connection_args": {}, "command": "show version"}
    resp = client.post(
        "/device/exec", json=payload, headers={"X-API-KEY": app_config.server.api_key}
    )
    assert resp.status_code == 400
    assert resp.json()["message"] == "Value Error"


def test_device_exec_success(monkeypatch, app_config):
    """POST /device/exec should enqueue job and return 201."""
    client = _client_with_stubs(monkeypatch)
    payload = {
        "driver": "netmiko",
        "connection_args": {"host": "1.1.1.1"},
        "command": "show version",
    }
    resp = client.post(
        "/device/exec", json=payload, headers={"X-API-KEY": app_config.server.api_key}
    )
    assert resp.status_code == 201
    assert resp.json()["data"]["id"] == "job1"


def test_device_bulk_returns_success_when_no_devices(monkeypatch, app_config):
    """POST /device/bulk returns success with empty devices list."""
    client = _client_with_stubs(monkeypatch)
    payload = {
        "driver": "netmiko",
        "connection_args": {"host": "1.1.1.1"},
        "command": "show version",
        "devices": [],
    }
    resp = client.post(
        "/device/bulk",
        json=payload,
        headers={"X-API-KEY": app_config.server.api_key},
    )

    assert resp.status_code == 201
    body = resp.json()
    assert body["code"] == 200
    assert body["message"] == "success"
    assert body["data"] is None


def test_device_bulk_expands_devices(monkeypatch, app_config):
    """POST /device/bulk should expand devices and merge connection args per-device."""
    calls: dict[str, object] = {}

    class CaptureManager:
        def execute_on_bulk_devices(self, reqs: Iterable[ExecutionRequest]):
            calls["reqs"] = list(reqs)
            jobs = [
                JobInResponse(id=f"job-{req.connection_args.host}", status="queued", queue="q1")
                for req in calls["reqs"]
            ]
            return jobs, []

    class ValidatingDriver(_StubDriver):
        called = 0

        @classmethod
        def validate(cls, req: ExecutionRequest | BulkExecutionRequest) -> None:
            cls.called += 1
            return None

    monkeypatch.setattr(device_module, "drivers", {"netmiko": ValidatingDriver})
    monkeypatch.setattr(device_module, "g_mgr", CaptureManager())
    monkeypatch.setattr(template_module, "renderers", {"stub": _StubRenderer})
    monkeypatch.setattr(template_module, "parsers", {"stub": _StubParser})
    client = TestClient(controller.app)

    payload = {
        "driver": "netmiko",
        "connection_args": {"host": "base-host", "username": "base-user"},
        "command": "show clock",
        "devices": [{"host": "10.0.0.1"}, {"host": "10.0.0.2", "username": "override"}],
    }
    resp = client.post(
        "/device/bulk",
        json=payload,
        headers={"X-API-KEY": app_config.server.api_key},
    )

    assert resp.status_code == 201
    reqs = calls["reqs"]
    assert len(reqs) == 2  # type: ignore
    assert reqs[0].connection_args.host == "10.0.0.1"  # type: ignore
    assert reqs[0].connection_args.username == "base-user"  # type: ignore
    assert reqs[1].connection_args.host == "10.0.0.2"  # type: ignore
    assert reqs[1].connection_args.username == "override"  # type: ignore
    assert all(req.command == "show clock" for req in reqs)  # type: ignore
    assert ValidatingDriver.called == 1


def test_template_render_missing_name(monkeypatch, app_config):
    """POST /template/render should 400 when name missing."""
    client = _client_with_stubs(monkeypatch)
    resp = client.post(
        "/template/render",
        json={"template": "foo"},
        headers={"X-API-KEY": app_config.server.api_key},
    )
    assert resp.status_code == 400


def test_template_render_not_found(monkeypatch, app_config):
    """POST /template/render should 404 for unknown renderer."""
    client = _client_with_stubs(monkeypatch)
    resp = client.post(
        "/template/render",
        json={"name": "unknown", "template": "foo"},
        headers={"X-API-KEY": app_config.server.api_key},
    )
    assert resp.status_code == 404


def test_template_render_success(monkeypatch, app_config):
    """POST /template/render should return rendered output."""
    client = _client_with_stubs(monkeypatch)
    resp = client.post(
        "/template/render",
        json={"name": "stub", "template": "foo"},
        headers={"X-API-KEY": app_config.server.api_key},
    )
    assert resp.status_code == 200
    assert resp.json()["data"] == "rendered"


def test_template_parse_success(monkeypatch, app_config):
    """POST /template/parse should return parsed data."""
    client = _client_with_stubs(monkeypatch)
    resp = client.post(
        "/template/parse",
        json={"name": "stub", "template": "foo", "context": "bar"},
        headers={"X-API-KEY": app_config.server.api_key},
    )
    assert resp.status_code == 200
    assert resp.json()["data"] == {"parsed": True}


def test_get_job_with_filters(monkeypatch, app_config):
    client, stub = _client_with_manage_stub(monkeypatch)
    resp = client.get(
        "/job",
        params={"queue": "FifoQ", "status": "finished"},
        headers={"X-API-KEY": app_config.server.api_key},
    )
    assert resp.status_code == 200
    assert stub.calls["get_job_list"] == ("FifoQ", "finished", None)
    data = resp.json()["data"]
    assert data[0]["queue"] == "FifoQ"


def test_get_job_by_id(monkeypatch, app_config):
    client, stub = _client_with_manage_stub(monkeypatch)
    resp = client.get(
        "/job",
        params={"id": "job-123"},
        headers={"X-API-KEY": app_config.server.api_key},
    )
    assert resp.status_code == 200
    assert stub.calls["get_job_list_by_ids"] == ["job-123"]
    assert resp.json()["data"][0]["id"] == "job-123"


def test_delete_job_by_id_and_queue(monkeypatch, app_config):
    client, stub = _client_with_manage_stub(monkeypatch)

    resp = client.delete(
        "/job",
        params={"id": "job-1"},
        headers={"X-API-KEY": app_config.server.api_key},
    )
    assert resp.status_code == 200
    assert stub.calls["cancel_job"] == ("job-1", None)
    assert resp.json()["data"] == ["job-1"]

    resp_queue = client.delete(
        "/job",
        params={"queue": "HostQ_h1"},
        headers={"X-API-KEY": app_config.server.api_key},
    )
    assert resp_queue.status_code == 200
    assert stub.calls["cancel_job"] == (None, "HostQ_h1")
    assert resp_queue.json()["data"] == ["c1"]


def test_get_workers_with_queue(monkeypatch, app_config):
    client, stub = _client_with_manage_stub(monkeypatch)
    resp = client.get(
        "/worker",
        params={"queue": "HostQ_h1"},
        headers={"X-API-KEY": app_config.server.api_key},
    )
    assert resp.status_code == 200
    assert stub.calls["get_worker_list"] == "HostQ_h1"
    assert resp.json()["data"][0]["queues"] == ["HostQ_h1"]


def test_kill_worker_by_name_and_queue(monkeypatch, app_config):
    client, stub = _client_with_manage_stub(monkeypatch)

    resp = client.delete(
        "/worker",
        params={"name": "worker-1"},
        headers={"X-API-KEY": app_config.server.api_key},
    )
    assert resp.status_code == 200
    assert stub.calls["kill_worker"] == ("worker-1", None)
    assert resp.json()["data"] == ["worker-1"]

    resp_queue = client.delete(
        "/worker",
        params={"queue": "HostQ_h2"},
        headers={"X-API-KEY": app_config.server.api_key},
    )
    assert resp_queue.status_code == 200
    assert stub.calls["kill_worker"] == (None, "HostQ_h2")
    assert resp_queue.json()["data"] == ["HostQ_h2-w"]

    resp_empty = client.delete("/worker", headers={"X-API-KEY": app_config.server.api_key})
    assert resp_empty.status_code == 200
    assert stub.calls["kill_worker"] == (None, None)
    assert resp_empty.json()["data"] == []
