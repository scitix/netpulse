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
    local_path: str = Field(default=..., description="Local file path")
    remote_path: str = Field(default=..., description="Remote file path")
    resume: bool = Field(default=False, description="Whether to resume interrupted transfer")
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
            "Whether to cleanup remote file after execution "
            "(only if execute_after_upload is True)"
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
        default=None, description="Working directory for script execution"
    )
    # Background task execution
    run_in_background: bool = Field(
        default=False, description="Whether to run command in background (using nohup)"
    )
    background_output_file: Optional[str] = Field(
        default=None,
        description="Output file for background task (default: /tmp/netpulse_<pid>.log)",
    )
    background_pid_file: Optional[str] = Field(
        default=None,
        description="PID file path for background task (default: /tmp/netpulse_<pid>.pid)",
    )
    # Background task query
    check_task: Optional["BackgroundTaskQuery"] = Field(
        default=None,
        description="Query status of a previously started background task",
    )
    # Streaming execution
    stream: bool = Field(
        default=False,
        description="Enable streaming mode: command runs in background with session tracking",
    )
    stream_query: Optional["StreamQuery"] = Field(
        default=None,
        description="Query streaming command output by session_id",
    )


class BackgroundTaskQuery(BaseModel):
    """Query parameters for checking background task status"""

    pid: int = Field(..., description="Process ID of the background task to check")
    output_file: Optional[str] = Field(
        default=None,
        description="Path to the task's output file (for reading logs)",
    )
    tail_lines: int = Field(
        default=100,
        ge=1,
        le=10000,
        description="Number of lines to return from output file tail",
    )
    kill_if_running: bool = Field(
        default=False,
        description="If True, terminate the task if it's still running",
    )
    cleanup_files: bool = Field(
        default=False,
        description="If True, remove pid/output files after query (only if task completed)",
    )


class StreamQuery(BaseModel):
    """Query parameters for streaming command output"""

    session_id: str = Field(..., description="Stream session ID returned from stream command")
    offset: int = Field(
        default=0,
        ge=0,
        description="Byte offset to read from (for incremental output)",
    )
    lines: int = Field(
        default=100,
        ge=1,
        le=10000,
        description="Number of lines to return from tail",
    )
    wait_complete: bool = Field(
        default=False,
        description="If True, wait for command to complete before returning",
    )
    kill: bool = Field(
        default=False,
        description="If True, terminate the command",
    )
    cleanup: bool = Field(
        default=False,
        description="If True, cleanup session files after command completes",
    )


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

    @model_validator(mode="after")
    def validate_sudo(self):
        """If sudo is enabled and password is required, ensure sudo_password is provided"""
        if self.sudo and self.sudo_password is None:
            # Note: Some systems may not require password for sudo, so we just warn
            # The actual requirement depends on sudoers configuration
            pass
        return self


# DEPRECATED: Use ParamikoExecutionRequest instead
class ParamikoPullingRequest(ExecutionRequest):
    driver: DriverName = DriverName.PARAMIKO
    connection_args: ParamikoConnectionArgs
    args: Optional[ParamikoSendCommandArgs] = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "driver": "paramiko",
                "queue_strategy": "fifo",
                "connection_args": {
                    "host": "192.168.1.100",
                    "username": "admin",
                    "password": "password123",
                    "port": 22,
                    "timeout": 30.0,
                    "host_key_policy": "auto_add",
                },
                "command": ["uname -a", "df -h", "free -m"],
                "args": {
                    "timeout": 30.0,
                    "get_pty": False,
                    # File transfer example (optional):
                    # "file_transfer": {
                    #     "operation": "upload",
                    #     "local_path": "/local/file.txt",
                    #     "remote_path": "/remote/file.txt",
                    #     "resume": False,
                    #     "chunk_size": 32768,
                    # }
                },
            }
        }
    )


# DEPRECATED: Use ParamikoExecutionRequest instead
class ParamikoPushingRequest(ExecutionRequest):
    driver: DriverName = DriverName.PARAMIKO
    connection_args: ParamikoConnectionArgs
    args: Optional[ParamikoSendConfigArgs] = None

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
                "args": {
                    "sudo": True,
                    "sudo_password": "sudo_pass",
                    "timeout": 30.0,
                },
            }
        }
    )


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
                "args": {
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
