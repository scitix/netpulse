import sys
import time

from netpulse.plugins.drivers.netmiko import NetmikoDriver
from netpulse.plugins.drivers.netmiko.model import (
    NetmikoConnectionArgs,
    NetmikoSendCommandArgs,
    NetmikoSendConfigSetArgs,
)

netmiko_module = sys.modules["netpulse.plugins.drivers.netmiko"]


def _reset_persisted_state():
    NetmikoDriver.persisted_session = None
    NetmikoDriver.persisted_conn_args = None
    NetmikoDriver._monitor_stop_event = None
    NetmikoDriver._monitor_thread = None


def test_netmiko_send_and_config_with_stub(monkeypatch):
    """Exercise send and config with enable/commit/save on stub session."""
    calls = {"send": [], "config": [], "commit": 0, "save": 0, "enable": 0, "disable": 0}

    class FakeSession:
        def send_command(self, cmd, **kwargs):
            calls["send"].append((cmd, kwargs))
            return f"resp-{cmd}"

        def send_config_set(self, cfg, **kwargs):
            calls["config"].append((tuple(cfg), kwargs))
            return "applied"

        def commit(self):
            calls["commit"] += 1
            return "committed"

        def save_config(self):
            calls["save"] += 1
            return "saved"

        def set_base_prompt(self):
            calls["save"] += 0  # noop

        def enable(self):
            calls["enable"] += 1

        def exit_enable_mode(self):
            calls["disable"] += 1

    driver = NetmikoDriver(
        args=NetmikoSendCommandArgs(cmd_verify=True),
        conn_args=NetmikoConnectionArgs(
            device_type="linux",
            host="stub",
            username="u",
            password="p",
        ),
        enabled=True,
        save=True,
    )

    session = FakeSession()

    send_result = driver.send(session, ["a", "b"])  # type: ignore
    assert len(send_result) == 2
    assert send_result[0].command == "a"
    assert send_result[0].output == "resp-a"
    assert send_result[0].metadata is not None
    assert send_result[1].command == "b"
    assert send_result[1].output == "resp-b"
    assert calls["send"] and all(kwargs["cmd_verify"] is True for _, kwargs in calls["send"])

    driver.args = NetmikoSendConfigSetArgs(exit_config_mode=True)
    config_result = driver.config(session, ["int lo0", "desc test"])  # type: ignore
    cfg_key = "int lo0\ndesc test"
    assert config_result[0].command == cfg_key
    assert config_result[0].output == "applied\ncommitted\nsaved"
    assert config_result[0].exit_status == 0
    assert config_result[0].metadata is not None

    assert calls["commit"] == 1
    assert calls["save"] >= 1
    assert calls["enable"] == 2  # enable called in send() and config()
    assert calls["disable"] == 2


def test_netmiko_connect_reuses_persisted_session(monkeypatch):
    """Reuse cached session and skip ConnectHandler when args match."""
    conn_args = NetmikoConnectionArgs(
        device_type="linux", host="h1", username="u", password="p", keepalive=None
    )
    fake_session = object()
    NetmikoDriver.persisted_session = fake_session  # type: ignore
    NetmikoDriver.persisted_conn_args = conn_args

    def fail_connect(**_kwargs):
        raise AssertionError("ConnectHandler should not be called when session is reused")

    monkeypatch.setattr(netmiko_module, "ConnectHandler", fail_connect)
    try:
        driver = NetmikoDriver(args=None, conn_args=conn_args)
        session = driver.connect()
        assert session is fake_session
    finally:
        _reset_persisted_state()


def test_netmiko_persisted_session_drops_on_conn_args_change():
    """Drop persisted session and disconnect when connection args change."""
    old_args = NetmikoConnectionArgs(
        device_type="linux", host="old", username="u", password="p", keepalive=None
    )
    new_args = NetmikoConnectionArgs(
        device_type="linux", host="new", username="u", password="p", keepalive=None
    )

    class FakeSession:
        def __init__(self):
            self.disconnected = False

        def disconnect(self):
            self.disconnected = True

    fake_session = FakeSession()
    NetmikoDriver.persisted_session = fake_session  # type: ignore
    NetmikoDriver.persisted_conn_args = old_args

    try:
        result = NetmikoDriver._get_persisted_session(new_args)
        assert result is None
        assert fake_session.disconnected is True
        assert NetmikoDriver.persisted_session is None
        assert NetmikoDriver.persisted_conn_args is None
    finally:
        _reset_persisted_state()


def test_netmiko_commit_handles_not_implemented():
    """_commit should swallow NotImplementedError and return None."""
    driver = NetmikoDriver(
        args=None,
        conn_args=NetmikoConnectionArgs(
            device_type="linux", host="h", username="u", password="p", keepalive=None
        ),
    )

    class FakeSession:
        def commit(self):
            raise NotImplementedError

    assert driver._commit(FakeSession()) is None  # type: ignore


def test_netmiko_disconnect_resets_persisted_session():
    """disconnect(reset=True) closes session and clears persisted state."""
    conn_args = NetmikoConnectionArgs(
        device_type="linux", host="h", username="u", password="p", keepalive=None
    )

    class FakeSession:
        def __init__(self):
            self.disconnected = False

        def disconnect(self):
            self.disconnected = True

    fake_session = FakeSession()
    NetmikoDriver.persisted_session = fake_session  # type: ignore
    NetmikoDriver.persisted_conn_args = conn_args

    try:
        driver = NetmikoDriver(args=None, conn_args=conn_args)
        driver.disconnect(fake_session, reset=True)  # type: ignore

        assert fake_session.disconnected is True
        assert NetmikoDriver.persisted_session is None
        assert NetmikoDriver.persisted_conn_args is None
    finally:
        _reset_persisted_state()


