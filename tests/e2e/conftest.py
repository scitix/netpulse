import logging
import os
import socket
from pathlib import Path

import pytest

from .settings import get_linux_ssh_target, get_redis_target, get_srl_target

log = logging.getLogger(__name__)


def pytest_configure(config):
    enabled, reason = _should_enable_e2e(config)
    config._e2e_enabled = enabled  # type: ignore[attr-defined]

    _info(config, "e2e tests enabled" if enabled else "e2e tests disabled", reason)


def pytest_collection_modifyitems(config, items):
    if getattr(config, "_e2e_enabled", False):
        return

    skip_marker = pytest.mark.skip(reason="e2e disabled; use --e2e or start lab services")
    for item in items:
        if "e2e" in item.keywords:
            item.add_marker(skip_marker)


def _should_enable_e2e(config) -> tuple[bool, str]:
    if config.getoption("--no-e2e"):
        return False, "forced off with --no-e2e"
    if config.getoption("--e2e"):
        return True, "--e2e flag set"

    reachable, details = _are_lab_services_reachable()
    if reachable:
        return True, f"lab reachable ({details})"
    return False, f"lab not reachable ({details})"


def _are_lab_services_reachable() -> tuple[bool, str]:
    checks = [
        ("ssh1", get_linux_ssh_target().host, get_linux_ssh_target().port),
        ("redis1", *get_redis_target()),
        ("srl1", get_srl_target().host, get_srl_target().port),
    ]
    failures: list[str] = []
    for name, host, port in checks:
        if not _tcp_ping(host, port, timeout=1.0):
            failures.append(f"{name} {host}:{port}")
    if failures:
        return False, f"unreachable: {', '.join(failures)}"
    return True, "all endpoints reachable"


@pytest.fixture(autouse=True)
def _configure_e2e_env(request):
    """Switch to e2e config for e2e-marked tests only."""
    if not getattr(request.config, "_e2e_enabled", False):
        return
    if "e2e" not in request.keywords:
        return

    base_dir = Path(__file__).resolve().parents[1]
    e2e_cfg = base_dir / "data" / "config.e2e.yaml"

    saved = {
        "NETPULSE_CONFIG_FILE": os.environ.get("NETPULSE_CONFIG_FILE"),
        "NETPULSE_SERVER__API_KEY": os.environ.get("NETPULSE_SERVER__API_KEY"),
        "NETPULSE_FAKE_REDIS": os.environ.get("NETPULSE_FAKE_REDIS"),
    }

    os.environ["NETPULSE_CONFIG_FILE"] = str(e2e_cfg)
    os.environ["NETPULSE_SERVER__API_KEY"] = "E2E_API_KEY"
    os.environ["NETPULSE_FAKE_REDIS"] = "0"

    import importlib

    from netpulse import utils
    from netpulse.services import manager, rediz

    importlib.reload(utils)
    importlib.reload(rediz)
    importlib.reload(manager)

    yield

    # Restore previous environment and reload back.
    for key, val in saved.items():
        if val is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = val

    importlib.reload(utils)
    importlib.reload(rediz)
    importlib.reload(manager)


def _tcp_ping(host: str, port: int, timeout: float = 1.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def _info(config, msg: str, detail: str):
    reporter = config.pluginmanager.get_plugin("terminalreporter")
    line = f"{msg}: {detail}"
    if reporter:
        reporter.write_line(line)
    else:
        log.info(line)
