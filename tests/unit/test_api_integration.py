
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from rq import Queue

from netpulse import controller


@pytest.fixture
def api_client():
    return TestClient(controller.app)

@pytest.mark.api
class TestAPIIntegration:
    """
    Integration tests that use real Manager logic but mocked Redis/Drivers
    to catch serialization and enqueueing issues.
    """

    def test_device_exec_real_manager_flow(self, api_client, app_config, monkeypatch, unit_runtime):
        """
        Catches normalization/serialization errors in the actual Manager._send_job logic.
        """
        # 1. Mock Driver validation and RPC initialization
        mock_driver_cls = MagicMock()

        # Target the modules directly
        # Ensure Manager uses fakeredis
        with patch("netpulse.routes.device.drivers", {"netmiko": mock_driver_cls}), \
             patch("netpulse.services.rpc.drivers", {"netmiko": mock_driver_cls}), \
             patch("netpulse.services.manager.g_mgr.rdb", unit_runtime.redis):

            # Mock _check_worker_alive to always return True
            monkeypatch.setattr(
                "netpulse.services.manager.g_mgr._check_worker_alive", lambda q: True
            )

            payload = {
                "driver": "netmiko",
                "connection_args": {"host": "1.2.3.4", "username": "test", "password": "test"},
                "command": "display version",
                "queue_strategy": "fifo"
            }

            # 2. Perform the request
            resp = api_client.post(
                "/device/exec",
                json=payload,
                headers={"X-API-KEY": app_config.server.api_key}
            )

            # 3. Verify results
            assert resp.status_code == 201
            job_id = resp.json()["id"]

            # 4. Inspect the actual Redis (fakeredis)
            q = Queue("FifoQ", connection=unit_runtime.redis)
            job = q.fetch_job(job_id)

            # In RQ 1.1x+, it's success_callback
            assert "rpc_webhook_callback" in str(job.success_callback)
            assert not isinstance(job.success_callback, list)

    def test_system_stats_endpoint(self, api_client, app_config):
        """
        Verify the new /system/stats endpoint.
        """
        from netpulse.models.response import SystemStatsResponse

        resp = api_client.get(
            "/system/stats",
            headers={"X-API-KEY": app_config.server.api_key}
        )
        assert resp.status_code == 200
        data = resp.json()
        SystemStatsResponse.model_validate(data)
        assert "jobs" in data
        assert "nodes" in data

    def test_detached_tasks_list_endpoint(self, api_client, app_config):
        """
        Verify the /detached-tasks endpoint.
        """
        mock_mgr = MagicMock()
        mock_mgr.list_detached_tasks.return_value = {
            "task1": {
                "task_id": "task1",
                "command": ["show ver"],
                "host": "1.1.1.1",
                "driver": "netmiko",
                "status": "running",
                "connection_args": {"host": "1.1.1.1"}
            }
        }

        with patch("netpulse.routes.detached_task.g_mgr", mock_mgr):
            resp = api_client.get(
                "/detached-tasks",
                headers={"X-API-KEY": app_config.server.api_key}
            )
            assert resp.status_code == 200
            data = resp.json()
            assert len(data) == 1
            assert data[0]["task_id"] == "task1"

    def test_timezone_serialization_helper(self, monkeypatch):
        """
        Verify the timezone serialization logic directly.
        """
        from datetime import datetime

        from netpulse.models.response import _serialize_datetime_with_tz

        naive_dt = datetime(2024, 5, 20, 10, 0, 0)

        # Test Asia/Shanghai
        monkeypatch.setenv("TZ", "Asia/Shanghai")
        serialized_sh = _serialize_datetime_with_tz(naive_dt)
        assert "+08:00" in serialized_sh

        # Test UTC
        monkeypatch.setenv("TZ", "UTC")
        serialized_utc = _serialize_datetime_with_tz(naive_dt)
        assert "Z" in serialized_utc or "+00:00" in serialized_utc
