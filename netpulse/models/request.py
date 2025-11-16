from typing import List, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .common import (
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
        None,
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
        None,
        title="Context",
        description="Context data for rendering",
    )

    model_config = ConfigDict(extra="allow")


class PullingRequest(BaseModel):
    driver: DriverName = Field(..., description="Device driver (netmiko, napalm, pyeapi)")
    connection_args: DriverConnectionArgs = Field(..., description="Device connection parameters")
    command: Union[List[str], str] = Field(
        ..., description="Command to execute (single command or list)"
    )
    args: Optional[DriverArgs] = Field(None, description="Driver-specific parameters")
    queue_strategy: Optional[QueueStrategy] = Field(
        None,
        description="Queue strategy (fifo/pinned). Auto-selected by driver if not specified",
    )
    webhook: Optional[WebHook] = Field(None, description="Webhook callback after task completion")
    parsing: Optional[TemplateParseRequest] = Field(
        None, description="Command output parsing configuration"
    )
    ttl: Optional[int] = Field(None, description="Task timeout in seconds", ge=1, le=3600)

    @model_validator(mode="after")
    def check_parsing(self):
        if self.parsing:
            if isinstance(self.command, list) and len(self.command) > 1:
                raise ValueError("`parsing` supports only a single command")
        return self

    @model_validator(mode="after")
    def set_queue_strategy_default(self):
        """Auto-select queue strategy based on driver type"""
        if self.queue_strategy is None:
            # SSH/long connection drivers use pinned strategy
            if self.driver in (DriverName.NETMIKO, DriverName.NAPALM):
                self.queue_strategy = QueueStrategy.PINNED
            # HTTP/stateless drivers use fifo strategy
            else:
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
                "command": "show ip interface brief",
                "queue_strategy": "pinned",
            }
        },
    )


class BatchPullingRequest(PullingRequest):
    devices: List[DriverConnectionArgs] = Field(
        ...,
        description="Device list for batch operation. Overrides fields in connection_args",
    )

    model_config = ConfigDict(
        extra="allow",
        json_schema_extra={
            "example": {
                "driver": "netmiko",
                "devices": [
                    {
                        "host": "172.17.0.1",
                        "username": "specialuser",
                        "password": "password1",
                    },
                    {
                        "host": "172.17.0.2",
                    },
                ],
                "connection_args": {
                    "device_type": "cisco_ios",
                    "username": "admin",
                    "password": "admin",
                    "timeout": 10,
                    "keepalive": 120,
                },
                "command": "show ip interface brief",
                "queue_strategy": "pinned",
            }
        },
    )


class PushingRequest(BaseModel):
    driver: DriverName = Field(..., description="Device driver (netmiko, napalm, pyeapi)")
    connection_args: DriverConnectionArgs = Field(..., description="Device connection parameters")
    config: Union[dict, List[str], str] = Field(
        ...,
        description="Configuration to push (string, list, or dict for template rendering)",
    )
    args: Optional[DriverArgs] = Field(None, description="Driver-specific parameters")
    queue_strategy: Optional[QueueStrategy] = Field(
        None,
        description="Queue strategy (fifo/pinned). Auto-selected by driver if not specified",
    )
    enable_mode: bool = Field(True, description="Enter privileged mode for configuration execution")
    webhook: Optional[WebHook] = Field(None, description="Webhook callback after task completion")
    rendering: Optional[TemplateRenderRequest] = Field(
        None, description="Configuration template rendering settings"
    )
    ttl: Optional[int] = Field(None, description="Task timeout in seconds", ge=1, le=3600)

    @model_validator(mode="after")
    def check_rendering(self):
        if self.rendering:
            if not isinstance(self.config, dict):
                raise ValueError("`rendering` requires config to be a dict")
        return self

    @model_validator(mode="after")
    def set_queue_strategy_default(self):
        """Auto-select queue strategy based on driver type"""
        if self.queue_strategy is None:
            # SSH/long connection drivers use pinned strategy
            if self.driver in [DriverName.NETMIKO, DriverName.NAPALM]:
                self.queue_strategy = QueueStrategy.PINNED
            # HTTP/stateless drivers use fifo strategy
            else:
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
                "queue_strategy": "pinned",
                "config": "interface GigabitEthernet0/1\n description Something",
            }
        },
    )


