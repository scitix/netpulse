from __future__ import annotations

import importlib
import logging
import os
import socket
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Mapping

import pytest
import requests

from redis import Redis

from .settings import (
    get_api_base,
    get_api_key,
    get_linux_ssh_target,
    get_redis_config,
    get_srl_targets,
)

log = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[2]
TESTS_DIR = Path(__file__).resolve().parents[1]
E2E_CONFIG = TESTS_DIR / "data" / "config.e2e.yaml"
API_BASE = get_api_base()
API_KEY = get_api_key()
REDIS_CFG = get_redis_config()

E2E_BASE_ENV: dict[str, str] = {
    "NETPULSE_CONFIG_FILE": str(E2E_CONFIG),
    "NETPULSE_SERVER__API_KEY": API_KEY,
    "NETPULSE_FAKE_REDIS": "0",
    "NETPULSE_REDIS__HOST": REDIS_CFG.host,
    "NETPULSE_REDIS__PORT": str(REDIS_CFG.port),
    "NETPULSE_REDIS__PASSWORD": REDIS_CFG.password,
    "PYTHONPATH": str(REPO_ROOT),
    "PYTHONUNBUFFERED": "1",
}

MODULES_TO_RELOAD: tuple[str, ...] = (
    "netpulse.utils.config",
    "netpulse.utils",
    "netpulse.plugins",
    "netpulse.services.rpc",
    "netpulse.services.rediz",
    "netpulse.services.manager",
    "netpulse.routes.device",
    "netpulse.routes.template",
    "netpulse.routes.manage",
    "netpulse.server.common",
    "netpulse.worker.common",
    "netpulse.worker.node",
    "netpulse.worker.fifo",
    "netpulse.controller",
)


# Ensure collection loads the e2e config instead of falling back to production defaults.
os.environ.update(
    {
        "NETPULSE_CONFIG_FILE": str(E2E_CONFIG),
        "NETPULSE_FAKE_REDIS": "0",
    }
)

from netpulse.utils.config import AppConfig  # noqa: E402


@dataclass
class E2ERuntime:
    config: AppConfig
    redis: Redis
    env: dict[str, str]


def pytest_configure(config):
    enabled, reason = _should_enable_e2e(config)
    config._e2e_enabled = enabled  # type: ignore[attr-defined]
    reporter = config.pluginmanager.get_plugin("terminalreporter")
    line = "e2e tests enabled" if enabled else ("e2e tests disabled " + reason)
    if reporter:
        reporter.write_line(line)
    else:
        log.info(line)


def pytest_collection_modifyitems(config, items):
    e2e_enabled = getattr(config, "_e2e_enabled", False)

    if config.getoption("--e2e"):
        non_e2e = [item for item in items if "e2e" not in item.keywords]
        for item in non_e2e:
            items.remove(item)
        if non_e2e:
            config.hook.pytest_deselected(items=non_e2e)
        return

    if e2e_enabled:
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
        ("redis1", REDIS_CFG.host, REDIS_CFG.port),
        ("srl1", get_srl_targets()[0].host, get_srl_targets()[0].port),
    ]
    failures: list[str] = []
    for name, host, port in checks:
        if not _tcp_ping(host, port, timeout=1.0):
            failures.append(f"{name} {host}:{port}")
    if failures:
        return False, f"unreachable: {', '.join(failures)}"
    return True, "all endpoints reachable"


def build_e2e_env(overrides: Mapping[str, str | None] | None = None) -> dict[str, str]:
    env = os.environ.copy()
    env.update(E2E_BASE_ENV)
    for key, value in (overrides or {}).items():
        if value is None:
            env.pop(key, None)
        else:
            env[key] = str(value)
    return env


def _reload_e2e_runtime(
    monkeypatch: pytest.MonkeyPatch, overrides: Mapping[str, str | None] | None = None
) -> E2ERuntime:
    """Apply e2e env, reload config-sensitive modules, and return runtime state."""
    env = build_e2e_env(overrides)

    for key in [k for k in os.environ if k.startswith("NETPULSE_") or k == "PYTHONPATH"]:
        monkeypatch.delenv(key, raising=False)
    for key, value in env.items():
        if key.startswith("NETPULSE_") or key == "PYTHONPATH":
            monkeypatch.setenv(key, value)

    importlib.invalidate_caches()
    for module_name in MODULES_TO_RELOAD:
        module = importlib.import_module(module_name)
        importlib.reload(module)

    from netpulse import utils
    from netpulse.services import rediz

    return E2ERuntime(config=utils.g_config, redis=rediz.g_rdb.conn, env=env)


def _is_e2e_test(request: pytest.FixtureRequest) -> bool:
    return "e2e" in request.keywords and getattr(request.config, "_e2e_enabled", False)


@pytest.fixture(autouse=True)
def e2e_runtime(monkeypatch: pytest.MonkeyPatch, request) -> E2ERuntime | None:
    """Ensure each e2e test reloads NetPulse with real Redis config."""
    if not _is_e2e_test(request):
        return None
    return _reload_e2e_runtime(monkeypatch)


@pytest.fixture(scope="session")
def api_headers() -> dict[str, str]:
    return {"X-API-KEY": API_KEY}


