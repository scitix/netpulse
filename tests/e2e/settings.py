import os
import socket
from dataclasses import dataclass


@dataclass
class SSHTarget:
    host: str
    username: str
    password: str
    port: int = 22
    command: str | None = None


def get_linux_ssh_target() -> SSHTarget:
    return SSHTarget(
        host=os.getenv("E2E_SSH_HOST", "172.20.20.21"),
        username=os.getenv("E2E_SSH_USER", "netpulse"),
        password=os.getenv("E2E_SSH_PASS", "netpulse"),
        port=int(os.getenv("E2E_SSH_PORT", "2222")),
        command=os.getenv("E2E_SSH_CMD", "echo netpulse-e2e"),
    )


def get_srl_target() -> SSHTarget:
    return SSHTarget(
        host=os.getenv("E2E_SRL_HOST", "172.20.20.11"),
        username=os.getenv("E2E_SRL_USER", "admin"),
        password=os.getenv("E2E_SRL_PASS", "NokiaSrl1!"),
        port=int(os.getenv("E2E_SRL_PORT", "22")),
        command=os.getenv("E2E_SRL_CMD", "show system information"),
    )


def get_redis_target() -> tuple[str, int]:
    return (
        os.getenv("E2E_REDIS_HOST", "172.20.20.30"),
        int(os.getenv("E2E_REDIS_PORT", "6379")),
    )


def is_reachable(host: str, port: int, timeout: float = 3.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False
