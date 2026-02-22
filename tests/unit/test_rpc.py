import pytest
from pydantic import HttpUrl

from netpulse.models import DriverConnectionArgs, DriverName
from netpulse.models.common import WebHook
from netpulse.models.request import ExecutionRequest, TemplateParseRequest, TemplateRenderRequest
from netpulse.plugins.drivers import BaseDriver
from netpulse.plugins.templates import BaseTemplateParser, BaseTemplateRenderer
from netpulse.services import rpc


class StubDriver(BaseDriver):
    driver_name = "netmiko"

    @classmethod
    def from_execution_request(cls, req: ExecutionRequest) -> "StubDriver":
        return cls(req=req)

    @classmethod
    def validate(cls, req: ExecutionRequest) -> None:
        return None

    def __init__(self, req: ExecutionRequest, **kwargs):
        self.req = req
        self.disconnect_calls: int = 0
        self.sent_payload: list[str] | None = None

    def connect(self) -> str:
        return "session"

    def send(self, session, command: list[str]) -> dict:
        self.sent_payload = command
        return {
            cmd: {
                "output": f"sent-{cmd}",
                "error": "",
                "exit_status": 0,
                "metadata": {"duration_seconds": 0.001},
            }
            for cmd in command
        }

    def config(self, session, config: list[str]) -> dict:
        self.sent_payload = config
        return {
            cfg: {
                "output": f"cfg-{cfg}",
                "error": "",
                "exit_status": 0,
                "metadata": {"duration_seconds": 0.001},
            }
            for cfg in config
        }

    def disconnect(self, session) -> None:
        self.disconnect_calls += 1


class StubRenderer(BaseTemplateRenderer):
    template_name = "stub-renderer"

    @classmethod
    def from_rendering_request(cls, req: TemplateRenderRequest) -> "StubRenderer":
        return cls()

    def __init__(self):
        self.called = False

    def render(self, context: dict | None) -> str:
        self.called = True
        return "rendered-cmd"


class StubParser(BaseTemplateParser):
    template_name = "stub-parser"

    @classmethod
    def from_parsing_request(cls, req: TemplateParseRequest) -> "StubParser":
        return cls()

    def __init__(self):
        self.called = False

    def parse(self, context: str) -> dict:
        self.called = True
        return {"parsed": context}


def test_rpc_execute_with_render_and_parse(monkeypatch, app_config):
    """RPC execute should render, send via driver, parse output, and return parsed map."""
    req = ExecutionRequest(
        driver=DriverName.NETMIKO,
        connection_args=DriverConnectionArgs(host="10.0.0.1"),
        command={"cmd": "show version"},
        rendering=TemplateRenderRequest(name="stub-renderer", template="t"),
        parsing=TemplateParseRequest(name="stub-parser", template="t"),
    )

    monkeypatch.setattr(
        rpc,
        "drivers",
        {DriverName.NETMIKO: StubDriver},
    )
    monkeypatch.setattr(rpc, "renderers", {"stub-renderer": StubRenderer})
    monkeypatch.setattr(rpc, "parsers", {"stub-parser": StubParser})

    result = rpc.execute(req)

    assert result["rendered-cmd"]["output"] == "sent-rendered-cmd"
    assert result["rendered-cmd"]["parsed"] == {"parsed": "sent-rendered-cmd"}


def test_rpc_execute_missing_driver_raises(monkeypatch, app_config):
    """RPC execute should raise when requested driver is unavailable."""
    req = ExecutionRequest(
        driver=DriverName.NETMIKO,
        connection_args=DriverConnectionArgs(host="10.0.0.1"),
        command="show version",
    )

    monkeypatch.setattr(rpc, "drivers", {})

    with pytest.raises(NotImplementedError):
        rpc.execute(req)


def test_rpc_execute_config_path(monkeypatch, app_config):
    """RPC execute should call driver.config when config is provided."""
    captured: dict[str, str] = {}

    class ConfigDriver(StubDriver):
        @classmethod
        def from_execution_request(cls, req: ExecutionRequest) -> "ConfigDriver":
            return cls(req=req)

        def config(self, session, config: list[str]) -> dict:
            captured["config"] = ",".join(config)
            cfg_key = "\n".join(config)
            return {cfg_key: {"output": f"cfg-{cfg_key}", "error": "", "exit_status": 0}}

    req = ExecutionRequest(
        driver=DriverName.NETMIKO,
        connection_args=DriverConnectionArgs(host="10.0.0.1"),
        config=["line1", "line2"],
    )

    monkeypatch.setattr(rpc, "drivers", {DriverName.NETMIKO: ConfigDriver})
    result = rpc.execute(req)

    assert captured["config"] == "line1,line2"
    assert result["line1\nline2"]["output"] == "cfg-line1\nline2"


def test_rpc_execute_parsing_requires_dict(monkeypatch, app_config):
    """Parsing step should fail when driver returns non-dict result."""

    class BadDriver(StubDriver):
        def send(self, session, command: list[str]) -> str:  # type: ignore[override]
            return "not-a-dict"

    req = ExecutionRequest(
        driver=DriverName.NETMIKO,
        connection_args=DriverConnectionArgs(host="10.0.0.1"),
        command="show version",
        parsing=TemplateParseRequest(name="stub-parser", template="t"),
    )

    monkeypatch.setattr(rpc, "drivers", {DriverName.NETMIKO: BadDriver})
    monkeypatch.setattr(rpc, "parsers", {"stub-parser": StubParser})

    with pytest.raises(ValueError):
        rpc.execute(req)


