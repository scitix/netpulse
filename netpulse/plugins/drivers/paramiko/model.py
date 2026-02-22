from typing import Dict, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

from ....models import DeviceTestInfo, DriverArgs, DriverConnectionArgs, DriverName
from ....models.request import ExecutionRequest


class ParamikoConnectionArgs(DriverConnectionArgs):
    """
    Paramiko connection arguments.

    Refer to `paramiko.SSHClient.connect()`
    """

    # Required fields
    host: str = Field(default=..., description="Server address (IP or domain name)")
    username: str = Field(default=..., description="SSH username")

    # Authentication (choose one)
    password: Optional[str] = Field(default=None, description="Password authentication")
    key_filename: Optional[str] = Field(default=None, description="Private key file path")
    pkey: Optional[str] = Field(default=None, description="Private key content (PEM format string)")
    passphrase: Optional[str] = Field(
        default=None, description="Private key passphrase (if key is encrypted)"
    )

    # Connection options
    port: int = Field(default=22, description="SSH port, default 22")
    timeout: float = Field(default=30.0, description="Connection timeout (seconds)")

    # Host key verification
    host_key_policy: Literal["auto_add", "reject", "warning"] = Field(
        default="auto_add",
        description=(
            "Host key verification policy: auto_add (auto accept), "
            "reject (reject), warning (warn but accept)"
        ),
    )

    # Advanced options
    look_for_keys: bool = Field(
        default=True, description="Whether to auto-discover keys in ~/.ssh/"
    )
    allow_agent: bool = Field(
        default=False,
        description="Whether to allow SSH agent (default False, consistent with Netmiko driver)",
    )
    compress: bool = Field(default=False, description="Whether to enable compression")
    banner_timeout: Optional[float] = Field(default=None, description="Banner timeout")
    auth_timeout: Optional[float] = Field(default=None, description="Authentication timeout")
    keepalive: Optional[int] = Field(
        default=None,
        description=(
            "Keepalive interval in seconds. When set, enables persistent connection mode. "
            "The connection will be kept alive and reused across multiple commands."
        ),
    )

    # SSH Proxy/Jump Host support
    proxy_host: Optional[str] = Field(
        default=None, description="Proxy/Jump host address (for SSH tunneling)"
    )
    proxy_port: int = Field(default=22, description="Proxy/Jump host SSH port")
    proxy_username: Optional[str] = Field(default=None, description="Proxy/Jump host username")
    proxy_password: Optional[str] = Field(default=None, description="Proxy/Jump host password")
    proxy_key_filename: Optional[str] = Field(
        default=None, description="Proxy/Jump host private key file path"
    )
    proxy_pkey: Optional[str] = Field(
        default=None, description="Proxy/Jump host private key content (PEM format)"
    )
    proxy_passphrase: Optional[str] = Field(
        default=None, description="Proxy/Jump host private key passphrase"
    )

    @model_validator(mode="after")
    def validate_authentication(self):
        """Ensure at least one authentication method is provided"""
        has_password = self.password is not None
        has_key_file = self.key_filename is not None
        has_pkey = self.pkey is not None
        has_agent = self.allow_agent is True
        has_auto_keys = self.look_for_keys is True

        if not (has_password or has_key_file or has_pkey or has_agent or has_auto_keys):
            raise ValueError(
                "At least one authentication method must be provided: "
                "password, key_filename, pkey, allow_agent, or look_for_keys"
            )

        return self

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "host": "192.168.1.100",
                "username": "admin",
                "password": "password123",
                "port": 22,
                "timeout": 30.0,
                "host_key_policy": "auto_add",
            }
        }
    )


class ParamikoFileTransferOperation(BaseModel):
    """File transfer operation parameters"""

    operation: Literal["upload", "download"] = Field(
        default=..., description="Transfer operation type: upload or download"
    )
    local_path: Optional[str] = Field(default=None, description="Local file path")
    remote_path: str = Field(default=..., description="Remote file path")
    resume: bool = Field(default=False, description="Whether to resume interrupted transfer")
    recursive: bool = Field(default=False, description="Whether to transfer directory recursively")
    sync_mode: Literal["full", "hash"] = Field(
        default="full",
        description="Sync mode: full (always transfer) or hash (skip if MD5 matches)",
    )
    chunk_size: int = Field(
        default=32768, description="Transfer chunk size in bytes (default 32KB)"
    )
    timeout: Optional[float] = Field(
        default=None, description="Transfer timeout (seconds), None means no timeout"
    )
    # Execute after upload/download
    execute_after_upload: bool = Field(
        default=False,
        description="Whether to execute command after upload (only for upload operation)",
    )
    execute_command: Optional[str] = Field(
        default=None,
        description="Command to execute after file transfer (e.g., 'bash /tmp/script.sh')",
    )
    cleanup_after_exec: bool = Field(
        default=True,
        description=(
            "Whether to cleanup remote file after execution (only if execute_after_upload is True)"
        ),
    )
    chmod: Optional[str] = Field(
        default=None,
        description=(
            "Optional permissions (octal string like '0755') to set on remote file after transfer"
        ),
    )