class BatchPushingRequest(PushingRequest):
    devices: List[DriverConnectionArgs] = Field(
        ...,
        description="Device list for batch operation. Overrides fields in connection_args",
    )

    model_config = ConfigDict(
        extra="allow",
        json_schema_extra={
            "example": {
                "driver": "netmiko",
                "devices": [
                    {
                        "host": "172.17.0.1",
                        "username": "specialuser",
                        "password": "password1",
                    },
                    {
                        "host": "172.17.0.2",
                    },
                ],
                "connection_args": {
                    "device_type": "cisco_ios",
                    "username": "admin",
                    "password": "admin",
                    "timeout": 10,
                    "keepalive": 120,
                },
                "config": "interface GigabitEthernet0/1\n description Something",
                "queue_strategy": "pinned",
            }
        },
    )


class ExecutionRequest(BaseModel):
    # Driver related fields
    driver: DriverName = Field(..., description="Device driver (netmiko, napalm, pyeapi)")
    driver_args: Optional[DriverArgs] = Field(None, description="Driver-specific parameters")

    # Device connection parameters
    connection_args: DriverConnectionArgs = Field(..., description="Device connection parameters")

    # Operation to execute
    config: Union[dict, List[str], str, None] = Field(
        None,
        description="configuration to apply (exclusive with command field)",
    )
    command: Union[dict, List[str], str, None] = Field(
        None,
        description="Command to execute (exclusive with config field)",
    )

    # Template handling
    rendering: Optional[TemplateRenderRequest] = Field(
        None, description="Configuration template rendering settings"
    )
    parsing: Optional[TemplateParseRequest] = Field(
        None, description="Output template parsing settings"
    )

    # Queue settings
    queue_strategy: Optional[QueueStrategy] = Field(
        None,
        description="Queue strategy (fifo/pinned). Auto-selected by driver if not specified",
    )
    ttl: Optional[int] = Field(300, description="Task timeout in seconds", ge=1, le=3600)

    # Webhook callback
    webhook: Optional[WebHook] = Field(None, description="Webhook callback after task completion")

    @model_validator(mode="after")
    def check_exclusive_fields(self):
        if (self.config is None) == (self.command is None):
            raise ValueError("Either `config` or `command` must be set, but not both")
        return self

    @model_validator(mode="after")
    def check_payload_type(self):
        valid_payload = self.config if self.config is not None else self.command
        if (self.rendering is not None) == isinstance(valid_payload, dict):
            raise ValueError("`rendering` should be set when command/config is a dict")
        return self

    @model_validator(mode="after")
    def set_queue_strategy_default(self):
        """Auto-select queue strategy based on driver type"""
        if self.queue_strategy is None:
            if self.driver in [DriverName.NETMIKO, DriverName.NAPALM]:
                # SSH/long connection drivers use pinned strategy
                self.queue_strategy = QueueStrategy.PINNED
            else:
                # HTTP/stateless drivers use fifo strategy
                self.queue_strategy = QueueStrategy.FIFO
        return self

    # TODO: Add more validations as needed

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
    devices: List[DriverConnectionArgs] = Field(
        ...,
        description="Device list for batch operation. Overrides fields in connection_args",
    )


