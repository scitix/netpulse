import sys
import textwrap

import pytest
import requests

from netpulse.models import DriverName
from netpulse.plugins.drivers.netmiko import NetmikoDriver
from netpulse.plugins.drivers.netmiko.model import (
    NetmikoConnectionArgs,
    NetmikoExecutionRequest,
    NetmikoSendConfigSetArgs,
)
from netpulse.services import rpc
from tests.e2e.settings import (
    get_api_base,
    get_api_key,
    get_linux_ssh_target,
    get_srl_targets,
    is_reachable,
)

pytestmark = pytest.mark.e2e

API_BASE = get_api_base()


def _api_headers() -> dict[str, str]:
    return {"X-API-KEY": get_api_key()}


def test_netmiko_exec_on_linux_ssh():
    """Run a command on the Linux SSH host via Netmiko."""
    target = get_linux_ssh_target()

    if not is_reachable(target.host, target.port):
        msg = (
            f"OpenSSH device at {target.host}:{target.port} unreachable; ensure ContainerLab is up"
        )
        pytest.skip(msg)

    req = NetmikoExecutionRequest(
        driver=DriverName.NETMIKO,
        connection_args=NetmikoConnectionArgs(
            device_type="linux",
            host=target.host,
            username=target.username,
            password=target.password,
            port=target.port,
            keepalive=None,
        ),
        command=target.command,
    )

    result = rpc.execute(req)

    assert target.command in result
    assert "netpulse-e2e" in result[target.command]


def test_netmiko_exec_on_srlinux(monkeypatch):
    """Run a show command on SR Linux via Netmiko (skip if auth/conn fails)."""
    target = get_srl_targets()[0]

    if not is_reachable(target.host, target.port):
        pytest.skip(f"SR Linux at {target.host}:{target.port} unreachable; ensure lab is up")

    netmiko_module = sys.modules["netpulse.plugins.drivers.netmiko"]
    monkeypatch.setattr(netmiko_module.os, "kill", lambda pid, sig: None)
    monkeypatch.setattr(netmiko_module.sys, "exit", lambda code=0: None)

    req = NetmikoExecutionRequest(
        driver=DriverName.NETMIKO,
        connection_args=NetmikoConnectionArgs(
            device_type="nokia_srl",
            host=target.host,
            username=target.username,
            password=target.password or "",
            port=target.port,
            keepalive=None,
        ),
        command=target.command,
    )

    try:
        result = rpc.execute(req)
    except Exception as exc:
        pytest.skip(f"SR Linux auth/connection failed: {exc}")

    assert target.command in result
    assert isinstance(result[target.command], str)
    assert result[target.command].strip()


def test_netmiko_config_on_srlinux(monkeypatch):
    """Push a simple config on SR Linux via Netmiko (skip if auth/conn fails)."""
    target = get_srl_targets()[0]

    if not is_reachable(target.host, target.port):
        pytest.skip(f"SR Linux at {target.host}:{target.port} unreachable; ensure lab is up")

    netmiko_module = sys.modules["netpulse.plugins.drivers.netmiko"]
    monkeypatch.setattr(netmiko_module.os, "kill", lambda pid, sig: None)
    monkeypatch.setattr(netmiko_module.sys, "exit", lambda code=0: None)

    conn_args = NetmikoConnectionArgs(
        device_type="nokia_srl",
        host=target.host,
        username=target.username,
        password=target.password or "",
        port=target.port,
        keepalive=None,
    )
    cfg_lines = ['set / system gnmi-server admin-state "enable"']

    req = NetmikoExecutionRequest(
        driver=DriverName.NETMIKO,
        connection_args=conn_args,
        driver_args=NetmikoSendConfigSetArgs(),
        config=cfg_lines,
    )

    try:
        result = rpc.execute(req)
    except Exception as exc:
        pytest.skip(f"SR Linux auth/connection failed: {exc}")

    assert isinstance(result, list)
    assert result and all(isinstance(item, str) for item in result)


def test_netmiko_reuses_persisted_session(monkeypatch):
    """Ensure Netmiko reuses a persisted session across multiple commands."""
    target = get_linux_ssh_target()

    if not is_reachable(target.host, target.port):
        pytest.skip(f"Linux SSH at {target.host}:{target.port} unreachable; ensure lab is up")

    netmiko_module = sys.modules["netpulse.plugins.drivers.netmiko"]
    monkeypatch.setattr(netmiko_module.os, "kill", lambda pid, sig: None)
    monkeypatch.setattr(netmiko_module.sys, "exit", lambda code=0: None)

    connect_calls: list[str] = []
    orig_connect = netmiko_module.ConnectHandler

    def spy_connect(**kwargs):
        connect_calls.append(kwargs["host"])
        return orig_connect(**kwargs)

    monkeypatch.setattr(netmiko_module, "ConnectHandler", spy_connect)

    set_calls: list[object] = []
    orig_set = NetmikoDriver._set_persisted_session

    def spy_set(cls, session, conn_args):
        set_calls.append(session)
        return orig_set.__func__(cls, session, conn_args)

    monkeypatch.setattr(NetmikoDriver, "_set_persisted_session", classmethod(spy_set))

    conn_args = NetmikoConnectionArgs(
        device_type="linux",
        host=target.host,
        username=target.username,
        password=target.password,
        port=target.port,
        keepalive=30,
    )

    try:
        for cmd in ["echo reuse-1", "echo reuse-2"]:
            req = NetmikoExecutionRequest(
                driver=DriverName.NETMIKO,
                connection_args=conn_args,
                command=cmd,
            )
            result = rpc.execute(req)
            assert cmd in result
            assert "reuse" in result[cmd]

        non_none_sets = [s for s in set_calls if s]
        assert len(non_none_sets) == 1, "persisted session should be set once"
        assert len(connect_calls) == 1, "ConnectHandler should be called once"
    finally:
        if NetmikoDriver.persisted_session:
            driver = NetmikoDriver(args=None, conn_args=conn_args)
            driver.disconnect(NetmikoDriver.persisted_session, reset=True)


