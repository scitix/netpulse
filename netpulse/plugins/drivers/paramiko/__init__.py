import logging
from io import StringIO
from typing import Optional

import paramiko

from .. import BaseDriver
from .model import (
    ParamikoConnectionArgs,
    ParamikoDeviceTestInfo,
    ParamikoExecutionRequest,
    ParamikoPullingRequest,
    ParamikoPushingRequest,
    ParamikoSendCommandArgs,
    ParamikoSendConfigArgs,
)

log = logging.getLogger(__name__)


class ParamikoDriver(BaseDriver):
    driver_name = "paramiko"

    @classmethod
    def from_pulling_request(cls, req: ParamikoPullingRequest) -> "ParamikoDriver":
        if not isinstance(req, ParamikoPullingRequest):
            # Preserve args if it's already ParamikoSendCommandArgs
            if hasattr(req, "args") and isinstance(req.args, ParamikoSendCommandArgs):
                # model_dump() may lose args fields, so we manually preserve it
                req_dict = req.model_dump(exclude_none=True)
                req_dict["args"] = req.args.model_dump(exclude_none=True)
                paramiko_req = ParamikoPullingRequest.model_validate(req_dict)
                # Ensure args is preserved (in case model_validate doesn't handle it correctly)
                paramiko_req.args = req.args
                req = paramiko_req
            else:
                # Handle case where args might be DriverArgs base class or dict
                req_dict = req.model_dump(exclude_none=True)
                # If args exists but is empty dict, try to get from original req.args
                if hasattr(req, "args") and req.args:
                    if isinstance(req.args, dict):
                        req_dict["args"] = req.args
                    elif isinstance(req.args, ParamikoSendCommandArgs):
                        req_dict["args"] = req.args.model_dump(exclude_none=True)
                    else:
                        # Try to convert DriverArgs to dict
                        try:
                            req_dict["args"] = req.args.model_dump(exclude_none=True)
                        except Exception:
                            req_dict["args"] = {}
                req = ParamikoPullingRequest.model_validate(req_dict)
        return cls(args=req.args, conn_args=req.connection_args)

    @classmethod
    def from_pushing_request(cls, req: ParamikoPushingRequest) -> "ParamikoDriver":
        if not isinstance(req, ParamikoPushingRequest):
            req = ParamikoPushingRequest.model_validate(req.model_dump())
        return cls(args=req.args, conn_args=req.connection_args)

    @classmethod
    def from_execution_request(cls, req: ParamikoExecutionRequest) -> "ParamikoDriver":
        if not isinstance(req, ParamikoExecutionRequest):
            req = ParamikoExecutionRequest.model_validate(req.model_dump())
        return cls(args=req.driver_args, conn_args=req.connection_args)

    @classmethod
    def validate(cls, req) -> None:
        """
        Validate the request without creating the driver instance.

        Raises:
            pydantic.ValidationError: If the request model validation fails
                (e.g., missing required fields, invalid field types).
            ValueError: If authentication validation fails in the model_validator
                (e.g., neither password nor key authentication provided).
        """
        # Validate the request model using Pydantic
        # This will automatically trigger the @model_validator for authentication
        if not isinstance(req, ParamikoExecutionRequest):
            ParamikoExecutionRequest.model_validate(req.model_dump())

    def __init__(
        self,
        args: Optional[ParamikoSendCommandArgs | ParamikoSendConfigArgs],
        conn_args: ParamikoConnectionArgs,
        **kwargs,
    ):
        self.args = args
        self.conn_args = conn_args

    def connect(self) -> paramiko.SSHClient:
        try:
            if self.conn_args.proxy_host:
                return self._connect_via_proxy()
            return self._connect_direct()
        except Exception as e:
            log.error(f"Error in connecting: {e}")
            raise e

    def _get_auth_kwargs(self, use_proxy: bool = False) -> dict:
        kwargs = {}
        if use_proxy:
            if self.conn_args.proxy_pkey:
                kwargs["pkey"] = self._load_pkey(
                    self.conn_args.proxy_pkey, self.conn_args.proxy_passphrase
                )
                kwargs["username"] = self.conn_args.proxy_username or self.conn_args.username
            elif self.conn_args.proxy_key_filename:
                kwargs["key_filename"] = self.conn_args.proxy_key_filename
                kwargs["username"] = self.conn_args.proxy_username or self.conn_args.username
                if self.conn_args.proxy_passphrase:
                    kwargs["passphrase"] = self.conn_args.proxy_passphrase
            else:
                kwargs["username"] = self.conn_args.proxy_username or self.conn_args.username
                if self.conn_args.proxy_password:
                    kwargs["password"] = self.conn_args.proxy_password
        else:
            if self.conn_args.pkey:
                kwargs["pkey"] = self._load_pkey(self.conn_args.pkey, self.conn_args.passphrase)
            elif self.conn_args.key_filename:
                kwargs["key_filename"] = self.conn_args.key_filename
                if self.conn_args.passphrase:
                    kwargs["passphrase"] = self.conn_args.passphrase
            elif self.conn_args.password:
                kwargs["password"] = self.conn_args.password
        return kwargs

    def _connect_direct(self) -> paramiko.SSHClient:
        client = paramiko.SSHClient()
        policy_map = {
            "auto_add": paramiko.AutoAddPolicy(),
            "reject": paramiko.RejectPolicy(),
            "warning": paramiko.WarningPolicy(),
        }
        client.set_missing_host_key_policy(
            policy_map.get(self.conn_args.host_key_policy, paramiko.AutoAddPolicy())
        )

        connect_kwargs = {
            "hostname": self.conn_args.host,
            "port": self.conn_args.port,
            "username": self.conn_args.username,
            "timeout": self.conn_args.timeout,
            "look_for_keys": self.conn_args.look_for_keys,
            "allow_agent": self.conn_args.allow_agent,
            "compress": self.conn_args.compress,
        }
        if self.conn_args.banner_timeout is not None:
            connect_kwargs["banner_timeout"] = self.conn_args.banner_timeout
        if self.conn_args.auth_timeout is not None:
            connect_kwargs["auth_timeout"] = self.conn_args.auth_timeout

        connect_kwargs.update(self._get_auth_kwargs(use_proxy=False))
        client.connect(**connect_kwargs)
        return client

    def _connect_via_proxy(self) -> paramiko.SSHClient:
        proxy_client = paramiko.SSHClient()
        proxy_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        proxy_kwargs = {
            "hostname": self.conn_args.proxy_host,
            "port": self.conn_args.proxy_port,
            "timeout": self.conn_args.timeout,
        }
        proxy_kwargs.update(self._get_auth_kwargs(use_proxy=True))
        proxy_client.connect(**proxy_kwargs)

        transport = proxy_client.get_transport()
        dest_addr = (self.conn_args.host, self.conn_args.port)
        local_addr = (self.conn_args.proxy_host, self.conn_args.proxy_port)
        channel = transport.open_channel("direct-tcpip", dest_addr, local_addr)

        target_client = paramiko.SSHClient()
        policy_map = {
            "auto_add": paramiko.AutoAddPolicy(),
            "reject": paramiko.RejectPolicy(),
            "warning": paramiko.WarningPolicy(),
        }
        target_client.set_missing_host_key_policy(
            policy_map.get(self.conn_args.host_key_policy, paramiko.AutoAddPolicy())
        )

        target_kwargs = {
            "hostname": self.conn_args.host,
            "port": self.conn_args.port,
            "username": self.conn_args.username,
            "sock": channel,
            "timeout": self.conn_args.timeout,
            "look_for_keys": False,
            "allow_agent": False,
        }
        if self.conn_args.banner_timeout is not None:
            target_kwargs["banner_timeout"] = self.conn_args.banner_timeout
        if self.conn_args.auth_timeout is not None:
            target_kwargs["auth_timeout"] = self.conn_args.auth_timeout

        target_kwargs.update(self._get_auth_kwargs(use_proxy=False))
        target_client.connect(**target_kwargs)
        target_client._proxy_client = proxy_client
        return target_client

    def _load_pkey(self, pkey_str: str, passphrase: Optional[str] = None) -> paramiko.PKey:
        key_file = StringIO(pkey_str)
        try:
            key_file.seek(0)
            return paramiko.RSAKey.from_private_key(key_file, password=passphrase)
        except paramiko.ssh_exception.SSHException:
            pass
        try:
            key_file.seek(0)
            return paramiko.Ed25519Key.from_private_key(key_file, password=passphrase)
        except paramiko.ssh_exception.SSHException:
            pass
        raise ValueError("Unsupported key format")

    def send(self, session: paramiko.SSHClient, command: list[str]) -> dict:
        if (
            self.args
            and isinstance(self.args, ParamikoSendCommandArgs)
            and self.args.file_transfer is not None
        ):
            log.debug(f"File transfer detected: {self.args.file_transfer}")
            return self._handle_file_transfer(session, self.args.file_transfer)

        # Check if script_content is provided (function 2: direct script execution)
        if (
            self.args
            and isinstance(self.args, ParamikoSendCommandArgs)
            and self.args.script_content
        ):
            log.debug("Script content execution detected")
            return self._execute_script_content(session, self.args)

        if not command:
            log.warning("No command provided")
            return {}

        try:
            result = {}
            for cmd in command:
                # Check if background execution is requested (function 3)
                if (
                    self.args
                    and isinstance(self.args, ParamikoSendCommandArgs)
                    and self.args.run_in_background
                ):
                    log.debug(f"Background execution requested for: {cmd}")
                    bg_result = self._execute_background_command(session, cmd, self.args)
                    result.update(bg_result)
                else:
                    exec_result = self._execute_command(session, cmd, self.args)
                    result.update(exec_result)
            return result
        except Exception as e:
            log.error(f"Error in sending command: {e}")
            raise e

    def _handle_file_transfer(self, session: paramiko.SSHClient, file_transfer_op) -> dict:
        from .model import ParamikoFileTransferOperation

        if not isinstance(file_transfer_op, ParamikoFileTransferOperation):
            file_transfer_op = ParamikoFileTransferOperation.model_validate(file_transfer_op)

        try:
            if file_transfer_op.operation == "upload":
                result = self._upload_file(
                    session,
                    file_transfer_op.local_path,
                    file_transfer_op.remote_path,
                    file_transfer_op.resume,
                    file_transfer_op.chunk_size,
                )
            elif file_transfer_op.operation == "download":
                result = self._download_file(
                    session,
                    file_transfer_op.remote_path,
                    file_transfer_op.local_path,
                    file_transfer_op.resume,
                    file_transfer_op.chunk_size,
                )
            else:
                raise ValueError(f"Unsupported operation: {file_transfer_op.operation}")

            bytes_transferred = result.get("bytes_transferred", 0)
            total_bytes = result.get("total_bytes", 0)
            
            transfer_result = {
                f"file_transfer_{file_transfer_op.operation}": {
                    "output": f"File transfer completed: {bytes_transferred}/{total_bytes} bytes",
                    "error": "",
                    "exit_status": 0 if result.get("success") else 1,
                    "transfer_result": result,
                }
            }
            
            # Execute command after upload if requested
            if (
                file_transfer_op.operation == "upload"
                and file_transfer_op.execute_after_upload
                and file_transfer_op.execute_command
            ):
                log.debug(f"Executing command after upload: {file_transfer_op.execute_command}")
                exec_result = self._execute_command(
                    session, file_transfer_op.execute_command, self.args
                )
                transfer_result.update(exec_result)
                
                # Cleanup remote file if requested
                if file_transfer_op.cleanup_after_exec:
                    log.debug(f"Cleaning up remote file: {file_transfer_op.remote_path}")
                    cleanup_result = self._execute_command(
                        session, f"rm -f {file_transfer_op.remote_path}", self.args
                    )
                    transfer_result.update(cleanup_result)
            
            return transfer_result
        except Exception as e:
            log.error(f"Error in file transfer: {e}")
            return {
                f"file_transfer_{file_transfer_op.operation}": {
                    "output": "",
                    "error": str(e),
                    "exit_status": 1,
                }
            }

    def config(self, session: paramiko.SSHClient, config: list[str]) -> dict:
        if not config:
            log.warning("No configuration provided")
            return {}

        try:
            result = {}
            for cfg_line in config:
                if self.args and isinstance(self.args, ParamikoSendConfigArgs) and self.args.sudo:
                    cmd = f"sudo -S {cfg_line}"
                else:
                    cmd = cfg_line

                exec_kwargs = {}
                if self.args:
                    if self.args.timeout:
                        exec_kwargs["timeout"] = self.args.timeout
                    if isinstance(self.args, ParamikoSendConfigArgs):
                        exec_kwargs["get_pty"] = self.args.get_pty or (
                            self.args.sudo and self.args.sudo_password is not None
                        )
                    else:
                        exec_kwargs["get_pty"] = False
                    if self.args.environment:
                        exec_kwargs["environment"] = self.args.environment

                stdin, stdout, stderr = session.exec_command(cmd, **exec_kwargs)

                if (
                    self.args
                    and isinstance(self.args, ParamikoSendConfigArgs)
                    and self.args.sudo
                    and self.args.sudo_password
                ):
                    stdin.write(f"{self.args.sudo_password}\n")
                    stdin.flush()

                output = stdout.read().decode("utf-8", errors="replace")
                error = stderr.read().decode("utf-8", errors="replace")
                exit_status = stdout.channel.recv_exit_status()

                result[cfg_line] = {
                    "output": output,
                    "error": error,
                    "exit_status": exit_status,
                }
            return result
        except Exception as e:
            log.error(f"Error in sending config: {e}")
            raise e

    def _execute_command(
        self, session: paramiko.SSHClient, cmd: str, args: Optional[ParamikoSendCommandArgs]
    ) -> dict:
        """Execute a single command and return result"""
        exec_kwargs = {}
        if args and isinstance(args, ParamikoSendCommandArgs):
            if args.timeout:
                exec_kwargs["timeout"] = args.timeout
            exec_kwargs["get_pty"] = args.get_pty
            if args.environment:
                exec_kwargs["environment"] = args.environment
            if args.bufsize != -1:
                exec_kwargs["bufsize"] = args.bufsize

        _stdin, stdout, stderr = session.exec_command(cmd, **exec_kwargs)
        output = stdout.read().decode("utf-8", errors="replace")
        error = stderr.read().decode("utf-8", errors="replace")
        exit_status = stdout.channel.recv_exit_status()

        return {
            cmd: {
                "output": output,
                "error": error,
                "exit_status": exit_status,
            }
        }

    def _execute_script_content(
        self, session: paramiko.SSHClient, args: ParamikoSendCommandArgs
    ) -> dict:
        """Execute script content directly via stdin (function 2)"""
        if not args.script_content:
            raise ValueError("script_content is required for script execution")

        # Build command with interpreter
        interpreter = args.script_interpreter or "bash"
        cmd = interpreter

        # Add working directory if specified
        if args.working_directory:
            cmd = f"cd {args.working_directory} && {cmd}"

        exec_kwargs = {}
        if args.timeout:
            exec_kwargs["timeout"] = args.timeout
        exec_kwargs["get_pty"] = args.get_pty
        if args.environment:
            exec_kwargs["environment"] = args.environment
        if args.bufsize != -1:
            exec_kwargs["bufsize"] = args.bufsize

        stdin, stdout, stderr = session.exec_command(cmd, **exec_kwargs)
        
        # Write script content to stdin
        stdin.write(args.script_content)
        stdin.close()

        output = stdout.read().decode("utf-8", errors="replace")
        error = stderr.read().decode("utf-8", errors="replace")
        exit_status = stdout.channel.recv_exit_status()

        return {
            f"script_execution_{interpreter}": {
                "output": output,
                "error": error,
                "exit_status": exit_status,
                "script_content_length": len(args.script_content),
            }
        }

    def _execute_background_command(
        self, session: paramiko.SSHClient, cmd: str, args: ParamikoSendCommandArgs
    ) -> dict:
        """Execute command in background and return PID (function 3)"""
        import uuid

        # Generate unique identifier for this background task
        task_id = str(uuid.uuid4())[:8]

        # Determine output and PID file paths
        output_file = args.background_output_file or f"/tmp/netpulse_{task_id}.log"
        pid_file = args.background_pid_file or f"/tmp/netpulse_{task_id}.pid"

        # Build background command with nohup
        bg_cmd = f"nohup {cmd} > {output_file} 2>&1 & echo $! > {pid_file}"

        # Execute the background command
        exec_result = self._execute_command(session, bg_cmd, args)

        # Read PID from remote file
        pid = None
        if exec_result[bg_cmd]["exit_status"] == 0:
            try:
                # Read PID file
                read_pid_cmd = f"cat {pid_file}"
                pid_result = self._execute_command(session, read_pid_cmd, args)
                if read_pid_cmd in pid_result:
                    pid_output = pid_result[read_pid_cmd]["output"].strip()
                    if pid_output:
                        pid = int(pid_output)
            except (ValueError, KeyError) as e:
                log.warning(f"Failed to read PID from {pid_file}: {e}")

        # Update result with background task info
        result_key = list(exec_result.keys())[0]
        exec_result[result_key]["background_task"] = {
            "pid": pid,
            "pid_file": pid_file,
            "output_file": output_file,
            "command": cmd,
        }

        return exec_result

    def disconnect(self, session: paramiko.SSHClient):
        try:
            if session:
                session.close()
                if hasattr(session, "_proxy_client"):
                    try:
                        session._proxy_client.close()
                    except Exception as e:
                        log.warning(f"Error closing proxy connection: {e}")
        except Exception as e:
            log.warning(f"Error closing SSH connection: {e}")

    def _upload_file(
        self,
        session: paramiko.SSHClient,
        local_path: str,
        remote_path: str,
        resume: bool = False,
        chunk_size: int = 32768,
    ) -> dict:
        import os

        try:
            sftp = session.open_sftp()
            try:
                local_size = os.path.getsize(local_path)
                remote_size = 0

                if resume:
                    try:
                        remote_attrs = sftp.stat(remote_path)
                        remote_size = remote_attrs.st_size
                        if remote_size >= local_size:
                            return {
                                "success": True,
                                "local_path": local_path,
                                "remote_path": remote_path,
                                "bytes_transferred": local_size,
                                "total_bytes": local_size,
                                "resumed": False,
                            }
                    except (FileNotFoundError, Exception):
                        remote_size = 0

                with open(local_path, "rb") as local_file:
                    if resume and remote_size > 0:
                        local_file.seek(remote_size)

                    mode = "ab" if (resume and remote_size > 0) else "wb"
                    remote_file = sftp.file(remote_path, mode)

                    try:
                        bytes_transferred = remote_size
                        total_bytes = local_size

                        while True:
                            chunk = local_file.read(chunk_size)
                            if not chunk:
                                break
                            remote_file.write(chunk)
                            bytes_transferred += len(chunk)

                        remote_file.close()

                        return {
                            "success": True,
                            "local_path": local_path,
                            "remote_path": remote_path,
                            "bytes_transferred": bytes_transferred,
                            "total_bytes": total_bytes,
                            "resumed": resume and remote_size > 0,
                        }
                    except Exception:
                        remote_file.close()
                        raise
            finally:
                sftp.close()
        except Exception as e:
            log.error(f"Error uploading file: {e}")
            raise

    def _download_file(
        self,
        session: paramiko.SSHClient,
        remote_path: str,
        local_path: str,
        resume: bool = False,
        chunk_size: int = 32768,
    ) -> dict:
        import os

        try:
            sftp = session.open_sftp()
            try:
                remote_attrs = sftp.stat(remote_path)
                remote_size = remote_attrs.st_size
                local_size = 0

                if resume and os.path.exists(local_path):
                    local_size = os.path.getsize(local_path)
                    if local_size >= remote_size:
                        return {
                            "success": True,
                            "local_path": local_path,
                            "remote_path": remote_path,
                            "bytes_transferred": remote_size,
                            "total_bytes": remote_size,
                            "resumed": False,
                        }

                remote_file = sftp.file(remote_path, "rb")
                if resume and local_size > 0:
                    remote_file.seek(local_size)

                mode = "ab" if (resume and local_size > 0) else "wb"
                with open(local_path, mode) as local_file:
                    bytes_transferred = local_size
                    total_bytes = remote_size

                    try:
                        while True:
                            chunk = remote_file.read(chunk_size)
                            if not chunk:
                                break
                            local_file.write(chunk)
                            bytes_transferred += len(chunk)

                        remote_file.close()

                        return {
                            "success": True,
                            "local_path": local_path,
                            "remote_path": remote_path,
                            "bytes_transferred": bytes_transferred,
                            "total_bytes": total_bytes,
                            "resumed": resume and local_size > 0,
                        }
                    except Exception:
                        remote_file.close()
                        raise
            finally:
                sftp.close()
        except Exception as e:
            log.error(f"Error downloading file: {e}")
            raise

    @classmethod
    def test(cls, connection_args: ParamikoConnectionArgs) -> ParamikoDeviceTestInfo:
        conn_args = (
            connection_args
            if isinstance(connection_args, ParamikoConnectionArgs)
            else ParamikoConnectionArgs.model_validate(
                connection_args.model_dump(exclude_none=True)
            )
        )

        driver = cls(args=None, conn_args=conn_args)
        session = None
        try:
            session = driver.connect()
            result = ParamikoDeviceTestInfo(host=conn_args.host)

            transport = session.get_transport()
            if transport and transport.remote_version:
                result.remote_version = transport.remote_version

            return result
        finally:
            if session:
                driver.disconnect(session)


__all__ = ["ParamikoDriver"]
