import socket

import pytest
import requests

from netpulse import utils
from tests.e2e.settings import get_api_base, get_api_key

pytestmark = pytest.mark.e2e

API_BASE = get_api_base()


def _headers() -> dict[str, str]:
    return {"X-API-KEY": get_api_key()}


def test_health_endpoint_returns_success(api_server):
    """Health check endpoint should respond with a success payload."""
    resp = requests.get(f"{API_BASE}/health", headers=_headers(), timeout=5)
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"


def test_job_list_empty_when_no_jobs(api_server):
    """Listing jobs without enqueues should return an empty list."""
    resp = requests.get(f"{API_BASE}/jobs", headers=_headers(), timeout=5)
    assert resp.status_code == 200
    body = resp.json()
    assert body == []


def test_worker_list_reports_fifo_worker(fifo_worker, api_server):
    """FIFO worker process should be visible via /workers listing."""
    fifo_queue = utils.g_config.get_fifo_queue_name()
    resp = requests.get(
        f"{API_BASE}/workers", params={"queue": fifo_queue}, headers=_headers(), timeout=5
    )
    assert resp.status_code == 200
    workers = resp.json()
    assert any(fifo_queue in (w.get("queues") or []) for w in workers)


def test_worker_list_reports_node_worker(node_worker, api_server):
    """Node worker should register its queue and appear in /workers listing."""
    node_queue = utils.g_config.get_node_queue_name(socket.gethostname())
    resp = requests.get(
        f"{API_BASE}/workers", params={"queue": node_queue}, headers=_headers(), timeout=5
    )
    assert resp.status_code == 200
    workers = resp.json()
    assert any(node_queue in (w.get("queues") or []) for w in workers)
