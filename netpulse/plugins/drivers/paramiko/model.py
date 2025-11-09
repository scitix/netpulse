from typing import Dict, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

from ....models import DriverArgs, DriverConnectionArgs
from ....models.common import DriverName
from ....models.request import PullingRequest, PushingRequest


class ParamikoConnectionArgs(DriverConnectionArgs):
    """Paramiko connection arguments, reference paramiko.SSHClient.connect()"""

    # Required fields
    host: str = Field(..., description="Server address (IP or domain name)")
    username: str = Field(..., description="SSH username")

    # Authentication (choose one)
    password: Optional[str] = Field(None, description="Password authentication")
    key_filename: Optional[str] = Field(None, description="Private key file path")
    pkey: Optional[str] = Field(
        None, description="Private key content (PEM format string)"
    )
    passphrase: Optional[str] = Field(
        None, description="Private key passphrase (if key is encrypted)"
    )

    # Connection options
    port: int = Field(22, description="SSH port, default 22")
    timeout: float = Field(30.0, description="Connection timeout (seconds)")

    # Host key verification
    host_key_policy: Literal["auto_add", "reject", "warning"] = Field(
        "auto_add",
        description=(
            "Host key verification policy: auto_add (auto accept), "
            "reject (reject), warning (warn but accept)"
        ),
    )

    # Advanced options
    look_for_keys: bool = Field(True, description="Whether to auto-discover keys in ~/.ssh/")
    allow_agent: bool = Field(
        False,
        description="Whether to allow SSH agent (default False, consistent with Netmiko driver)",
    )
    compress: bool = Field(False, description="Whether to enable compression")
    banner_timeout: Optional[float] = Field(None, description="Banner timeout")
    auth_timeout: Optional[float] = Field(None, description="Authentication timeout")

    # SSH Proxy/Jump Host support
    proxy_host: Optional[str] = Field(
        None, description="Proxy/Jump host address (for SSH tunneling)"
    )
    proxy_port: int = Field(22, description="Proxy/Jump host SSH port")
    proxy_username: Optional[str] = Field(None, description="Proxy/Jump host username")
    proxy_password: Optional[str] = Field(None, description="Proxy/Jump host password")
    proxy_key_filename: Optional[str] = Field(
        None, description="Proxy/Jump host private key file path"
    )
    proxy_pkey: Optional[str] = Field(
        None, description="Proxy/Jump host private key content (PEM format)"
    )
    proxy_passphrase: Optional[str] = Field(
        None, description="Proxy/Jump host private key passphrase"
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
        ..., description="Transfer operation type: upload or download"
    )
    local_path: str = Field(..., description="Local file path")
    remote_path: str = Field(..., description="Remote file path")
    resume: bool = Field(False, description="Whether to resume interrupted transfer")
    chunk_size: int = Field(32768, description="Transfer chunk size in bytes (default 32KB)")
    timeout: Optional[float] = Field(
        None, description="Transfer timeout (seconds), None means no timeout"
    )


class ParamikoSendCommandArgs(DriverArgs):
    """Command execution arguments, reference paramiko.SSHClient.exec_command()"""

    timeout: Optional[float] = Field(
        None, description="Command execution timeout (seconds), None means no timeout"
    )
    get_pty: bool = Field(
        False, description="Whether to use pseudo-terminal (PTY), for interactive commands"
    )
    environment: Optional[Dict[str, str]] = Field(
        None, description="Environment variables dictionary"
    )
    bufsize: int = Field(-1, description="Buffer size, -1 means use system default")
    file_transfer: Optional[ParamikoFileTransferOperation] = Field(
        None,
        description=(
            "File transfer operation. If set, file transfer will be performed "
            "instead of command execution"
        ),
    )


class ParamikoSendConfigArgs(DriverArgs):
    """Configuration deployment arguments"""

    timeout: Optional[float] = Field(None, description="Configuration execution timeout (seconds)")
    get_pty: bool = Field(False, description="Whether to use pseudo-terminal")
    sudo: bool = Field(False, description="Whether to use sudo execution")
    sudo_password: Optional[str] = Field(None, description="Sudo password (if sudo is enabled)")
    environment: Optional[Dict[str, str]] = Field(None, description="Environment variables")

    @model_validator(mode="after")
    def validate_sudo(self):
        """If sudo is enabled and password is required, ensure sudo_password is provided"""
        if self.sudo and self.sudo_password is None:
            # Note: Some systems may not require password for sudo, so we just warn
            # The actual requirement depends on sudoers configuration
            pass
        return self


class ParamikoPullingRequest(PullingRequest):
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


class ParamikoPushingRequest(PushingRequest):
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



