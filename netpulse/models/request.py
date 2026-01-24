from typing import List, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .common import (
    BulkDeviceRequest,
    CredentialRef,
    DriverArgs,
    DriverConnectionArgs,
    DriverName,
    QueueStrategy,
    WebHook,
)


class TemplateParseRequest(BaseModel):
    """Base request model for template parsing"""

    name: str = Field(default="", title="Parser name", description="Parser name to use")

    template: str = Field(
        ...,
        title="Template source",
        description="Template source URI (default: plain text)",
    )

    context: Optional[str] = Field(
        default=None,
        title="Context",
        description="Context content to be parsed",
    )

    model_config = ConfigDict(extra="allow")


class TemplateRenderRequest(BaseModel):
    """Base request model for template rendering"""

    name: str = Field("", title="Renderer name", description="Renderer name to use")

    template: str = Field(
        ...,
        title="Template source",
        description="Template source URI (default: plain text)",
    )

    context: Optional[dict] = Field(
        default=None,
        title="Context",
        description="Context data for rendering",
    )

    model_config = ConfigDict(extra="allow")


class ExecutionRequest(BaseModel):
    # Driver related fields
    driver: DriverName = Field(..., description="Device driver (netmiko, napalm, pyeapi)")
    driver_args: Optional[DriverArgs] = Field(
        default=None, description="Driver-specific parameters"
    )

    # Device connection parameters
    connection_args: DriverConnectionArgs = Field(..., description="Device connection parameters")
    credential: Optional[CredentialRef] = Field(
        default=None, description="External credential reference to populate connection_args"
    )

    # Operation to execute
    config: Union[dict, List[str], str, None] = Field(
        default=None,
        description="configuration to apply (exclusive with command field)",
    )
    command: Union[dict, List[str], str, None] = Field(
        default=None,
        description="Command to execute (exclusive with config field)",
    )

    # Template handling
    rendering: Optional[TemplateRenderRequest] = Field(
        default=None, description="Configuration template rendering settings"
    )
    parsing: Optional[TemplateParseRequest] = Field(
        default=None, description="Output template parsing settings"
    )

    # Queue settings
    queue_strategy: Optional[QueueStrategy] = Field(
        default=None,
        description="Queue strategy (fifo/pinned). Auto-selected by driver if not specified",
    )
    ttl: Optional[int] = Field(default=300, description="Job timeout in seconds", ge=1, le=86400)
    result_ttl: Optional[int] = Field(
        default=None,
        description=(
            "Result retention time in seconds. "
            "If not set, uses system default. "
            "Useful for long-running tasks that need result retention (e.g., 48-hour stress tests)"
        ),
        ge=60,
        le=604800,  # Max 7 days
    )

    # Webhook callback
    webhook: Optional[WebHook] = Field(
        default=None, description="Webhook callback after Job completion"
    )

    @model_validator(mode="after")
    def check_exclusive_fields(self):
        if (self.config is None) == (self.command is None):
            raise ValueError("Either `config` or `command` must be set, but not both")
        return self

    @model_validator(mode="after")
    def check_payload_type(self):
        valid_payload = self.config if self.config is not None else self.command
        if (self.rendering is not None) != isinstance(valid_payload, dict):
            raise ValueError("`rendering` should be set when command/config is a dict")
        return self

    @model_validator(mode="after")
    def infer_defaults(self):
        """Auto-select default values based on other fields"""
        if self.queue_strategy is None:
            if self.driver in [DriverName.NETMIKO]:
                # Netmiko uses pinned strategy by default for persistent connections
                self.queue_strategy = QueueStrategy.PINNED
            else:
                # Other drivers (including Paramiko) use fifo by default
                # User can manually select pinned when persistent connection is desired
                self.queue_strategy = QueueStrategy.FIFO

        return self

    model_config = ConfigDict(
        extra="allow",
        json_schema_extra={
            "example": {
                "driver": "netmiko",
                "connection_args": {
                    "device_type": "cisco_ios",
                    "host": "172.17.0.1",
                    "username": "admin",
                    "password": "admin",
                },
                "config": "interface GigabitEthernet0/1\n description Something",
            }
        },
    )


class BulkExecutionRequest(ExecutionRequest):
    devices: List[BulkDeviceRequest] = Field(
        ...,
        description=(
            "Device list for batch operation. Each device can override connection_args "
            "and optionally override command/config from base request"
        ),
    )

    # Allow more time for bulk operations
    ttl: Optional[int] = Field(default=600, description="Job timeout in seconds", ge=1, le=86400)


class ConnectionTestRequest(BaseModel):
    """Request model for device connection testing"""

    driver: DriverName = Field(..., description="Device driver")
    connection_args: DriverConnectionArgs = Field(..., description="Device connection parameters")
    credential: Optional[CredentialRef] = Field(
        default=None, description="External credential reference to populate connection_args"
    )

    model_config = ConfigDict(
        extra="allow",
        json_schema_extra={
            "example": {
                "driver": "netmiko",
                "connection_args": {
                    "device_type": "cisco_ios",
                    "host": "192.168.1.1",
                    "username": "admin",
                    "password": "admin",
                    "timeout": 30,
                },
            }
        },
    )