class DeviceRequest(BaseModel):
    """
    Unified device operation request model

    Automatically identifies operation type:
    - Contains command field: query operation (retrieve data)
    - Contains config field: configuration operation (send configuration)

    Supports all drivers: netmiko, napalm, pyeapi
    Auto-selects optimal queue strategy
    """

    # Basic required fields
    driver: DriverName = Field(..., description="Device driver")
    connection_args: DriverConnectionArgs = Field(..., description="Device connection parameters")

    # Operation fields (choose one)
    command: Optional[Union[List[str], str]] = Field(
        None,
        description="Command to execute (query operation). Single command or list",
    )
    config: Optional[Union[dict, List[str], str]] = Field(
        None,
        description="Configuration to push (config operation). String, list or dict",
    )

    # Driver-specific arguments
    driver_args: Optional[dict] = Field(
        None,
        description="Driver-specific parameters, validated by driver and operation type",
    )

    # Optional configuration
    options: Optional[dict] = Field(
        None,
        description="Global options (queue_strategy, ttl, parsing, rendering, webhook)",
    )

    @model_validator(mode="after")
    def validate_operation_type(self):
        """Validate operation type and required fields"""
        has_command = self.command is not None
        has_config = self.config is not None

        if not has_command and not has_config:
            raise ValueError(
                "Either 'command' (query operation) or 'config' (config operation) must be provided"
            )

        if has_command and has_config:
            raise ValueError("Cannot specify both 'command' and 'config' in the same request")

        return self

    @model_validator(mode="after")
    def validate_driver_args(self):
        """Auto-detect and validate driver_args type based on driver and operation type"""
        if not self.driver_args:
            return self

        # If driver_args is already the correct type, validate it
        if not isinstance(self.driver_args, dict):
            expected_type = self._get_expected_args_type()
            if not isinstance(self.driver_args, expected_type):
                raise ValueError(
                    f"For driver '{self.driver}' {self._get_operation_type()} operation, "
                    f"driver_args should be {expected_type.__name__}, "
                    f"but got {type(self.driver_args).__name__}"
                )
            return self

        # If driver_args is dict (for backward compatibility), convert to appropriate type
        try:
            expected_type = self._get_expected_args_type()
            self.driver_args = expected_type.model_validate(self.driver_args)
        except Exception as e:
            valid_fields = (
                list(expected_type.model_fields.keys())
                if hasattr(expected_type, "model_fields")
                else []
            )
            raise ValueError(
                f"Invalid driver_args for driver '{self.driver}' "
                f"{self._get_operation_type()} operation. "
                f"Expected {expected_type.__name__} with fields: {valid_fields}. "
                f"Validation error: {e!s}"
            )

        return self

    @model_validator(mode="after")
    def set_intelligent_defaults(self):
        """Set intelligent default values"""
        if not self.options:
            self.options = {}

        # Auto-select optimal queue strategy
        if "queue_strategy" not in self.options:
            if self.driver == DriverName.NETMIKO:
                # SSH/Telnet long connections benefit from pinned strategy
                self.options["queue_strategy"] = "pinned"
            elif self.driver == DriverName.PARAMIKO:
                # Paramiko uses short connections, benefit from fifo strategy
                self.options["queue_strategy"] = "fifo"
            else:
                # HTTP/HTTPS stateless connections benefit from fifo strategy
                self.options["queue_strategy"] = "fifo"

        # Config operations default to enable mode - set in connection_args
        if self.is_push_operation() and not hasattr(self.connection_args, "enable_mode"):
            # Set enable_mode in connection_args if not already present
            self.connection_args.__dict__.setdefault("enable_mode", True)

        # Set default timeout
        if "ttl" not in self.options:
            self.options["ttl"] = 300  # 5 minutes default timeout

        return self

    def is_pull_operation(self) -> bool:
        """Check if this is a query operation"""
        return self.command is not None

    def is_push_operation(self) -> bool:
        """Check if this is a config operation"""
        return self.config is not None

    def _get_expected_args_type(self):
        """Auto-detect expected driver_args type based on driver and operation type"""
        # Lazy import to avoid circular imports
        if self.driver == DriverName.NETMIKO:
            from ..plugins.drivers.netmiko.model import (
                NetmikoSendCommandArgs,
                NetmikoSendConfigSetArgs,
            )

            if self.is_pull_operation():
                return NetmikoSendCommandArgs
            else:
                return NetmikoSendConfigSetArgs
        elif self.driver == DriverName.NAPALM:
            from ..plugins.drivers.napalm.model import NapalmPullingArgs, NapalmPushingArgs

            if self.is_pull_operation():
                return NapalmPullingArgs
            else:
                return NapalmPushingArgs
        elif self.driver == DriverName.PYEAPI:
            from ..plugins.drivers.pyeapi.model import PyeapiArg

            return PyeapiArg
        elif self.driver == DriverName.PARAMIKO:
            from ..plugins.drivers.paramiko.model import (
                ParamikoSendCommandArgs,
                ParamikoSendConfigArgs,
            )

            if self.is_pull_operation():
                return ParamikoSendCommandArgs
            else:
                return ParamikoSendConfigArgs
        else:
            raise ValueError(f"Unsupported driver: {self.driver}")

    def _get_operation_type(self) -> str:
        """Get operation type description for error messages"""
        return "query" if self.is_pull_operation() else "config"

    def to_pulling_request(self) -> PullingRequest:
        """Convert to PullingRequest for backward compatibility"""
        if not self.is_pull_operation():
            raise ValueError("Cannot convert non-pull request to PullingRequest")

        # Ensure driver_args is properly serialized for RQ
        args = self.driver_args
        if args is not None and hasattr(args, "model_dump"):
            # Convert to dict to ensure proper serialization
            args = args.model_dump(exclude_none=True)

        return PullingRequest(
            driver=self.driver,
            connection_args=self.connection_args,
            command=self.command,
            args=args,
            queue_strategy=self.options.get("queue_strategy"),
            webhook=self.options.get("webhook"),
            parsing=self.options.get("parsing"),
            ttl=self.options.get("ttl"),
        )

    def to_pushing_request(self) -> PushingRequest:
        """Convert to PushingRequest for backward compatibility"""
        if not self.is_push_operation():
            raise ValueError("Cannot convert non-push request to PushingRequest")

        # Get enable_mode from connection_args, default to True for config operations
        enable_mode = getattr(self.connection_args, "enable_mode", True)

        return PushingRequest(
            driver=self.driver,
            connection_args=self.connection_args,
            config=self.config,
            args=self.driver_args,
            enable_mode=enable_mode,
            queue_strategy=self.options.get("queue_strategy"),
            webhook=self.options.get("webhook"),
            rendering=self.options.get("rendering"),
            ttl=self.options.get("ttl"),
        )

    model_config = ConfigDict(extra="forbid")


