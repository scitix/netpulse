from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict, Field


class DriverExecutionResult(BaseModel):
    """
    Standardized result for a single command or config operation.
    """

    command: str = ""
    stdout: Any = ""
    stderr: str = ""
    exit_status: int = 0
    download_url: Optional[str] = None  # Formal field for file resources
    metadata: Dict[str, Any] = Field(default_factory=dict)
    parsed: Optional[Any] = None

    model_config = ConfigDict(
        populate_by_name=True,
        json_schema_extra={
            "example": {
                "command": "show version",
                "stdout": "Arista vEOS\nHardware version: 4.25.4M",
                "stderr": "",
                "exit_status": 0,
                "download_url": None,
                "metadata": {
                    "host": "172.17.0.1",
                    "duration_seconds": 0.123,
                    "session_reused": True,
                },
                "parsed": {"version": "4.25.4M", "model": "vEOS"},
            }
        }
    )
