from __future__ import annotations

import importlib
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterator, Mapping

import pytest

from redis import Redis

BASE_DIR = Path(__file__).resolve().parents[1]
TEST_CONFIG = BASE_DIR / "data" / "config.test.yaml"
BASE_ENV = {
    "NETPULSE_CONFIG_FILE": str(TEST_CONFIG),
    "NETPULSE_FAKE_REDIS": "1",
}

# Modules that capture global configuration at import time and need to be reloaded
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

# Ensure collection already uses the unit-test configuration
os.environ.update(BASE_ENV)

# AppConfig must be imported after setting NETPULSE_CONFIG_FILE
from netpulse.utils.config import AppConfig  # noqa: E402


@dataclass
class UnitRuntime:
    config: AppConfig
    redis: Redis


def _apply_unit_env(
    monkeypatch: pytest.MonkeyPatch, overrides: Mapping[str, str | None] | None = None
) -> None:
    """Reset NETPULSE_ env vars and apply overrides for this test."""
    for key in [k for k in os.environ if k.startswith("NETPULSE_")]:
        monkeypatch.delenv(key, raising=False)

    merged = {**BASE_ENV, **(overrides or {})}
    for key, value in merged.items():
        if value is None:
            continue
        monkeypatch.setenv(key, value)


def _reload_runtime() -> UnitRuntime:
    importlib.invalidate_caches()
    for module_name in MODULES_TO_RELOAD:
        module = importlib.import_module(module_name)
        importlib.reload(module)

    from netpulse import utils
    from netpulse.services import rediz

    conn: Redis = rediz.g_rdb.conn  # type: ignore[assignment]
    conn.flushall()
    return UnitRuntime(config=utils.g_config, redis=conn)


@pytest.fixture(scope="function", autouse=True)
def unit_runtime(monkeypatch: pytest.MonkeyPatch) -> Iterator[UnitRuntime]:
    """
    Force each test to start with a clean configuration and fresh fakeredis instance.
    """
    _apply_unit_env(monkeypatch)
    runtime = _reload_runtime()
    yield runtime
    runtime.redis.flushall()


@pytest.fixture()
def app_config(unit_runtime: UnitRuntime) -> AppConfig:
    """
    Load NetPulse modules with the test configuration and fakeredis.
    """
    return unit_runtime.config


@pytest.fixture()
def fake_redis_conn(unit_runtime: UnitRuntime) -> Iterator[Redis]:
    conn = unit_runtime.redis
    conn.flushall()
    try:
        yield conn
    finally:
        conn.flushall()


@pytest.fixture()
def runtime_loader(
    monkeypatch: pytest.MonkeyPatch,
) -> Callable[[Mapping[str, str | None] | None], UnitRuntime]:
    """
    Reload NetPulse with custom NETPULSE_* overrides inside a test.
    """

    def _loader(env_overrides: Mapping[str, str | None] | None = None) -> UnitRuntime:
        _apply_unit_env(monkeypatch, env_overrides)
        return _reload_runtime()

    return _loader
