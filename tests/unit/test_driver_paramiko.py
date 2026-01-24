from netpulse.plugins.drivers.paramiko import ParamikoDriver
from netpulse.plugins.drivers.paramiko.model import (
    ParamikoConnectionArgs,
    ParamikoFileTransferOperation,
    ParamikoSendCommandArgs,
    ParamikoSendConfigArgs,
)


def test_paramiko_send_uses_exec_args(monkeypatch):
    """Ensure exec args are passed through to session.exec_command."""

    class FakeStdout:
        def __init__(self, text: str):
            self._text = text
            self.channel = type("C", (), {"recv_exit_status": lambda self: 0})()

        def read(self):
            return self._text.encode()

    class FakeStderr(FakeStdout):
        pass

    class FakeSession:
        def __init__(self):
            self.calls = []

        def exec_command(self, cmd, **kwargs):
            self.calls.append((cmd, kwargs))
            return None, FakeStdout(f"out-{cmd}"), FakeStderr("")

    session = FakeSession()
    driver = ParamikoDriver(
        args=ParamikoSendCommandArgs(
            timeout=1.5, get_pty=True, environment={"k": "v"}, bufsize=1024
        ),
        conn_args=ParamikoConnectionArgs(host="h", username="u", password="p"),
    )

    result = driver.send(session, ["cmd1", "cmd2"])  # type: ignore
    assert set(result.keys()) == {"cmd1", "cmd2"}
    for _, kwargs in session.calls:
        assert kwargs["timeout"] == 1.5
        assert kwargs["get_pty"] is True
        assert kwargs["environment"] == {"k": "v"}
        assert kwargs["bufsize"] == 1024


def test_paramiko_send_returns_empty_when_no_commands():
    """Return empty dict and avoid exec when no commands are provided."""

    class FakeSession:
        def __init__(self):
            self.called = False

        def exec_command(self, *_args, **_kwargs):
            self.called = True
            raise AssertionError("should not be called")

    driver = ParamikoDriver(
        args=None, conn_args=ParamikoConnectionArgs(host="h", username="u", password="p")
    )
    session = FakeSession()

    assert driver.send(session, []) == {}  # type: ignore
    assert session.called is False


def test_paramiko_send_runs_file_transfer(monkeypatch):
    """Use file_transfer branch instead of executing commands."""
    op = ParamikoFileTransferOperation(
        operation="upload", local_path="/tmp/a", remote_path="/tmp/b"
    )
    driver = ParamikoDriver(
        args=ParamikoSendCommandArgs(file_transfer=op),
        conn_args=ParamikoConnectionArgs(host="h", username="u", password="p"),
    )

    called = {}

    def fake_handle(self, session, file_transfer_op):
        called["session"] = session
        called["op"] = file_transfer_op
        return {"file_transfer_upload": {"exit_status": 0}}

    monkeypatch.setattr(ParamikoDriver, "_handle_file_transfer", fake_handle)
    fake_session = object()

    result = driver.send(fake_session, ["ignored"])  # type: ignore
    assert result == {"file_transfer_upload": {"exit_status": 0}}
    assert called["session"] is fake_session
    assert called["op"] == op


def test_paramiko_config_with_sudo(monkeypatch):
    """Prefix commands with sudo and request PTY when sudo_password is set."""

    class FakeChannel:
        def recv_exit_status(self):
            return 0

    class FakeIO:
        def __init__(self, payload: str = ""):
            self._payload = payload
            self.channel = FakeChannel()
            self.writes = []

        def read(self):
            return self._payload.encode()

        def write(self, data):
            self.writes.append(data)

        def flush(self):
            return None

    class FakeSession:
        def __init__(self):
            self.exec_calls = []

        def exec_command(self, cmd, **kwargs):
            self.exec_calls.append((cmd, kwargs))
            return FakeIO(), FakeIO("ok"), FakeIO("")

    session = FakeSession()
    driver = ParamikoDriver(
        args=ParamikoSendConfigArgs(sudo=True, sudo_password="pw", get_pty=False),
        conn_args=ParamikoConnectionArgs(host="h", username="u", password="p"),
    )

    result = driver.config(session, ["echo 1"])  # type: ignore
    assert "echo 1" in result
    cmd, kwargs = session.exec_calls[0]
    assert cmd.startswith("sudo -S")
    assert kwargs["get_pty"] is True  # sudo + password should force PTY
    assert result["echo 1"]["exit_status"] == 0


def test_paramiko_config_returns_empty_when_no_config():
    """Return empty dict and skip exec when no config lines are provided."""

    class FakeSession:
        def __init__(self):
            self.called = False

        def exec_command(self, *_args, **_kwargs):
            self.called = True
            raise AssertionError("should not be called")

    driver = ParamikoDriver(
        args=ParamikoSendConfigArgs(),
        conn_args=ParamikoConnectionArgs(host="h", username="u", password="p"),
    )
    session = FakeSession()

    assert driver.config(session, []) == {}  # type: ignore
    assert session.called is False


def test_paramiko_test_returns_remote_version(monkeypatch):
    """ParamikoDriver.test should populate host and remote_version and close session."""

    class FakeTransport:
        remote_version = "SSH-2.0-fake"

    class FakeSession:
        def __init__(self):
            self.closed = False

        def get_transport(self):
            return FakeTransport()

        def close(self):
            self.closed = True

    fake_session = FakeSession()

    def fake_connect(self):
        return fake_session

    monkeypatch.setattr(ParamikoDriver, "connect", fake_connect)

    result = ParamikoDriver.test(ParamikoConnectionArgs(host="h", username="u", password="p"))

    assert result.host == "h"
    assert result.remote_version == "SSH-2.0-fake"
    assert fake_session.closed is True
