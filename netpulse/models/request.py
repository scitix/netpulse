from typing import List, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .common import (
    BulkDeviceRequest,
    CredentialRef,
    DriverArgs,
    DriverConnectionArgs,
    DriverName,
    FileTransferModel,
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

    model_config = ConfigDict(
        extra="allow",
        json_schema_extra={
            "example": {
                "name": "textfsm",
                "template": "cisco_ios_show_version.textfsm",
                "context": "Cisco IOS Software, v15.2...",
            }
        },
    )


class TemplateRenderRequest(BaseModel):
    """Base request model for template rendering"""

    name: str = Field("jinja2", title="Renderer name", description="Renderer name to use")

    template: Optional[str] = Field(
        default=None,
        title="Template source",
        description="Template source URI (default: plain text)",
    )

    context: Optional[dict] = Field(
        default=None,
        title="Context",
        description="Context data for rendering",
    )

    model_config = ConfigDict(
        extra="allow",
        json_schema_extra={
            "example": {
                "name": "jinja2",
                "template": "hostname {{ hostname }}\ninterface {{ intf }}",
                "context": {"hostname": "router1", "intf": "Gi0/1", "desc": "Configured by Jinja"},
            }
        },
    )


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
    file_transfer: Optional[FileTransferModel] = Field(
        default=None,
        description="Standardized file transfer operation (top-level citizen)",
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

    # Detached Task Control (System-level)
    detach: bool = Field(
        default=False,
        description="Run command in background and return a Task ID immediately",
    )
    push_interval: Optional[int] = Field(
        default=None,
        ge=5,
        le=3600,
        description="Interval (seconds) for incremental webhook log pushes. Requires detach=True",
    )

    # Internal field for file transfer bridge
    staged_file_id: Optional[str] = Field(
        default=None,
        description="Internal reference to the staged file (Multipart mode)",
    )

    @model_validator(mode="after")
    def check_detach_args(self):
        if self.push_interval is not None and not self.detach:
            raise ValueError("`push_interval` requires `detach=True`")
        if self.detach and self.driver != DriverName.PARAMIKO:
            raise ValueError(
                "Detached mode is currently only supported by the "
                f"{DriverName.PARAMIKO.value} driver"
            )
        return self

    @model_validator(mode="after")
    def check_file_transfer_args(self):
        if self.file_transfer and self.driver not in (DriverName.PARAMIKO, DriverName.NETMIKO):
            raise ValueError(
                f"File transfer is currently not supported by the {self.driver.value} driver"
            )
        return self

    @model_validator(mode="after")
    def check_exclusive_fields(self):
        # We allow command and config to be None IF we have a primary action like file_transfer,
        # or if we have driver_args (legacy/other), or if we have a staged_file_id (multipart).
        is_actionable = (
            self.file_transfer is not None
            or self.driver_args is not None
            or self.staged_file_id is not None
        )

        # Basic exclusivity: only one of command, config can be set
        # Note: In future, we might allow command + file_transfer in a sequence
        if self.config is not None and self.command is not None:
            raise ValueError("Only one of `config` or `command` can be set")

        if self.config is None and self.command is None and not is_actionable:
            msg = "Either `config`, `command`, `file_transfer`, or an actionable `driver_args` set."
            raise ValueError(msg)

        return self

    @model_validator(mode="after")
    def check_payload_type(self):
        valid_payload = self.config if self.config is not None else self.command
        # If payload is a dict, rendering MUST be set
        if isinstance(valid_payload, dict) and self.rendering is None:
            raise ValueError("`rendering` should be set when command/config is a dict")
        # For non-dict payloads, rendering is optional
        # (context-only mode or direct command-as-template)
        return self

    @model_validator(mode="after")
    def infer_defaults(self):
        """Auto-select default values based on other fields"""
        if self.queue_strategy is None:
            if self.detach:
                # Detached tasks should pin to a worker to reuse persistent SSH connections
                # for querying/killing.
                self.queue_strategy = QueueStrategy.PINNED
            elif self.driver in [DriverName.NETMIKO]:
                # Netmiko uses pinned strategy by default for persistent connections
                self.queue_strategy = QueueStrategy.PINNED
            else:
                # Other drivers (including Paramiko) use fifo by default
                # User can manually select pinned when persistent connection is desired
                self.queue_strategy = QueueStrategy.FIFO

        if self.queue_strategy == QueueStrategy.PINNED:
            if getattr(self.connection_args, "keepalive", None) is None:
                self.connection_args.keepalive = 60

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
                "config": [
                    "interface GigabitEthernet0/1",
                    "description Managed by NetPulse"
                ],
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

    model_config = ConfigDict(
        extra="allow",
        json_schema_extra={
            "example": {
                "driver": "netmiko",
                "command": ["show version"],
                "devices": [
                    {
                        "host": "172.17.0.1",
                        "device_type": "cisco_ios",
                        "username": "admin",
                        "password": "pass",
                    },
                    {
                        "host": "172.17.0.2",
                        "device_type": "cisco_xe",
                        "username": "admin",
                        "password": "pass",
                        "command": ["show ip interface brief"],
                    },
                ],
            }
        },
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


class DetachedTaskDiscoveryRequest(BaseModel):
    """Request model for detached task discovery on a device"""

    driver: DriverName = Field(..., description="Device driver")
    connection_args: DriverConnectionArgs = Field(..., description="Device connection parameters")
    credential: Optional[CredentialRef] = Field(
        default=None, description="External credential reference to populate connection_args"
    )

    model_config = ConfigDict(
        extra="allow",
        json_schema_extra={
            "example": {
                "driver": "paramiko",
                "connection_args": {
                    "host": "192.168.1.1",
                    "username": "admin",
                    "password": "admin",
                },
            }
        },
    )