def test_netmiko_test_invokes_connecthandler(monkeypatch):
    """NetmikoDriver.test should call ConnectHandler, find prompt, and disconnect."""
    conn_args = NetmikoConnectionArgs(
        device_type="linux", host="h", username="u", password="p", keepalive=None
    )
    calls: dict[str, object] = {}

    class FakeConnection:
        def __init__(self):
            self.disconnected = False

        def find_prompt(self):
            calls["find_prompt"] = True
            return "prompt#"

        def disconnect(self):
            self.disconnected = True
            calls["disconnect"] = True

    def fake_connecthandler(**kwargs):
        calls["kwargs"] = kwargs
        return FakeConnection()

    monkeypatch.setattr(netmiko_module, "ConnectHandler", fake_connecthandler)
    result = NetmikoDriver.test(conn_args)

    assert result.host == "h"
    assert result.prompt == "prompt#"
    assert calls["kwargs"]["host"] == "h"  # type: ignore
    assert calls["kwargs"]["device_type"] == "linux"  # type: ignore
    assert calls.get("disconnect") is True


def test_netmiko_monitor_thread_keepalive_and_stop(monkeypatch):
    """Monitor thread performs keepalive and can be stopped without killing process."""
    _reset_persisted_state()
    monkeypatch.setattr(netmiko_module.sys, "exit", lambda code=0: None)
    monkeypatch.setattr(netmiko_module.os, "kill", lambda pid, sig: None)

    class FakeSession:
        RETURN = "\n"

        def __init__(self):
            self.alive_checks = 0
            self.write_calls = 0
            self.clear_calls = 0

        def is_alive(self):
            self.alive_checks += 1
            return True

        def clear_buffer(self):
            self.clear_calls += 1
            return ""

        def write_channel(self, data):
            self.write_calls += 1
            return data

    session = FakeSession()
    conn_args = NetmikoConnectionArgs(
        device_type="linux", host="h", username="u", password="p", keepalive=0
    )

    NetmikoDriver._set_persisted_session(session, conn_args)  # type: ignore
    try:
        time.sleep(0.01)
        stop_event = NetmikoDriver._monitor_stop_event
        if stop_event:
            stop_event.set()
        NetmikoDriver._stop_monitor_thread()
    finally:
        _reset_persisted_state()

    assert session.alive_checks >= 1
    assert session.write_calls >= 1


def test_netmiko_monitor_thread_kills_on_unhealthy(monkeypatch):
    """Monitor thread should terminate worker when session becomes unhealthy."""
    _reset_persisted_state()
    kill_calls: list[tuple[int, int]] = []
    exit_calls: list[int] = []

    monkeypatch.setattr(netmiko_module.os, "kill", lambda pid, sig: kill_calls.append((pid, sig)))
    monkeypatch.setattr(netmiko_module.sys, "exit", lambda code=0: exit_calls.append(code))

    class FakeSession:
        RETURN = "\n"

        def __init__(self):
            self.calls = 0

        def is_alive(self):
            self.calls += 1
            return False

        def clear_buffer(self):
            return ""

        def write_channel(self, data):
            return data

    session = FakeSession()
    conn_args = NetmikoConnectionArgs(
        device_type="linux", host="h", username="u", password="p", keepalive=0
    )

    NetmikoDriver._set_persisted_session(session, conn_args)  # type: ignore
    try:
        time.sleep(0.01)
        NetmikoDriver._stop_monitor_thread()
    finally:
        _reset_persisted_state()

    assert kill_calls, "monitor should call os.kill on unhealthy session"
    assert exit_calls, "monitor should exit the thread after kill"


def test_netmiko_monitor_thread_stops_on_keepalive_error(monkeypatch):
    """Monitor thread should stop and signal kill when keepalive send fails."""
    _reset_persisted_state()
    kill_calls: list[tuple[int, int]] = []
    exit_calls: list[int] = []

    monkeypatch.setattr(netmiko_module.os, "kill", lambda pid, sig: kill_calls.append((pid, sig)))
    monkeypatch.setattr(netmiko_module.sys, "exit", lambda code=0: exit_calls.append(code))

    class FakeSession:
        RETURN = "\n"

        def __init__(self):
            self.alive_checks = 0
            self.write_calls = 0

        def is_alive(self):
            self.alive_checks += 1
            return True

        def clear_buffer(self):
            return "junk-data"

        def write_channel(self, data):
            self.write_calls += 1
            raise RuntimeError("keepalive failed")

    session = FakeSession()
    conn_args = NetmikoConnectionArgs(
        device_type="linux", host="h", username="u", password="p", keepalive=0
    )

    NetmikoDriver._set_persisted_session(session, conn_args)  # type: ignore
    try:
        time.sleep(0.02)
        NetmikoDriver._stop_monitor_thread()
    finally:
        _reset_persisted_state()

    assert session.write_calls >= 1
    assert kill_calls, "monitor should call os.kill on keepalive failure"
    assert exit_calls, "monitor should exit after keepalive failure"