class ParamikoSendCommandArgs(DriverArgs):
    """Command execution arguments, reference paramiko.SSHClient.exec_command()"""

    timeout: Optional[float] = Field(
        default=None, description="Command execution timeout (seconds), None means no timeout"
    )
    get_pty: bool = Field(
        default=False, description="Whether to use pseudo-terminal (PTY), for interactive commands"
    )
    environment: Optional[Dict[str, str]] = Field(
        default=None, description="Environment variables dictionary"
    )
    bufsize: int = Field(default=-1, description="Buffer size, -1 means use system default")
    file_transfer: Optional[ParamikoFileTransferOperation] = Field(
        default=None,
        description=(
            "File transfer operation. If set, file transfer will be performed "
            "instead of command execution"
        ),
    )
    # Script content execution
    script_content: Optional[str] = Field(
        default=None,
        description="Script content to execute directly via stdin (alternative to command field)",
    )
    script_interpreter: str = Field(
        default="bash", description="Script interpreter (bash, sh, python, etc.)"
    )
    working_directory: Optional[str] = Field(
        default=None, description="Working directory for the command or script"
    )
    # Interactive support
    expect_map: Optional[Dict[str, str]] = Field(
        default=None,
        description="Map of expected prompts to automated responses (e.g. {'[Y/n]': 'y'})",
    )
    # Sudo support
    sudo: bool = Field(default=False, description="Whether to use sudo execution")
    sudo_password: Optional[str] = Field(
        default=None, description="Sudo password (if sudo is enabled)"
    )
    # Metadata Control
    read_detached_task_logs: Optional[dict] = Field(
        default=None, description="Internal use only: instructions for reading detached task logs"
    )
    list_active_detached_tasks: bool = Field(
        default=False, description="List all active background/detached tasks on the target machine"
    )

    @model_validator(mode="after")
    def validate_sudo(self):
        """If sudo is enabled and password is required, ensure sudo_password is provided"""
        if self.sudo and self.sudo_password is None:
            # Note: Some systems may not require password for sudo
            pass
        return self


class ParamikoSendConfigArgs(DriverArgs):
    """Configuration deployment arguments"""

    timeout: Optional[float] = Field(
        default=None, description="Configuration execution timeout (seconds)"
    )
    get_pty: bool = Field(default=False, description="Whether to use pseudo-terminal")
    sudo: bool = Field(default=False, description="Whether to use sudo execution")
    sudo_password: Optional[str] = Field(
        default=None, description="Sudo password (if sudo is enabled)"
    )
    environment: Optional[Dict[str, str]] = Field(default=None, description="Environment variables")
    stop_on_error: bool = Field(
        default=True, description="Stop execution of subsequent lines if a command fails"
    )

    @model_validator(mode="after")
    def validate_sudo(self):
        """If sudo is enabled and password is required, ensure sudo_password is provided"""
        if self.sudo and self.sudo_password is None:
            # Note: Some systems may not require password for sudo, so we just warn
            # The actual requirement depends on sudoers configuration
            pass
        return self


# Removed deprecated Pulling/Pushing models. Use ParamikoExecutionRequest.


class ParamikoExecutionRequest(ExecutionRequest):
    driver: DriverName = DriverName.PARAMIKO
    connection_args: ParamikoConnectionArgs
    driver_args: Optional[ParamikoSendCommandArgs | ParamikoSendConfigArgs] = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "driver": "paramiko",
                "queue_strategy": "fifo",
                "connection_args": {
                    "host": "192.168.1.100",
                    "username": "admin",
                    "key_filename": "/path/to/private_key",
                    "passphrase": "key_password",
                },
                "config": [
                    "echo 'Hello World' > /tmp/test.txt",
                    "chmod 644 /tmp/test.txt",
                ],
                "driver_args": {
                    "sudo": True,
                    "sudo_password": "sudo_pass",
                    "timeout": 30.0,
                },
            }
        }
    )


class ParamikoDeviceTestInfo(DeviceTestInfo):
    driver: DriverName = DriverName.PARAMIKO
    remote_version: Optional[str] = None
