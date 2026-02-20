from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class DriverExecutionResult(BaseModel):
    """
    Standardized result for a single command or config operation.
    """

    output: Any
    error: str = ""
    exit_status: int = 0
    telemetry: Dict[str, Any] = Field(default_factory=dict)
    parsed: Optional[Any] = None
