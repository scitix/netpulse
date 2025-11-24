from typing import Any, Dict, Optional

from pydantic import ConfigDict, Field

from ....models import DeviceTestInfo, DriverArgs, DriverConnectionArgs, DriverName
from ....models.request import ExecutionRequest


class NetmikoConnectionArgs(DriverConnectionArgs):
    """
    Connection arguments for Netmiko.
    Refer to `netmiko.ConnectHandler()` for details.
    """

    # Required fields
    device_type: str = Field(default=...)
    host: str = Field(default=...)
    username: str = Field(default=...)
    password: str = Field(default=...)

    # Optional fields
    ip: Optional[str] = None
    secret: Optional[str] = None
    port: Optional[int] = 22
    verbose: Optional[bool] = None
    global_delay_factor: Optional[int] = 1
    global_cmd_verify: Optional[bool] = None
    use_keys: Optional[bool] = None
    key_file: Optional[str] = None
    pkey: Optional[str] = None
    passphrase: Optional[str] = None
    disabled_algorithms: Optional[Dict[str, Any]] = None
    disable_sha2_fix: bool = False
    allow_agent: Optional[bool] = False
    ssh_strict: Optional[bool] = None
    system_host_keys: Optional[bool] = False
    alt_host_keys: Optional[bool] = False
    alt_key_file: Optional[str] = ""
    ssh_config_file: Optional[str] = None
    timeout: Optional[int] = 100
    session_timeout: Optional[int] = None
    auth_timeout: Optional[float] = None
    blocking_timeout: Optional[int] = 20
    banner_timeout: Optional[int] = 15
    keepalive: Optional[int] = 180  # keepalive (3m) differs from netmiko default (0)
    default_enter: Optional[str] = None
    response_return: Optional[str] = None
    serial_settings: Optional[str] = None
    fast_cli: Optional[bool] = False
    session_log: Optional[str] = None
    session_log_record_writes: Optional[bool] = False
    session_log_file_mode: Optional[str] = "write"
    allow_auto_change: Optional[bool] = False
    encoding: Optional[str] = "ascii"

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "device_type": "cisco_ios",
                "host": "172.17.0.2",
                "username": "device_username",
                "password": "device_password",
            }
        }
    )


class NetmikoSendCommandArgs(DriverArgs):
    """
    Arguments for Netmiko send_command method.
    """

    expect_string: Optional[str] = None
    read_timeout: float = 10.0
    delay_factor: Optional[float] = None
    max_loops: Optional[int] = None
    auto_find_prompt: bool = True
    strip_prompt: bool = True
    strip_command: bool = True
    normalize: bool = True
    use_textfsm: bool = False
    textfsm_template: Optional[str] = None
    use_ttp: bool = False
    ttp_template: Optional[str] = None
    use_genie: bool = False
    cmd_verify: bool = True
    raise_parsing_error: bool = False


class NetmikoSendConfigSetArgs(DriverArgs):
    """
    Arguments for Netmiko send_config_set method.
    """

    exit_config_mode: bool = True
    read_timeout: Optional[float] = None
    delay_factor: Optional[float] = None
    max_loops: Optional[int] = None
    strip_prompt: bool = False
    strip_command: bool = False
    config_mode_command: Optional[str] = None
    cmd_verify: bool = True
    enter_config_mode: bool = True
    error_pattern: str = ""
    terminator: str = r"#"
    bypass_commands: Optional[str] = None


class NetmikoExecutionRequest(ExecutionRequest):
    driver: DriverName = DriverName.NETMIKO
    connection_args: NetmikoConnectionArgs
    driver_args: Optional[NetmikoSendConfigSetArgs | NetmikoSendCommandArgs] = None

    save: bool = Field(default=False, description="Save configuration after execution")
    enable_mode: bool = Field(default=False, description="Enter privileged mode for execution")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "driver": "netmiko",
                "queue_strategy": "pinned",
                "connection_args": {
                    "device_type": "cisco_ios",
                    "host": "172.17.0.1",
                    "port": "10005",
                    "username": "admin",
                    "password": "admin",
                },
                "config": ["hostname cat"],
                "save": True,
                "enable_mode": True,
            }
        }
    )


class NetmikoDeviceTestInfo(DeviceTestInfo):
    driver: DriverName = DriverName.NETMIKO
    device_type: str
    prompt: str
