import logging
from datetime import datetime, timezone
from typing import Any

import requests

from netpulse.models.common import RESULT_TYPE_NAMES, WebhookPayload

from .. import BaseWebHookCaller, WebHook

log = logging.getLogger(__name__)


class BasicWebHookCaller(BaseWebHookCaller):
    webhook_name = "basic"

    def __init__(self, hook: WebHook):
        self.config = hook

    def build_payload(self, req: Any, job: Any, result: Any, is_success: bool, **kwargs) -> dict:
        """Build the JSON payload dict for webhook delivery.

        The payload is aligned with JobInResponse but optimized for webhook consumers:
        - result.type uses self-describing strings instead of integers
        - Includes device connection info (host, device_type) from the request
        - Includes event_type and timestamp for webhook-specific context
        - Omits internal scheduling fields (queue, worker, enqueued_at)
        """
        event_type = kwargs.get("event_type") or ("job.completed" if is_success else "job.failed")
        timestamp = datetime.now(timezone.utc).isoformat()

        # Build result dict with string type (aligned with JobResult but self-describing)
        result_dict = self._build_result(job, result, is_success)

        # Build device info from request connection_args
        device_info = self._build_device_info(req)

        # Extract timing from job (JobInResponse or compatible object)
        started_at = self._serialize_dt(getattr(job, "started_at", None))
        ended_at = self._serialize_dt(getattr(job, "ended_at", None))
        duration = getattr(job, "duration", None)

        # final=True means no more events for this id (consumer can stop listening)
        is_final = event_type != "detached.log_push"

        payload = WebhookPayload(
            id=getattr(job, "id", "unknown"),
            status=getattr(job, "status", "failed" if not is_success else "finished"),
            event_type=event_type,
            final=is_final,
            timestamp=timestamp,
            started_at=started_at,
            ended_at=ended_at,
            duration=duration,
            result=result_dict,
            device=device_info,
            task_id=getattr(job, "task_id", None),
            device_name=getattr(job, "device_name", None),
            command=getattr(job, "command", None),
        )
        return payload.model_dump(mode="json")

    def call(self, req: Any, job: Any, result: Any, **kwargs):
        is_success = kwargs.get("is_success")
        if is_success is None:
            if hasattr(job, "get_status"):
                status = job.get_status()
                status_str = status.value if hasattr(status, "value") else str(status)
                is_success = status_str == "finished"
            else:
                is_success = getattr(job, "status", "unknown") == "finished"

        # Extract event_type from kwargs, pass separately
        # to avoid conflict with positional is_success
        event_type = kwargs.get("event_type")
        data = self.build_payload(req, job, result, is_success, event_type=event_type)

        resp = requests.request(
            method=self.config.method.value,
            url=self.config.url.unicode_string(),
            headers=self.config.headers,
            cookies=self.config.cookies,
            timeout=self.config.timeout,
            auth=self.config.auth,
            json=data,
        )
        resp.raise_for_status()
        log.debug(f"Webhook {self.config.url} called successfully")

    def _build_result(self, job: Any, result: Any, is_success: bool) -> dict:
        """Build result dict aligned with JobResult but with string type."""
        # If job has a structured result (JobInResponse), use it
        job_result = getattr(job, "result", None)
        if job_result is not None and hasattr(job_result, "model_dump"):
            result_dict = job_result.model_dump(mode="json")
            # Convert integer type to string
            if "type" in result_dict:
                result_dict["type"] = RESULT_TYPE_NAMES.get(
                    result_dict["type"], str(result_dict["type"])
                )
            return result_dict

        # Fallback: build from raw result (when job has no structured JobResult)
        if isinstance(result, tuple) and len(result) >= 2:
            return {
                "type": "failed",
                "retval": None,
                "error": {"type": str(result[0]), "message": str(result[1])},
            }
        else:
            type_str = "successful" if is_success else "failed"
            return {"type": type_str, "retval": result, "error": None}

    def _build_device_info(self, req: Any) -> dict | None:
        """Extract device connection info from request."""
        if req is None:
            return None
        conn_args = getattr(req, "connection_args", None)
        if conn_args is None:
            return None
        device_info = {}
        host = getattr(conn_args, "host", None)
        if host:
            device_info["host"] = host
        device_type = getattr(conn_args, "device_type", None)
        if device_type:
            device_info["device_type"] = device_type
        return device_info or None

    @staticmethod
    def _serialize_dt(dt) -> str | None:
        """Serialize datetime to ISO format string."""
        if dt is None:
            return None
        if hasattr(dt, "isoformat"):
            return dt.isoformat()
        return str(dt)


__all__ = ["BasicWebHookCaller"]
