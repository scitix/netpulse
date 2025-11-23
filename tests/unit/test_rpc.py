import pytest

from netpulse.models import DriverConnectionArgs, DriverName
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

    def send(self, session, command: list[str]) -> dict[str, str]:
        self.sent_payload = command
        return {cmd: f"sent-{cmd}" for cmd in command}

    def config(self, session, config: list[str]) -> dict[str, str]:
        self.sent_payload = config
        return {cfg: f"cfg-{cfg}" for cfg in config}

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

    assert result == {"rendered-cmd": {"parsed": "sent-rendered-cmd"}}


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

        def config(self, session, config: list[str]) -> dict[str, str]:
            captured["config"] = ",".join(config)
            return {cfg: f"cfg-{cfg}" for cfg in config}

    req = ExecutionRequest(
        driver=DriverName.NETMIKO,
        connection_args=DriverConnectionArgs(host="10.0.0.1"),
        config=["line1", "line2"],
    )

    monkeypatch.setattr(rpc, "drivers", {DriverName.NETMIKO: ConfigDriver})
    result = rpc.execute(req)

    assert captured["config"] == "line1,line2"
    assert result == {"line1": "cfg-line1", "line2": "cfg-line2"}


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
    assert result == {"rendered": "sent-rendered"}


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

    with pytest.raises(RuntimeError):
        rpc.execute(req)

    assert disconnect_calls, "disconnect should be invoked on exception"
