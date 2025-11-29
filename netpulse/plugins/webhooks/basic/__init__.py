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
        # Convert result to string and determine success status
        is_success = True
        if isinstance(result, tuple) and len(result) == 2:
            # Error tuple format: (exc_type, exc_value)
            is_success = False
            result_str = f"({result[0]}, {result[1]})"
        elif isinstance(result, str):
            result_str = result
            # Check if result string contains error tuple format
            if result_str.startswith("('") and result_str.endswith("')"):
                is_success = False
        elif isinstance(result, dict):
            # Format dictionary result (multiple commands) in a readable way
            result_str = self._format_dict_result(result)
        else:
            result_str = str(result)

        # Build webhook payload with comprehensive information
        data = {
            "id": job.id,
            "result": result_str,
            "status": "success" if is_success else "failed",
        }

        # Add device information
        if req and hasattr(req, "connection_args") and req.connection_args:
            device_info = {}
            if hasattr(req.connection_args, "host") and req.connection_args.host:
                device_info["host"] = req.connection_args.host
            if hasattr(req.connection_args, "device_type") and req.connection_args.device_type:
                device_info["device_type"] = req.connection_args.device_type
            if device_info:
                data["device"] = device_info

        # Add driver information
        if req and hasattr(req, "driver"):
            data["driver"] = req.driver.value if hasattr(req.driver, "value") else str(req.driver)

        # Add command or config information
        if req:
            if hasattr(req, "command") and req.command is not None:
                # Convert command to string if it's a list
                if isinstance(req.command, list):
                    data["command"] = "\n".join(req.command) if req.command else None
                else:
                    data["command"] = str(req.command)
            elif hasattr(req, "config") and req.config is not None:
                # Convert config to string if it's a list or dict
                if isinstance(req.config, list):
                    data["config"] = "\n".join(req.config) if req.config else None
                elif isinstance(req.config, dict):
                    data["config"] = str(req.config)
                else:
                    data["config"] = str(req.config)

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
