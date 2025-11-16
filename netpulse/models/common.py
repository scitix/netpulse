from enum import Enum
from typing import Any, Dict, Optional, Tuple, Union

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator, model_validator


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


class CredentialReference(BaseModel):
    """Credential reference model.

    Supports multiple formats:
    1. Full format: {"provider": "vault", "path": "sites/hq/readonly", ...}
    2. Short format: {"path": "sites/hq/readonly"}  # provider defaults to "vault"
    3. String format: "sites/hq/readonly"  # handled by DriverConnectionArgs validator
    """

    provider: str = Field("vault", description="Credential provider name, defaults to 'vault'")
    path: str = Field(..., description="Credential path in Vault, supports hierarchical structure")
    username_key: Optional[str] = Field("username", description="Username field name")
    password_key: Optional[str] = Field("password", description="Password field name")


class WebHook(BaseModel):
    class WebHookMethod(str, Enum):
        GET = "GET"
        POST = "POST"
        PUT = "PUT"
        DELETE = "DELETE"
        PATCH = "PATCH"

    name: str = Field("basic", description="Name of the WebHookCaller")
    url: HttpUrl = Field(..., description="Webhook URL")
    method: WebHookMethod = Field(WebHookMethod.POST, description="HTTP method for webhook")

    headers: Optional[Dict[str, str]] = Field(None, description="Custom headers for the request")
    cookies: Optional[Dict[str, str]] = Field(None, description="Cookies to send with the request")
    auth: Optional[Tuple[str, str]] = Field(None, description="(Username, Password) for Basic Auth")
    timeout: float = Field(
        5.0, ge=0.5, le=120.0, description="Request timeout in seconds (default 5s)"
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


class DriverConnectionArgs(BaseModel):
    """
    NOTE: We loose the field checking to Optional.
    Strict checks should be done in derived classes.
    """

    device_type: Optional[str] = Field(None, description="Device type")
    host: Optional[str] = Field(None, description="Device IP address")
    username: Optional[str] = Field(None, description="Device username")
    password: Optional[str] = Field(None, description="Device password")
    credential_ref: Optional[Union[CredentialReference, str, Dict[str, Any]]] = Field(
        None,
        description=(
            "Credential reference from credential provider. "
            "Supports: string path, dict with path, or full CredentialReference object"
        ),
    )

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

    @field_validator("credential_ref", mode="before")
    @classmethod
    def normalize_credential_ref(cls, v):
        """Normalize credential_ref to CredentialReference object.

        Supports string path, dict with path, or CredentialReference object.
        """
        if v is None:
            return None

        if isinstance(v, str):
            # String format: just the path
            return CredentialReference(path=v)

        if isinstance(v, dict):
            # Dict format: ensure it has path
            if "path" not in v:
                raise ValueError("credential_ref dict must contain 'path' field")
            return CredentialReference(**v)

        # Already a CredentialReference object
        return v

    @model_validator(mode="after")
    def validate_credentials(self):
        """
        Validate credential configuration: must provide direct credentials or credential reference,
        but not both.

        Note: Some drivers may only need username (e.g., key authentication), not password,
        so only check if username exists, don't require password.
        """
        has_direct_creds = self.username is not None
        has_credential_ref = self.credential_ref is not None

        if not has_direct_creds and not has_credential_ref:
            raise ValueError("Must provide username or credential reference")

        if has_direct_creds and has_credential_ref:
            raise ValueError("Cannot provide both direct credentials and credential reference")

        return self

    def enforced_field_check(self):
        """
        DriverConnectionArgs could be auto-filled in Batch APIs.
        After that, we need to manually check.
        """
        if self.host is None:
            raise ValueError("host is None")

        return self


class DriverArgs(BaseModel):
    """
    This is a generic model for driver arguments.
    Depends on the driver's method, the arguments can be different.
    """

    model_config = ConfigDict(extra="allow")