def test_api_exec_netmiko_pinned(node_worker, api_server, wait_for_job):
    """End-to-end: POST /device/exec with Netmiko should use pinned host queue."""
    target = get_linux_ssh_target()
    if not is_reachable(target.host, target.port):
        pytest.skip(f"Linux SSH at {target.host}:{target.port} unreachable; ensure lab is up")

    cmd = "echo api-netmiko-e2e"
    payload = {
        "driver": "netmiko",
        "connection_args": {
            "device_type": "linux",
            "host": target.host,
            "username": target.username,
            "password": target.password,
            "port": target.port,
            "keepalive": 5,
        },
        "command": cmd,
    }

    try:
        resp = requests.post(
            f"{API_BASE}/device/exec",
            json=payload,
            headers=_api_headers(),
            timeout=10,
        )
    except requests.exceptions.RequestException as exc:
        pytest.skip(f"API unreachable at {API_BASE}: {exc}")

    assert resp.status_code == 201, resp.text
    body = resp.json()
    job = body["data"]
    assert job["queue"] == f"HostQ_{target.host}"

    finished = wait_for_job(job_id=job["id"])
    assert finished["status"] == "finished"
    result = finished["result"]["retval"]
    assert cmd in result
    assert "api-netmiko-e2e" in result[cmd]


def test_api_netmiko_srl_render_and_parse(node_worker, api_server, wait_for_job):
    """End-to-end: SR Linux exec should render commands via Jinja2 and parse output via TextFSM."""
    target = get_srl_targets()[0]
    if not is_reachable(target.host, target.port):
        pytest.skip(f"SR Linux at {target.host}:{target.port} unreachable; ensure lab is up")

    # Render a command using Jinja2 and parse the response with a permissive TextFSM template.
    textfsm_template = textwrap.dedent(
        r"""
        Value SYSNAME (.+)

        Start
          ^System name: +${SYSNAME} -> Record
        """
    ).strip()

    payload = {
        "driver": "netmiko",
        "connection_args": {
            "device_type": "nokia_srl",
            "host": target.host,
            "username": target.username,
            "password": target.password or "",
            "port": target.port,
            "keepalive": 10,
        },
        "command": {"base_cmd": target.command},
        "rendering": {"name": "jinja2", "template": "{{ base_cmd }}"},
        "parsing": {"name": "textfsm", "template": textfsm_template},
    }

    try:
        resp = requests.post(
            f"{API_BASE}/device/exec",
            json=payload,
            headers=_api_headers(),
            timeout=10,
        )
    except requests.exceptions.RequestException as exc:
        pytest.skip(f"API unreachable at {API_BASE}: {exc}")

    assert resp.status_code == 201, resp.text
    job = resp.json()["data"]
    assert job["queue"] == f"HostQ_{target.host}"

    finished = wait_for_job(job_id=job["id"], timeout=120)
    assert finished["status"] == "finished"
    retval = finished["result"]["retval"]
    assert isinstance(retval, dict) and retval, "expected parsed output keyed by command"
    rendered_cmd = next(iter(retval.keys()))
    parsed = retval[rendered_cmd]
    assert isinstance(parsed, list), "TextFSM parser should return a list of records"


def test_api_netmiko_srl_bulk_exec(node_worker, api_server, wait_for_job):
    """End-to-end: bulk Netmiko exec against multiple SR Linux devices via /device/bulk."""
    reachable_targets = [
        t
        for t in get_srl_targets()
        if is_reachable(t.host, t.port)  # type: ignore[arg-type]
    ]
    if len(reachable_targets) < 2:
        pytest.skip("Need at least two reachable SR Linux devices for bulk execution")

    targets = reachable_targets[:2]
    base_conn = {
        "device_type": "nokia_srl",
        "host": targets[0].host,
        "username": targets[0].username,
        "password": targets[0].password or "",
        "port": targets[0].port,
        "keepalive": 10,
    }

    devices = [
        {
            "host": t.host,
            "username": t.username,
            "password": t.password or "",
            "port": t.port,
        }
        for t in targets
    ]

    cmd = targets[0].command or "show system information"
    payload = {
        "driver": "netmiko",
        "connection_args": base_conn,
        "command": cmd,
        "devices": devices,
    }

    resp = requests.post(
        f"{API_BASE}/device/bulk",
        json=payload,
        headers=_api_headers(),
        timeout=15,
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()["data"]
    succeeded = body["succeeded"]
    failed = body["failed"]

    assert len(succeeded) == len(devices)
    assert failed == []

    for job in succeeded:
        finished = wait_for_job(job_id=job["id"], timeout=120)
        assert finished["status"] == "finished"
        retval = finished["result"]["retval"]
        assert isinstance(retval, dict) and retval, "expected command output per host"
        # Since bulk returns list in order, ensure each job got output for the issued command.
        assert cmd in retval
