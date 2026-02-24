from enum import Enum
from typing import Any, Dict, List, Literal, Optional, Tuple

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, model_validator

from .driver import DriverExecutionResult


class QueueStrategy(str, Enum):
    FIFO = "fifo"
    PINNED = "pinned"


class DriverName(str, Enum):
    NAPALM = "napalm"
    NETMIKO = "netmiko"
    PARAMIKO = "paramiko"
    PYEAPI = "pyeapi"
    # NCCLIENT = "ncclient"
    # PURESNMP = "puresnmp"
    # RESTCONF = "restconf"


class JobAdditionalData(BaseModel):
    """
    Used in rq.Job.meta.
    We can store custom data here.
    """

    error: Optional[Tuple[str, str]] = None  # 0: exc_type, 1: exc_value
    task_id: Optional[str] = None
    device_name: Optional[str] = None
    command: Optional[List[str]] = None


class JobResult(BaseModel):
    """
    A customized version of `rq.job.Result`.
    """

    class ResultType(int, Enum):
        SUCCESSFUL = 1
        FAILED = 2
        STOPPED = 3
        RETRIED = 4

    type: ResultType
    retval: Optional[list[DriverExecutionResult]] = None
    error: Optional[Any] = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "type": 1,
                "retval": [
                    {
                        "command": "show version",
                        "output": "Arista vEOS\nHardware version: 4.25.4M",
                        "error": "",
                        "exit_status": 0,
                        "download_url": None,
                        "metadata": {
                            "host": "172.17.0.1",
                            "duration_seconds": 0.123,
                            "session_reused": True,
                        },
                        "parsed": {"version": "4.25.4M", "model": "vEOS"},
                    }
                ],
                "error": {
                    "type": "ValueError",
                    "message": "Something went wrong",
                },
            }
        }
    )


class NodeInfo(BaseModel):
    hostname: str
    count: int
    capacity: int
    queue: str

    def __hash__(self):
        return hash(self.hostname)

    def __eq__(self, value):
        return self.hostname == value.hostname


class WebHook(BaseModel):
    class WebHookMethod(str, Enum):
        GET = "GET"
        POST = "POST"
        PUT = "PUT"
        DELETE = "DELETE"
        PATCH = "PATCH"

    name: str = Field(default="basic", description="Name of the WebHookCaller")
    url: HttpUrl = Field(default=..., description="Webhook URL")
    method: WebHookMethod = Field(default=WebHookMethod.POST, description="HTTP method for webhook")

    headers: Optional[Dict[str, str]] = Field(
        default=None, description="Custom headers for the request"
    )
    cookies: Optional[Dict[str, str]] = Field(
        default=None, description="Cookies to send with the request"
    )
    auth: Optional[Tuple[str, str]] = Field(
        default=None, description="(Username, Password) for Basic Auth"
    )
    timeout: float = Field(
        default=5.0, ge=0.5, le=120.0, description="Request timeout in seconds (default 5s)"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "basic",
                "url": "http://localhost:5000/webhook",
                "method": "POST",
                "headers": {"Content-Type": "application/json"},
                "timeout": 5.0,
            }
        }
    )


class CredentialRef(BaseModel):
    """
    Reference to a credential entry resolved by credential providers.
    """

    name: Optional[str] = Field(default=None, description="Credential provider name")
    ref: str = Field(..., description="Provider-specific reference (e.g., secret path or ID)")

    mount: Optional[str] = Field(default=None, description="Optional mount point or backend name")
    version: Optional[int] = Field(
        default=None, description="Optional version for versioned stores"
    )
    field_mapping: Optional[dict[str, str]] = Field(
        default=None,
        description="Mapping from provider fields to connection_args keys",
    )
    namespace: Optional[str] = Field(default=None, description="Optional namespace or tenant scope")

    model_config = ConfigDict(
        extra="allow",
        json_schema_extra={
            "example": {
                "name": "vault_kv",
                "ref": "netpulse/device-a",
                "mount": "kv",
                "field_mapping": {"username": "user", "password": "pass"},
            }
        },
    )


