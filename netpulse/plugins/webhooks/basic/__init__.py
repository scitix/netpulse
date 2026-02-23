import logging
from typing import Any

import requests

from netpulse.models.driver import DriverExecutionResult

from .. import BaseWebHookCaller, WebHook

log = logging.getLogger(__name__)


class BasicWebHookCaller(BaseWebHookCaller):
    webhook_name = "basic"

    def __init__(self, hook: WebHook):
        self.config = hook

    def call(self, req: Any, job: Any, result: Any, **kwargs):
        # Determine success status and format result
        is_success = kwargs.get("is_success")
        if is_success is None:
            # Fallback logic if is_success not explicitly passed
            if hasattr(job, "get_status"):
                status = job.get_status()
                # Handle RQ JobStatus enum (which has .value) or raw string
                status_str = status.value if hasattr(status, "value") else str(status)
                is_success = status_str == "finished"
            else:
                # JobInResponse or other objects
                is_success = getattr(job, "status", "unknown") == "finished"

        # If result is an exception tuple or JobAdditionalData (containing error)
        if isinstance(result, tuple) and len(result) == 2:
            is_success = False
            result_payload = f"{result[0]}: {result[1]}"
        elif hasattr(result, "error") and result.error:
            # Handle JobAdditionalData or similar models
            is_success = False
            exc_type, exc_msg = result.error
            result_payload = f"{exc_type}: {exc_msg}"
        elif isinstance(result, list):
            # Use the formatting logic for list results
            result_payload = self._format_result(result)
        else:
            result_payload = str(result)

        # Build webhook payload with comprehensive information
        data = {
            "id": job.id,
            "status": "success" if is_success else "failed",
            "result": result_payload,
        }

        # Add device information
        if req:
            conn_args = getattr(req, "connection_args", None)
            if conn_args:
                device_info = {}
                host = getattr(conn_args, "host", None)
                if host:
                    device_info["host"] = host
                device_type = getattr(conn_args, "device_type", None)
                if device_type:
                    device_info["device_type"] = device_type
                if device_info:
                    data["device"] = device_info

            # Add driver information
            driver = getattr(req, "driver", None)
            if driver:
                data["driver"] = driver.value if hasattr(driver, "value") else str(driver)

            # Add command or config information
            command = getattr(req, "command", None)
            if command is not None:
                if isinstance(command, list):
                    data["command"] = "\n".join(command) if command else None
                else:
                    data["command"] = str(command)
            else:
                config = getattr(req, "config", None)
                if config is not None:
                    if isinstance(config, list):
                        data["config"] = "\n".join(config) if config else None
                    elif isinstance(config, dict):
                        data["config"] = str(config)
                    else:
                        data["config"] = str(config)

        try:
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
        except Exception as e:
            log.warning(f"Failed to call webhook {self.config.url}: {e}")
        else:
            log.debug(f"Webhook {self.config.url} called successfully")

    def _format_result(self, result: list) -> str:
        """
        Format list result (multiple commands) into a readable string.
        """
        if not result:
            return "[]"

        lines = []
        for res in result:
            # Handle DriverExecutionResult object
            if isinstance(res, DriverExecutionResult):
                lines.append(f"Command: {res.command}")
                lines.append(f"Output:\n{res.output}")
                if res.error:
                    lines.append(f"Error: {res.error}")
                lines.append(f"Exit Status: {res.exit_status}")
            elif isinstance(res, dict):
                # Handle dict format (e.g., if somehow a dict is passed in the list)
                cmd = res.get("command", "unknown")
                lines.append(f"Command: {cmd}")
                if "output" in res:
                    lines.append(f"Output:\n{res['output']}")
                if "error" in res and res.get("error"):
                    lines.append(f"Error: {res['error']}")
                if "exit_status" in res:
                    lines.append(f"Exit Status: {res['exit_status']}")
            else:
                # Simple string or other output
                lines.append(str(res))
            lines.append("")  # Empty line between commands

        return "\n".join(lines).rstrip()


__all__ = ["BasicWebHookCaller"]