@pytest.fixture()
def wait_for_job(api_headers: dict[str, str]) -> Callable[[str, float], dict]:
    """Poll the API for a job until it finishes or times out."""

    def _wait(job_id: str, timeout: float = 60.0) -> dict:
        deadline = time.time() + timeout
        while time.time() < deadline:
            resp = requests.get(f"{API_BASE}/jobs/{job_id}", headers=api_headers, timeout=5)

            try:
                resp.raise_for_status()
            except requests.HTTPError:
                if resp.status_code == 404:
                    time.sleep(2)
                    continue
                pytest.fail(f"Job status check failed with {resp.status_code}, resp:\n{resp.text}")

            job = resp.json()
            if job["status"] in {"finished", "failed", "stopped"}:
                return job
            if job["status"] == "unknown":
                pytest.fail(f"Job {job_id} has unknown status")

            time.sleep(2)
        pytest.fail(f"Job {job_id} did not complete within {timeout}s")

    return _wait


@pytest.fixture()
def wait_for_worker(
    e2e_runtime: E2ERuntime | None,
    api_headers: dict[str, str],
) -> Callable[[str, float, subprocess.Popen | None], None]:
    """Wait until a worker is registered on the given queue."""

    def _wait(queue: str, timeout: float = 15.0, proc: subprocess.Popen | None = None) -> None:
        if e2e_runtime is None:
            pytest.skip("e2e environment is not enabled")

        from rq import Queue, Worker

        conn = e2e_runtime.redis
        deadline = time.time() + timeout

        while time.time() < deadline:
            try:
                if Worker.all(queue=Queue(queue, connection=conn)):
                    return
            except Exception:
                pass

            try:
                resp = requests.get(
                    f"{API_BASE}/workers",
                    params={"queue": queue},
                    headers=api_headers,
                    timeout=5,
                )
                if resp.status_code == 200 and resp.json():
                    return
            except requests.RequestException:
                pass

            time.sleep(1)

        output = _read_process_output(proc)
        return_code = proc.returncode if proc else None
        pytest.fail(
            f"No worker available for queue {queue} within {timeout}s; "
            f"worker rc={return_code}\n{output}"
        )

    return _wait


def _wait_for_node_queue(runtime: E2ERuntime, timeout: float, proc: subprocess.Popen | None) -> str:
    """Wait for NodeWorker to register its node_info entry and return its queue name."""
    from netpulse.models import NodeInfo

    deadline = time.time() + timeout
    key = runtime.config.redis.key.node_info_map

    while time.time() < deadline:
        try:
            entries = runtime.redis.hgetall(key)
            for raw in entries.values():  # type: ignore
                try:
                    payload = raw.decode() if isinstance(raw, (bytes, bytearray)) else raw
                    node = NodeInfo.model_validate_json(payload)
                    if node.queue:
                        return node.queue
                except Exception:
                    continue
        except Exception:
            pass
        time.sleep(1)

    output = _read_process_output(proc)
    rc = proc.returncode if proc else None
    pytest.fail(
        f"NodeWorker did not register in Redis within {timeout}s; "
        f"node map key={key}; worker rc={rc}\n{output}"
    )


def _spawn_worker(kind: str, env: Mapping[str, str]) -> subprocess.Popen:
    cmd = [sys.executable, str(REPO_ROOT / "worker.py"), kind]
    return subprocess.Popen(cmd, cwd=REPO_ROOT, env=dict(env))


def _stop_process(proc: subprocess.Popen):
    if proc.poll() is None:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
    _read_process_output(proc)


def _read_process_output(proc: subprocess.Popen | None) -> str:
    if not proc:
        return ""
    try:
        stdout, _ = proc.communicate(timeout=1)
        return stdout.decode(errors="ignore")
    except Exception:
        return ""


@pytest.fixture
def fifo_worker(e2e_runtime: E2ERuntime | None, wait_for_worker):
    if e2e_runtime is None:
        pytest.skip("e2e environment is not enabled")

    proc = _spawn_worker("fifo", e2e_runtime.env)
    try:
        wait_for_worker(queue=e2e_runtime.config.get_fifo_queue_name(), proc=proc, timeout=30.0)
        yield proc
    finally:
        _stop_process(proc)


@pytest.fixture
def node_worker(e2e_runtime: E2ERuntime | None, wait_for_worker):
    if e2e_runtime is None:
        pytest.skip("e2e environment is not enabled")

    proc = _spawn_worker("node", e2e_runtime.env)
    try:
        node_q = _wait_for_node_queue(runtime=e2e_runtime, timeout=30.0, proc=proc)
        wait_for_worker(queue=node_q, proc=proc, timeout=30.0)
        yield proc
    finally:
        _stop_process(proc)


@pytest.fixture(scope="session")
def api_server(request):
    """Start a real FastAPI server for e2e tests and stop after suite."""
    if not getattr(request.config, "_e2e_enabled", False):
        yield
        return

    env = build_e2e_env()
    cmd = [
        sys.executable,
        "-m",
        "uvicorn",
        "netpulse.controller:app",
        "--host",
        "0.0.0.0",
        "--port",
        str(os.getenv("E2E_API_PORT", "8000")),
    ]
    proc = subprocess.Popen(
        cmd, cwd=REPO_ROOT, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT
    )

    deadline = time.time() + 30
    try:
        while time.time() < deadline:
            try:
                resp = requests.get(
                    f"{API_BASE}/health",
                    timeout=2,
                    headers={"X-API-KEY": API_KEY},
                )
                if resp.status_code == 200:
                    break
            except requests.RequestException:
                pass
            if proc.poll() is not None:
                output = _read_process_output(proc)
                raise RuntimeError(f"API server exited early with code {proc.returncode}\n{output}")
            time.sleep(0.5)
        else:
            output = _read_process_output(proc)
            raise RuntimeError(f"API server did not become ready within timeout\n{output}")

        yield
    finally:
        _stop_process(proc)


def _tcp_ping(host: str, port: int, timeout: float = 1.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False
