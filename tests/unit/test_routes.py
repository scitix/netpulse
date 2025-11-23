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
from netpulse.models.response import JobInResponse

device_module = import_module("netpulse.routes.device")
template_module = import_module("netpulse.routes.template")


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
    monkeypatch.setattr(device_module, "drivers", {"netmiko": _StubDriver})
    monkeypatch.setattr(device_module, "g_mgr", _StubManager())
    monkeypatch.setattr(template_module, "renderers", {"stub": _StubRenderer})
    monkeypatch.setattr(template_module, "parsers", {"stub": _StubParser})
    return TestClient(controller.app)


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