class DriverConnectionArgs(BaseModel):
    """ """

    device_type: Optional[str] = Field(default=None, description="Device type")

    # NOTE: We loose checking here, as DriverConnectionArgs could be
    # auto-filled in Batch APIs. After that, we need to manually check.
    host: Optional[str] = Field(default=None, description="Device IP/hostname")
    username: Optional[str] = Field(default=None, description="Device username")
    password: Optional[str] = Field(default=None, description="Device password")

    model_config = ConfigDict(
        extra="allow",
        json_schema_extra={
            "example": {
                "device_type": "cisco_ios",
                "host": "172.17.0.1",
                "username": "admin",
                "password": "admin",
            }
        },
    )


class BulkDeviceRequest(DriverConnectionArgs):
    """
    Extended device request for bulk operations.
    Allows per-device command/config override.
    """

    command: Optional[Any] = Field(
        default=None,
        description="Device-specific command override (exclusive with config)",
    )
    config: Optional[Any] = Field(
        default=None,
        description="Device-specific config override (exclusive with command)",
    )
    file_transfer: Optional[Any] = Field(
        default=None,
        description="Device-specific file transfer override",
    )

    @model_validator(mode="after")
    def check_command_config_exclusivity(self):
        supplied = sum(x is not None for x in [self.command, self.config, self.file_transfer])
        if supplied > 1:
            raise ValueError(
                f"Device {self.host}: cannot specify more than one of "
                "'command', 'config', or 'file_transfer'"
            )
        return self

    model_config = ConfigDict(
        extra="allow",
        json_schema_extra={
            "example": {
                "device_type": "cisco_ios",
                "host": "192.168.1.1",
                "username": "admin",
                "password": "admin",
                "command": ["show ip int brief"],
            }
        },
    )


class DriverArgs(BaseModel):
    """
    This is a generic model for driver arguments.
    Depends on the driver's method, the arguments can be different.
    """

    model_config = ConfigDict(extra="allow")


class DeviceTestInfo(BaseModel):
    """Base model for device connection test results."""

    driver: DriverName = Field(..., description="Driver name used in the test")
    host: Optional[str] = Field(None, description="Device IP/hostname")

    model_config = ConfigDict(extra="allow")


class BatchFailedItem(BaseModel):
    """Item representing a failed job submission in a batch."""

    host: str
    reason: str


class FileTransferModel(BaseModel):
    """
    Standardized model for file transfer operations.
    Moved to top-level citizen for better API consistency.
    """

    operation: Literal["upload", "download"] = Field(
        ..., description="Transfer operation type: upload or download"
    )
    remote_path: str = Field(..., description="Remote file path")
    local_path: Optional[str] = Field(
        default=None,
        description="Local file path. For download, use staged task folder if not provided.",
    )

    # Optional Sync/Optimization settings
    overwrite: bool = Field(default=True, description="Overwrite destination if exists")
    resume: bool = Field(default=False, description="Whether to resume interrupted transfer")
    recursive: bool = Field(default=False, description="Whether to transfer directory recursively")
    sync_mode: Literal["full", "hash"] = Field(
        default="full",
        description="Sync mode: full (always transfer) or hash (skip if MD5 matches)",
    )
    hash_algorithm: str = Field(default="md5", description="Hash algorithm for verification")
    verify_file: bool = Field(default=True, description="Verify file integrity after transfer")
    chunk_size: int = Field(
        default=32768, description="Transfer chunk size (bytes), default 32KB"
    )

    # Post-transfer actions
    chmod: Optional[str] = Field(
        default=None, description="Set permissions (e.g., '0755') after transfer"
    )
    execute_after_upload: bool = Field(
        default=False, description="Whether to execute execute_command after upload"
    )
    execute_command: Optional[str] = Field(
        default=None, description="Command to execute after transfer"
    )
    cleanup_after_exec: bool = Field(
        default=True, description="Cleanup the file if execution succeeds"
    )

    model_config = ConfigDict(
        extra="allow",
        json_schema_extra={
            "example": {
                "operation": "upload",
                "remote_path": "/tmp/config.cfg",
                "local_path": "staged://abc-123",
                "overwrite": True,
                "execute_after_upload": True,
                "execute_command": "ls -l /tmp/config.cfg",
            }
        },
    )