def test_rpc_execute_rendering_requires_dict(monkeypatch, app_config):
    """Rendering step should fail when payload is not a dict."""

    req = ExecutionRequest(
        driver=DriverName.NETMIKO,
        connection_args=DriverConnectionArgs(host="10.0.0.1"),
        command={"cmd": "show version"},
        rendering=TemplateRenderRequest(name="stub-renderer", template="t"),
    )

    monkeypatch.setattr(rpc, "drivers", {DriverName.NETMIKO: StubDriver})
    monkeypatch.setattr(rpc, "renderers", {"stub-renderer": StubRenderer})

    monkeypatch.setattr(StubRenderer, "render", classmethod(lambda cls, ctx: "rendered"))

    result = rpc.execute(req)
    assert result["rendered"]["output"] == "sent-rendered"


def test_rpc_disconnect_called_on_exception(monkeypatch, app_config):
    """Driver.disconnect should be called even when send/config raises."""
    disconnect_calls: list[int] = []

    class FailingDriver(StubDriver):
        def send(self, session, command: list[str]):
            raise RuntimeError("boom")

        def disconnect(self, session) -> None:
            disconnect_calls.append(1)

    req = ExecutionRequest(
        driver=DriverName.NETMIKO,
        connection_args=DriverConnectionArgs(host="10.0.0.1"),
        command="show version",
    )

    monkeypatch.setattr(rpc, "drivers", {DriverName.NETMIKO: FailingDriver})

    result = rpc.execute(req)
    assert result["show version"].exit_status == 1
    assert "boom" in result["show version"].error
    assert disconnect_calls, "disconnect should be invoked on exception"


def _req_with_webhook() -> ExecutionRequest:
    return ExecutionRequest(
        driver=DriverName.NETMIKO,
        connection_args=DriverConnectionArgs(host="10.0.0.1"),
        command="show version",
        webhook=WebHook(name="basic", url=HttpUrl("http://example.com/hook")),
    )


def test_rpc_exception_callback_skips_invalid_meta():
    """rpc_exception_callback should return None when job.meta fails validation."""

    class DummyJob:
        def __init__(self):
            self.meta = "not-a-dict"
            self.save_calls = 0

        def save_meta(self):
            self.save_calls += 1

    job = DummyJob()
    result = rpc.rpc_exception_callback(job, None, ValueError, ValueError("boom"), None)  # type: ignore

    assert result is None
    assert job.save_calls == 0
    assert job.meta == "not-a-dict"


def test_rpc_webhook_callback_success_invokes_webhook(monkeypatch):
    """rpc_webhook_callback should dispatch result to webhook on success."""
    req = _req_with_webhook()
    calls: list[tuple[ExecutionRequest, str, object]] = []

    class DummyJob:
        def __init__(self):
            self.kwargs = {"req": req}
            self.id = "job-123"
            self.meta = {}

    class DummyWebhook:
        webhook_name = "basic"

        def __init__(self, hook):
            self.hook = hook

        def call(self, req, job, result, **kwargs):
            calls.append((req, job.id, result))

    monkeypatch.setattr(rpc, "webhooks", {"basic": DummyWebhook})

    job = DummyJob()
    rpc.rpc_webhook_callback(job, None, {"ok": True})

    assert calls == [(req, "job-123", {"ok": True})]


def test_rpc_webhook_callback_failure_uses_unknown_error(monkeypatch):
    """Failure path should fall back to 'Unknown Error' when meta validation fails."""
    req = _req_with_webhook()
    results: list[object] = []

    class DummyJob:
        def __init__(self):
            self.kwargs = {"req": req}
            self.id = "job-err"
            self.meta = "bad-meta"

        def save_meta(self):
            return None

    class DummyWebhook:
        webhook_name = "basic"

        def __init__(self, hook):
            pass

        def call(self, req, job, result, **kwargs):
            results.append(result)

    monkeypatch.setattr(rpc, "webhooks", {"basic": DummyWebhook})

    job = DummyJob()
    rpc.rpc_webhook_callback(job, None, ValueError, ValueError("boom"), None)

    assert results == ["Unknown Error"]


def test_rpc_webhook_callback_raises_when_webhook_fails(monkeypatch):
    """Webhook errors should bubble up instead of being swallowed."""
    req = _req_with_webhook()

    class DummyJob:
        def __init__(self):
            self.kwargs = {"req": req}
            self.id = "job-raise"
            self.meta = {}

    class FailingWebhook:
        webhook_name = "basic"

        def __init__(self, hook):
            pass

        def call(self, req, job, result, **kwargs):
            raise RuntimeError("webhook failed")

    monkeypatch.setattr(rpc, "webhooks", {"basic": FailingWebhook})

    job = DummyJob()
    with pytest.raises(RuntimeError, match="webhook failed"):
        rpc.rpc_webhook_callback(job, None, {"ok": True})
