import logging
from typing import Any

import requests
import rq

from .. import BaseWebHookCaller, WebHook

log = logging.getLogger(__name__)


class BasicWebHookCaller(BaseWebHookCaller):
    webhook_name = "basic"

    def __init__(self, hook: WebHook):
        self.config = hook

    def call(self, req: Any, job: rq.job.Job, result: Any, **kwargs):
        # Determine success status and format result
        # Top 1 Alignment: Keep the result as a rich dict/object if possible
        is_success = job.get_status() == "finished"

        # If result is an exception tuple from rpc_exception_callback
        if isinstance(result, tuple) and len(result) == 2:
            is_success = False
            result_payload = {"error": f"{result[0]}: {result[1]}"}
        else:
            result_payload = result

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

    def _format_dict_result(self, result: dict) -> str:
        """
        Format dictionary result (multiple commands) into a readable string.
        Handles both simple dict format: {"cmd": "output"}
        and nested dict format: {"cmd": {"output": "...", "error": "...", "exit_status": 0}}
        """
        if not result:
            return "{}"

        lines = []
        for cmd, output in result.items():
            lines.append(f"Command: {cmd}")
            if isinstance(output, dict):
                # Handle nested dict format (e.g., paramiko driver)
                if "output" in output:
                    lines.append(f"Output:\n{output['output']}")
                if "error" in output and output.get("error"):
                    lines.append(f"Error: {output['error']}")
                if "exit_status" in output:
                    lines.append(f"Exit Status: {output['exit_status']}")
            else:
                # Simple string output
                lines.append(f"Output:\n{output}")
            lines.append("")  # Empty line between commands

        return "\n".join(lines).rstrip()


__all__ = ["BasicWebHookCaller"]
