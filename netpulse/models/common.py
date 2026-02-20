from enum import Enum
from typing import Any, Dict, Optional, Tuple

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, model_validator


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
    retval: Optional[Any] = None
    error: Optional[Any] = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "type": 1,
                "retval": "Interface GigabitEthernet1/0/1",
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

    @model_validator(mode="after")
    def check_command_config_exclusivity(self):
        if self.command is not None and self.config is not None:
            raise ValueError(
                f"Device {self.host}: cannot specify both 'command' and 'config', choose one"
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
                "command": "show version",
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
