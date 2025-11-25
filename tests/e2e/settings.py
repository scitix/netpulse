from __future__ import annotations

import os
import socket
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Target:
    host: str
    username: str
    password: str
    port: int = 22
    command: str | None = None


@dataclass
class RedisTarget:
    host: str = "172.20.20.30"
    port: int = 6379
    password: str = ""


@dataclass
class ApiTarget:
    host: str = "localhost"
    port: int = 8000
    api_key: str = "E2E_API_KEY"

    @property
    def base(self) -> str:
        return f"http://{self.host}:{self.port}"


@dataclass
class LabConfig:
    """
    Centralized defaults for the ContainerLab-based e2e environment.
    Can be overridden by a small set of E2E_* env vars but keeps the
    defaults in a single place to avoid scattered overrides.
    """

    linux: Target = field(
        default_factory=lambda: Target(
            host="172.20.20.21",
            username="netpulse",
            password="netpulse",
            port=2222,
            command="echo netpulse-e2e",
        )
    )
    srl: list[Target] = field(
        default_factory=lambda: [
            Target(
                host="172.20.20.11",
                username="admin",
                password="NokiaSrl1!",
                port=22,
                command="show system information",
            ),
            Target(
                host="172.20.20.12",
                username="admin",
                password="NokiaSrl1!",
                port=22,
                command="show system information",
            ),
        ]
    )
    redis: RedisTarget = field(default_factory=RedisTarget)
    api: ApiTarget = field(default_factory=ApiTarget)


def _split_hosts(raw: str | None) -> list[str]:
    if not raw:
        return []
    return [h.strip() for h in raw.split(",") if h.strip()]


def load_lab_config(env: Any = None) -> LabConfig:
    env = env or os.environ
    cfg = LabConfig()

    # Linux host overrides
    cfg.linux.host = env.get("E2E_SSH_HOST", cfg.linux.host)
    cfg.linux.username = env.get("E2E_SSH_USER", cfg.linux.username)
    cfg.linux.password = env.get("E2E_SSH_PASS", cfg.linux.password)
    cfg.linux.port = int(env.get("E2E_SSH_PORT", cfg.linux.port))
    cfg.linux.command = env.get("E2E_SSH_CMD", cfg.linux.command)

    # SR Linux overrides:
    # allow a comma-separated host list; shared creds/port/cmd overrides apply to all.
    srl_hosts = _split_hosts(env.get("E2E_SRL_HOSTS")) or [t.host for t in cfg.srl]
    srl_user = env.get("E2E_SRL_USER", cfg.srl[0].username)
    srl_pass = env.get("E2E_SRL_PASS", cfg.srl[0].password)
    srl_port = int(env.get("E2E_SRL_PORT", cfg.srl[0].port))
    srl_cmd = env.get("E2E_SRL_CMD", cfg.srl[0].command)
    cfg.srl = [
        Target(host=h, username=srl_user, password=srl_pass, port=srl_port, command=srl_cmd)
        for h in srl_hosts
    ]

    # Redis overrides
    cfg.redis.host = env.get("E2E_REDIS_HOST", cfg.redis.host)
    cfg.redis.port = int(env.get("E2E_REDIS_PORT", cfg.redis.port))
    cfg.redis.password = env.get("E2E_REDIS_PASSWORD", cfg.redis.password)

    # API overrides
    cfg.api.host = env.get("E2E_API_HOST", cfg.api.host)
    cfg.api.port = int(env.get("E2E_API_PORT", cfg.api.port))
    cfg.api.api_key = env.get("E2E_API_KEY", cfg.api.api_key)

    return cfg


# Load once for e2e tests; consumers call getters below.
LAB_CONFIG = load_lab_config()


def get_linux_ssh_target() -> Target:
    return LAB_CONFIG.linux


def get_srl_targets() -> list[Target]:
    return LAB_CONFIG.srl


def get_redis_config() -> RedisTarget:
    return LAB_CONFIG.redis


def get_api_base() -> str:
    return LAB_CONFIG.api.base


def get_api_key() -> str:
    return LAB_CONFIG.api.api_key


def is_reachable(host: str, port: int, timeout: float = 3.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False