class BatchDeviceRequest(BaseModel):
    """
    Batch device operation request model

    Execute same operation on multiple devices
    Supports device-level connection parameter override
    """

    # Basic required fields
    driver: DriverName = Field(..., description="Device driver")
    devices: List[DriverConnectionArgs] = Field(
        ...,
        description="Device list for batch operation. Overrides connection_args fields",
        min_length=1,
        max_length=100,
    )
    connection_args: DriverConnectionArgs = Field(
        ..., description="Default connection parameters template"
    )

    # Operation fields (choose one)
    command: Optional[Union[List[str], str]] = Field(
        None, description="Command to execute (query operation)"
    )
    config: Optional[Union[dict, List[str], str]] = Field(
        None, description="Configuration to push (config operation)"
    )

    # Driver-specific arguments
    driver_args: Optional[dict] = Field(
        None,
        description="Driver-specific parameters for all devices, validated by driver type",
    )

    # Optional configuration
    options: Optional[dict] = Field(
        None,
        description="Global options for all devices (queue_strategy, ttl, etc.)",
    )

    @model_validator(mode="after")
    def validate_operation_type(self):
        """Validate operation type and required fields"""
        has_command = self.command is not None
        has_config = self.config is not None

        if not has_command and not has_config:
            raise ValueError(
                "Either 'command' (query operation) or 'config' (config operation) must be provided"
            )

        if has_command and has_config:
            raise ValueError("Cannot specify both 'command' and 'config' in the same request")

        return self

    @model_validator(mode="after")
    def validate_driver_args(self):
        """Auto-detect and validate driver_args type based on driver and operation type"""
        if not self.driver_args:
            return self

        # If driver_args is already the correct type, validate it
        if not isinstance(self.driver_args, dict):
            expected_type = self._get_expected_args_type()
            if not isinstance(self.driver_args, expected_type):
                raise ValueError(
                    f"For driver '{self.driver}' {self._get_operation_type()} operation, "
                    f"driver_args should be {expected_type.__name__}, "
                    f"but got {type(self.driver_args).__name__}"
                )
            return self

        # If driver_args is dict (for backward compatibility), convert to appropriate type
        try:
            expected_type = self._get_expected_args_type()
            self.driver_args = expected_type.model_validate(self.driver_args)
        except Exception as e:
            valid_fields = (
                list(expected_type.model_fields.keys())
                if hasattr(expected_type, "model_fields")
                else []
            )
            raise ValueError(
                f"Invalid driver_args for driver '{self.driver}' "
                f"{self._get_operation_type()} operation. "
                f"Expected {expected_type.__name__} with fields: {valid_fields}. "
                f"Validation error: {e!s}"
            )

        return self

    @model_validator(mode="after")
    def set_intelligent_defaults(self):
        """Set intelligent default values"""
        if not self.options:
            self.options = {}

        # Auto-select optimal queue strategy
        if "queue_strategy" not in self.options:
            if self.driver == "netmiko":
                self.options["queue_strategy"] = "pinned"
            elif self.driver == "paramiko":
                self.options["queue_strategy"] = "fifo"
            else:
                self.options["queue_strategy"] = "fifo"

        # Config operations default to enable mode - set in connection_args
        if self.is_push_operation() and not hasattr(self.connection_args, "enable_mode"):
            # Set enable_mode in connection_args if not already present
            self.connection_args.__dict__.setdefault("enable_mode", True)

        # Batch operations use longer default timeout
        if "ttl" not in self.options:
            self.options["ttl"] = 600  # 10 minutes default timeout

        return self

    def is_pull_operation(self) -> bool:
        """Check if this is a query operation"""
        return self.command is not None

    def is_push_operation(self) -> bool:
        """Check if this is a config operation"""
        return self.config is not None

    def _get_expected_args_type(self):
        """Auto-detect expected driver_args type based on driver and operation type"""
        # Lazy import to avoid circular imports
        if self.driver == DriverName.NETMIKO:
            from ..plugins.drivers.netmiko.model import (
                NetmikoSendCommandArgs,
                NetmikoSendConfigSetArgs,
            )

            if self.is_pull_operation():
                return NetmikoSendCommandArgs
            else:
                return NetmikoSendConfigSetArgs
        elif self.driver == DriverName.NAPALM:
            from ..plugins.drivers.napalm.model import NapalmPullingArgs, NapalmPushingArgs

            if self.is_pull_operation():
                return NapalmPullingArgs
            else:
                return NapalmPushingArgs
        elif self.driver == DriverName.PYEAPI:
            from ..plugins.drivers.pyeapi.model import PyeapiArg

            return PyeapiArg
        elif self.driver == DriverName.PARAMIKO:
            from ..plugins.drivers.paramiko.model import (
                ParamikoSendCommandArgs,
                ParamikoSendConfigArgs,
            )

            if self.is_pull_operation():
                return ParamikoSendCommandArgs
            else:
                return ParamikoSendConfigArgs
        else:
            raise ValueError(f"Unsupported driver: {self.driver}")

    def _get_operation_type(self) -> str:
        """Get operation type description for error messages"""
        return "query" if self.is_pull_operation() else "config"

    def to_batch_pulling_request(self) -> BatchPullingRequest:
        """Convert to BatchPullingRequest for backward compatibility"""
        if not self.is_pull_operation():
            raise ValueError("Cannot convert non-pull request to BatchPullingRequest")

        return BatchPullingRequest(
            driver=self.driver,
            devices=self.devices,
            connection_args=self.connection_args,
            command=self.command,
            args=self.driver_args,
            queue_strategy=self.options.get("queue_strategy"),
            webhook=self.options.get("webhook"),
            parsing=self.options.get("parsing"),
            ttl=self.options.get("ttl"),
        )

    def to_batch_pushing_request(self) -> BatchPushingRequest:
        """Convert to BatchPushingRequest for backward compatibility"""
        if not self.is_push_operation():
            raise ValueError("Cannot convert non-push request to BatchPushingRequest")

        # Get enable_mode from connection_args, default to True for config operations
        enable_mode = getattr(self.connection_args, "enable_mode", True)

        return BatchPushingRequest(
            driver=self.driver,
            devices=self.devices,
            connection_args=self.connection_args,
            config=self.config,
            args=self.driver_args,
            enable_mode=enable_mode,
            queue_strategy=self.options.get("queue_strategy"),
            webhook=self.options.get("webhook"),
            rendering=self.options.get("rendering"),
            ttl=self.options.get("ttl"),
        )

    model_config = ConfigDict(extra="forbid")


class ConnectionTestRequest(BaseModel):
    """Request model for device connection testing"""

    driver: DriverName = Field(..., description="Device driver")
    connection_args: DriverConnectionArgs = Field(..., description="Device connection parameters")

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
