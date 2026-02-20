import hashlib
import logging
import os
import shlex
import signal
import sys
import threading
import time
import uuid
from io import StringIO
from stat import S_ISDIR
from typing import Any, ClassVar, Dict, List, Optional

import paramiko

from ....models.driver import DriverExecutionResult
from .. import BaseDriver
from .model import (
    BackgroundTaskQuery,
    ParamikoConnectionArgs,
    ParamikoDeviceTestInfo,
    ParamikoExecutionRequest,
    ParamikoSendCommandArgs,
    ParamikoSendConfigArgs,
    StreamQuery,
)

log = logging.getLogger(__name__)


class ParamikoDriver(BaseDriver):
    """
    Paramiko driver with persistent connection support.

    When keepalive is set in connection_args, the driver will maintain
    a persistent SSH connection that is reused across multiple commands.
    """

    driver_name = "paramiko"

    # Persistent connection state (class-level for worker reuse)
    persisted_session: ClassVar[Optional[paramiko.SSHClient]] = None
    persisted_conn_args: ClassVar[Optional[ParamikoConnectionArgs]] = None

    # Monitor thread for keepalive
    _monitor_stop_event: ClassVar[Optional[threading.Event]] = None
    _monitor_thread: ClassVar[Optional[threading.Thread]] = None
    _monitor_lock: ClassVar[threading.Lock] = threading.Lock()

    _HOST_KEY_POLICIES: ClassVar[dict[str, paramiko.MissingHostKeyPolicy]] = {
        "auto_add": paramiko.AutoAddPolicy(),
        "reject": paramiko.RejectPolicy(),
        "warning": paramiko.WarningPolicy(),
    }

    @classmethod
    def _get_persisted_session(
        cls, conn_args: ParamikoConnectionArgs
    ) -> Optional[paramiko.SSHClient]:
        """
        Check if persisted session is still alive, otherwise disconnect it.
        """
        if cls.persisted_session and cls.persisted_conn_args:
            # Check if connection args changed
            if cls.persisted_conn_args.host != conn_args.host:
                log.warning("New connection args detected, disconnecting old session")
                with cls._monitor_lock:
                    try:
                        cls.persisted_session.close()
                    except Exception as e:
                        log.error(f"Error in disconnecting old session: {e}")
                    finally:
                        cls._set_persisted_session(None, None)
                return None

            # Check if session is still alive
            transport = cls.persisted_session.get_transport()
            if transport is None or not transport.is_active():
                log.warning("Persisted session is no longer active, clearing")
                cls._set_persisted_session(None, None)
                return None

        return cls.persisted_session

    @classmethod
    def _set_persisted_session(
        cls, session: Optional[paramiko.SSHClient], conn_args: Optional[ParamikoConnectionArgs]
    ) -> Optional[paramiko.SSHClient]:
        """
        Persist session and connection args. Start monitor thread if keepalive is enabled.
        """
        # Clear
        if session is None:
            if cls.persisted_conn_args and cls.persisted_conn_args.keepalive:
                cls._stop_monitor_thread()
            cls.persisted_session = None
            cls.persisted_conn_args = None
            return None

        # Setup
        cls.persisted_session = session
        cls.persisted_conn_args = conn_args
        if conn_args and conn_args.keepalive:
            cls._start_monitor_thread(session)

        return cls.persisted_session

    @classmethod
    def _start_monitor_thread(cls, session: paramiko.SSHClient):
        """
        Start a keepalive monitor thread for the SSH connection.
        """
        if cls._monitor_thread and cls._monitor_thread.is_alive():
            log.debug("Monitoring thread already running")
            return

        assert cls.persisted_conn_args is not None
        cls._monitor_stop_event = threading.Event()
        host = cls.persisted_conn_args.host
        timeout = cls.persisted_conn_args.keepalive

        def monitor():
            suicide = False
            log.info(f"Paramiko monitoring thread started ({host})")
            assert cls._monitor_stop_event is not None

            while not cls._monitor_stop_event.is_set():
                if cls._monitor_stop_event.wait(timeout=timeout):
                    break

                with cls._monitor_lock:
                    # Double checking
                    if cls._monitor_stop_event.is_set():
                        break

                    # Health checking
                    transport = session.get_transport()
                    if transport is None or not transport.is_active():
                        log.warning(f"Connection to {host} is unhealthy")
                        suicide = True
                        cls._monitor_stop_event.set()
                        break

                    # Keepalive - send a null request
                    try:
                        transport.send_ignore()
                    except Exception as e:
                        log.warning(f"Error in sending keepalive to {host}: {e}")
                        suicide = True
                        cls._monitor_stop_event.set()

            log.debug(f"Paramiko monitoring thread quitting with `suicide={suicide}`.")

            # When connection is disconnected, the worker should suicide.
            if suicide:
                log.info(f"Pinned worker for {host} suicides.")
                os.kill(os.getpid(), signal.SIGTERM)

            sys.exit(0)

        cls._monitor_thread = threading.Thread(target=monitor, daemon=True)
        cls._monitor_thread.start()

    @classmethod
    def _stop_monitor_thread(cls):
        """Stop the monitor thread."""
        if cls._monitor_stop_event:
            cls._monitor_stop_event.set()
        if cls._monitor_thread and cls._monitor_thread.is_alive():
            cls._monitor_thread.join(timeout=5)
        cls._monitor_thread = None
        cls._monitor_stop_event = None

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
            # Check for persisted session if keepalive is enabled
            if self.conn_args.keepalive:
                session = self._get_persisted_session(self.conn_args)
                if session:
                    log.info("Reusing existing Paramiko connection")
                    return session

            # Create new connection
            log.info(f"Creating new Paramiko connection to {self.conn_args.host}...")
            if self.conn_args.proxy_host:
                session = self._connect_via_proxy()
            else:
                session = self._connect_direct()

            # Persist session if keepalive is enabled
            if self.conn_args.keepalive:
                self._set_persisted_session(session, self.conn_args)

            return session
        except Exception as e:
            log.error(f"Error in connecting: {e}")
            raise

    def _get_auth_kwargs(self, use_proxy: bool = False) -> dict:
        """Get authentication kwargs for SSH connection."""
        kwargs = {}
        if use_proxy:
            pkey = self.conn_args.proxy_pkey
            key_filename = self.conn_args.proxy_key_filename
            passphrase = self.conn_args.proxy_passphrase
            password = self.conn_args.proxy_password
            username = self.conn_args.proxy_username or self.conn_args.username
        else:
            pkey = self.conn_args.pkey
            key_filename = self.conn_args.key_filename
            passphrase = self.conn_args.passphrase
            password = self.conn_args.password
            username = None  # Will be set in connect_kwargs

        if pkey:
            kwargs["pkey"] = self._load_pkey(pkey, passphrase)
        elif key_filename:
            kwargs["key_filename"] = key_filename
            if passphrase:
                kwargs["passphrase"] = passphrase
        elif password:
            kwargs["password"] = password

        if username:
            kwargs["username"] = username

        return kwargs

    def _connect_direct(self) -> paramiko.SSHClient:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(
            self._HOST_KEY_POLICIES.get(self.conn_args.host_key_policy, paramiko.AutoAddPolicy())
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
        target_client.set_missing_host_key_policy(
            self._HOST_KEY_POLICIES.get(self.conn_args.host_key_policy, paramiko.AutoAddPolicy())
        )

        target_kwargs = {
            "hostname": self.conn_args.host,
            "port": self.conn_args.port,
            "username": self.conn_args.username,
            "sock": channel,
            "timeout": self.conn_args.timeout,
            "look_for_keys": self.conn_args.look_for_keys,
            "allow_agent": self.conn_args.allow_agent,
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
        # Check if stream query is requested (highest priority)
        if (
            self.args
            and isinstance(self.args, ParamikoSendCommandArgs)
            and self.args.stream_query is not None
        ):
            log.debug(f"Stream query detected: {self.args.stream_query}")
            return self._query_stream(session, self.args.stream_query)

        # Check if task query is requested
        if (
            self.args
            and isinstance(self.args, ParamikoSendCommandArgs)
            and self.args.check_task is not None
        ):
            log.debug(f"Background task query detected: {self.args.check_task}")
            return self._check_background_task(session, self.args.check_task)

        # Check if task listing is requested
        if (
            self.args
            and isinstance(self.args, ParamikoSendCommandArgs)
            and self.args.list_active_tasks
        ):
            log.debug("Active task listing requested")
            tasks = self._list_active_tasks(session)
            return {
                "task_list": DriverExecutionResult(
                    output=f"Found {len(tasks)} active tasks",
                    telemetry={"active_tasks": tasks}
                )
            }

        if (
            self.args
            and isinstance(self.args, ParamikoSendCommandArgs)
            and self.args.file_transfer is not None
        ):
            log.debug(f"File transfer detected: {self.args.file_transfer}")
            return self._handle_file_transfer(session, self.args.file_transfer)

        # Check if script_content is provided for direct script execution
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
                # Check if streaming execution is requested
                if (
                    self.args
                    and isinstance(self.args, ParamikoSendCommandArgs)
                    and self.args.stream
                ):
                    log.debug(f"Stream execution requested for: {cmd}")
                    stream_result = self._execute_stream_command(session, cmd, self.args)
                    result.update(stream_result)
                # Check if background execution is requested
                elif (
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
            return {
                " ".join(command): DriverExecutionResult(
                    output="",
                    error=str(e),
                    exit_status=1,
                    telemetry={"duration_seconds": 0.0},
                )
            }

    def _apply_env_to_command(self, command: str, env: Optional[Dict[str, str]]) -> str:
        """Helper to prepend environment variables to a command string"""
        if not env:
            return command
        # Build export commands
        env_exports = [f"export {k}='{v}'" for k, v in env.items()]
        return f"{' && '.join(env_exports)} && {command}"

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
                    file_transfer_op.recursive,
                    file_transfer_op.sync_mode,
                    file_transfer_op.chunk_size,
                    file_transfer_op.chmod,
                )
            elif file_transfer_op.operation == "download":
                result = self._download_file(
                    session,
                    file_transfer_op.remote_path,
                    file_transfer_op.local_path,
                    file_transfer_op.resume,
                    file_transfer_op.recursive,
                    file_transfer_op.sync_mode,
                    file_transfer_op.chunk_size,
                )
            else:
                raise ValueError(f"Unsupported operation: {file_transfer_op.operation}")

            bytes_used = result.get("bytes_transferred", 0)
            total_bytes = result.get("total_bytes", 0)

            transfer_result = {
                f"file_transfer_{file_transfer_op.operation}": DriverExecutionResult(
                    output=f"File transfer completed: {bytes_used}/{total_bytes} bytes",
                    error="",
                    exit_status=0 if result.get("success") else 1,
                    telemetry={"transfer_result": result},
                )
            }

            # Execute command after upload if requested
            if (
                file_transfer_op.operation == "upload"
                and file_transfer_op.execute_after_upload
                and file_transfer_op.execute_command
            ):
                cmd_after = file_transfer_op.execute_command

                log.debug(f"Executing command after upload: {cmd_after}")
                exec_result = self._execute_command(session, cmd_after, self.args)
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
                f"file_transfer_{file_transfer_op.operation}": DriverExecutionResult(
                    output="",
                    error=str(e),
                    exit_status=1,
                    telemetry={},
                )
            }

    def config(
        self, session: paramiko.SSHClient, config: list[str]
    ) -> Dict[str, DriverExecutionResult]:
        if not config:
            log.warning("No configuration provided")
            return {}


        try:
            result = {}
            for cfg_line in config:
                start_time = time.perf_counter()
                if self.args and isinstance(self.args, ParamikoSendConfigArgs) and self.args.sudo:
                    # Smart wrapping: if command contains redirections or pipes, wrap it in bash -c
                    has_shell_chars = any(c in cfg_line for c in (">", "|", ">>", "<<", "<"))
                    if has_shell_chars and "bash -c" not in cfg_line:
                        cmd = f"sudo -S bash -c {shlex.quote(cfg_line)}"
                    else:
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
                if self.args and self.args.environment:
                    cmd = self._apply_env_to_command(cmd, self.args.environment)

                # Mask sensitive data in logs
                log.debug(f"Executing config line: {cfg_line}")
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
                duration = time.perf_counter() - start_time

                # Clean sudo output
                if (
                    self.args
                    and isinstance(self.args, ParamikoSendConfigArgs)
                    and self.args.sudo
                    and self.args.sudo_password
                ):
                    output = self._clean_sudo_output(output, self.args.sudo_password)

                result[cfg_line] = DriverExecutionResult(
                    output=output,
                    error=error,
                    exit_status=exit_status,
                    telemetry={"duration_seconds": round(duration, 3)},
                )

                # Fail-fast: Stop if stop_on_error is true (default)
                if exit_status != 0 and self.args and getattr(self.args, "stop_on_error", True):
                    log.warning(f"Config aborted at line due to error: {cfg_line}")
                    break
            return result
        except Exception as e:
            log.error(f"Error in sending config: {e}")
            return {
                "\n".join(config): DriverExecutionResult(
                    output="",
                    error=str(e),
                    exit_status=1,
                    telemetry={"duration_seconds": 0.0},
                )
            }

    def _get_local_md5(self, path: str) -> Optional[str]:
        """Calculate MD5 hash of a local file."""
        if not os.path.exists(path) or os.path.isdir(path):
            return None
        hash_md5 = hashlib.md5()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()

    def _get_remote_md5(self, session: paramiko.SSHClient, path: str) -> Optional[str]:
        """Calculate MD5 hash of a remote file using md5sum."""
        cmd = f"md5sum '{path}'"
        # We use a simplified execute logic here to avoid recursion or overhead
        _stdin, stdout, _stderr = session.exec_command(cmd)
        output = stdout.read().decode().strip()
        if output and " " in output:
            return output.split()[0]
        return None

    def _clean_sudo_output(self, output: str, password: str) -> str:
        """Remove sudo password echo and prompt from the output."""
        lines = output.splitlines()
        cleaned_lines = []

        # Standard sudo prompt markers
        noise_markers = [
            password,
            "[sudo] password for",
        ]

        for line in lines:
            if any(marker in line for marker in noise_markers):
                continue
            cleaned_lines.append(line)

        return "\n".join(cleaned_lines).lstrip()


    def _execute_command(
        self, session: paramiko.SSHClient, cmd: str, args: Optional[ParamikoSendCommandArgs]
    ) -> Dict[str, DriverExecutionResult]:
        """Execute a single command and return result with telemetry"""

        start_time = time.perf_counter()

        exec_kwargs = {}
        expect_map = None
        if args and isinstance(args, ParamikoSendCommandArgs):
            if args.timeout:
                exec_kwargs["timeout"] = args.timeout
            exec_kwargs["get_pty"] = args.get_pty
            if args.bufsize != -1:
                exec_kwargs["bufsize"] = args.bufsize
            expect_map = args.expect_map

        exec_cmd = cmd
        if args and args.environment:
            exec_cmd = self._apply_env_to_command(cmd, args.environment)

        # Use interactive handler if expect_map is provided
        if expect_map:
            output, error, exit_status = self._execute_interactive(
                session, exec_cmd, expect_map, **exec_kwargs
            )
        else:
            _stdin, stdout, stderr = session.exec_command(exec_cmd, **exec_kwargs)
            output = stdout.read().decode("utf-8", errors="replace")
            error = stderr.read().decode("utf-8", errors="replace")
            exit_status = stdout.channel.recv_exit_status()

        duration = time.perf_counter() - start_time

        return {
            cmd: DriverExecutionResult(
                output=output,
                error=error,
                exit_status=exit_status,
                telemetry={
                    "duration_seconds": round(duration, 3),
                },
            )
        }

    def _execute_interactive(
        self, session: paramiko.SSHClient, cmd: str, expect_map: dict, **kwargs
    ) -> tuple[str, str, int]:
        """Execute a command in an interactive session with prompt handling"""


        # We need a PTY for interactive interaction
        kwargs["get_pty"] = True
        timeout = kwargs.get("timeout", 60.0)

        # Start command
        stdin, stdout, stderr = session.exec_command(cmd, **kwargs)

        full_output = ""
        # Small timeout for polling each chunk
        poll_interval = 0.2
        max_no_output = int((timeout or 60) / poll_interval)
        no_output_count = 0

        while not stdout.channel.exit_status_ready():
            if stdout.channel.recv_ready():
                chunk = stdout.channel.recv(4096).decode("utf-8", errors="replace")
                if chunk:
                    full_output += chunk
                    no_output_count = 0

                    # Check if any prompt matches
                    for prompt, response in expect_map.items():
                        if prompt in chunk:
                            stdin.write(response + "\n")
                            stdin.flush()
                            break
            else:
                time.sleep(poll_interval)
                no_output_count += 1
                if no_output_count > max_no_output:
                    break

        # Read final output
        if stdout.channel.recv_ready():
            full_output += stdout.channel.recv(4096).decode("utf-8", errors="replace")

        # Avoid blocking on recv_exit_status if the command is still hung
        if not stdout.channel.exit_status_ready():
            log.warning(
                f"Interactive command timed out or hung, attempting graceful interrupt: {cmd}"
            )
            try:
                # Send Ctrl+C
                stdin.write("\x03")
                stdin.flush()
                # Wait a bit for it to react
                time.sleep(1)
            except Exception:
                pass

            if not stdout.channel.exit_status_ready():
                log.error(f"Command still active after interrupt, closing channel: {cmd}")
                stdout.channel.close()
                exit_status = -1  # Mark as abnormal termination
            else:
                exit_status = stdout.channel.recv_exit_status()
        else:
            exit_status = stdout.channel.recv_exit_status()

        error = ""
        if stderr.channel.recv_stderr_ready():
            error = stderr.channel.recv_stderr(4096).decode("utf-8", errors="replace")

        return full_output, error, exit_status

    def _execute_script_content(
        self, session: paramiko.SSHClient, args: ParamikoSendCommandArgs
    ) -> Dict[str, DriverExecutionResult]:
        """Execute script content directly via stdin"""
        if not args.script_content:
            return {}


        start_time = time.perf_counter()

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
        script_content = args.script_content

        stdin.write(script_content)
        stdin.close()

        output = stdout.read().decode("utf-8", errors="replace")
        error = stderr.read().decode("utf-8", errors="replace")
        exit_status = stdout.channel.recv_exit_status()
        duration = time.perf_counter() - start_time
        return {
            f"script_execution_{interpreter}": DriverExecutionResult(
                output=output,
                error=error,
                exit_status=exit_status,
                telemetry={
                    "duration_seconds": round(duration, 3),
                    "script_content_length": len(args.script_content),
                },
            )
        }

    def _execute_background_command(
        self, session: paramiko.SSHClient, cmd: str, args: ParamikoSendCommandArgs
    ) -> Dict[str, DriverExecutionResult]:
        """Execute command in background and return PID"""


        task_id = str(uuid.uuid4())[:8]
        output_file = args.background_output_file or f"/tmp/netpulse_{task_id}.log"
        pid_file = args.background_pid_file or f"/tmp/netpulse_{task_id}.pid"
        meta_file = f"{pid_file}.meta"

        # exec -a sets the process name in 'comm' for later validation
        bg_cmd = (
            f'nohup bash -c "exec -a {task_id} {cmd}" > {output_file} 2>&1 & '
            f"echo $! > {pid_file}; "
            f"echo {int(time.time())} > {pid_file}.ttl; "
            f"echo {task_id} > {meta_file}"
        )

        # Cleanup expired tasks occasionally
        self._cleanup_expired_tasks(session, args.ttl_seconds)

        # Execute the background command
        exec_result = self._execute_command(session, bg_cmd, args)

        # Read PID from remote file
        pid = None
        if exec_result[bg_cmd].exit_status == 0:
            try:
                # Read PID file
                read_pid_cmd = f"cat {pid_file}"
                pid_result = self._execute_command(session, read_pid_cmd, args)
                if read_pid_cmd in pid_result:
                    pid_output = pid_result[read_pid_cmd].output.strip()
                    if pid_output:
                        pid = int(pid_output)
            except (ValueError, KeyError) as e:
                log.warning(f"Failed to read PID from {pid_file}: {e}")

        # Update result with background task info
        result_key = next(iter(exec_result.keys()))
        exec_result[result_key].telemetry["background_task"] = {
            "pid": pid,
            "pid_file": pid_file,
            "output_file": output_file,
            "command": cmd,
        }

        return exec_result

    def _execute_stream_command(
        self, session: paramiko.SSHClient, cmd: str, args: ParamikoSendCommandArgs
    ) -> Dict[str, DriverExecutionResult]:
        """Execute command in streaming mode (returns session_id for polling output)"""


        session_id = str(uuid.uuid4())[:12]
        output_file = f"/tmp/netpulse_stream_{session_id}.log"
        pid_file = f"/tmp/netpulse_stream_{session_id}.pid"
        meta_file = f"{pid_file}.meta"

        bg_cmd = (
            f'nohup bash -c "exec -a {session_id} {cmd}" > {output_file} 2>&1 & '
            f"echo $! > {pid_file}; "
            f"echo {int(time.time())} > {pid_file}.ttl; "
            f"echo {session_id} > {meta_file}"
        )

        # Cleanup expired tasks on this host occasionally
        self._cleanup_expired_tasks(session, args.ttl_seconds if args else 3600)

        # Execute the background command
        exec_result = self._execute_command(session, bg_cmd, args)

        # Read PID from remote file
        pid = None
        if exec_result[bg_cmd].exit_status == 0:
            try:
                read_pid_cmd = f"cat {pid_file}"
                pid_result = self._execute_command(session, read_pid_cmd, args)
                if read_pid_cmd in pid_result:
                    pid_output = pid_result[read_pid_cmd].output.strip()
                    if pid_output:
                        pid = int(pid_output)
            except (ValueError, KeyError) as e:
                log.warning(f"Failed to read PID from {pid_file}: {e}")

        # Since stream command doesn't actually produce output in this call, we return metadata
        return {
            "stream": DriverExecutionResult(
                output=f"Stream session started: {session_id}",
                error="",
                exit_status=0,
                telemetry={
                    "stream": {
                        "session_id": session_id,
                        "pid": pid,
                        "output_file": output_file,
                        "command": cmd,
                    }
                },
            )
        }

    def _query_stream(
        self, session: paramiko.SSHClient, query: StreamQuery
    ) -> Dict[str, DriverExecutionResult]:
        """Query streaming command output with identity verification"""
        sid = query.session_id
        log_f, pid_f = f"/tmp/netpulse_stream_{sid}.log", f"/tmp/netpulse_stream_{sid}.pid"
        meta_f = f"{pid_f}.meta"

        data = {
            "session_id": sid, "completed": False, "exit_code": None, "output": None,
            "output_bytes": 0, "runtime_seconds": None, "killed": False,
            "cleaned": False, "identity_verified": False,
        }

        try:
            # Check PID and verify process identity (comm)
            cmd_pid = f"cat {pid_f} 2>/dev/null"
            res_pid = self._execute_command(session, cmd_pid, None)
            pid = res_pid[cmd_pid].output.strip() if cmd_pid in res_pid else None

            if pid and pid.isdigit():
                check_c = f"ps -p {pid} -o pid,etime,comm --no-headers 2>/dev/null"
                res_check = self._execute_command(session, check_c, None)
                out = res_check[check_c].output.strip()

                if out:
                    parts = out.split()
                    if len(parts) >= 3 and parts[0] == pid and parts[2] == sid:
                        data.update({"completed": False, "identity_verified": True})
                        try:
                            data["runtime_seconds"] = self._parse_etime(parts[1])
                        except Exception:
                            pass

                        if query.kill:
                            kill_c = (
                                f"kill -15 {pid} 2>/dev/null; "
                                "sleep 0.5; "
                                f"kill -9 {pid} 2>/dev/null"
                            )
                            self._execute_command(session, kill_c, None)
                            data.update({"killed": True, "completed": True})
                    else:
                        log.warning(f"Stream PID {pid} reuse detected! '{out}' != '{sid}'")
                        data["completed"] = True
                else:
                    data.update({"completed": True, "exit_code": 0})

            # Read output
            read_c = f"tail -n {query.lines} {log_f} 2>/dev/null"
            if query.offset > 0:
                read_c = (
                    f"dd if={log_f} bs=1 skip={query.offset} 2>/dev/null "
                    f"| tail -n {query.lines}"
                )

            data["output"] = self._execute_command(session, read_c, None)[read_c].output

            # Update sizing
            size_c = f"stat -c%s {log_f} 2>/dev/null || echo 0"
            size_out = self._execute_command(session, size_c, None)[size_c].output.strip()
            data["output_bytes"] = data["next_offset"] = int(size_out) if size_out.isdigit() else 0

            if query.cleanup and data["completed"]:
                clean_c = f"rm -f {log_f} {pid_f} {pid_f}.ttl {meta_f} 2>/dev/null"
                self._execute_command(session, clean_c, None)
                data["cleaned"] = True

        except Exception as e:
            log.error(f"Error querying stream: {e}")
            data["error"] = str(e)

        return {
            "stream_result": DriverExecutionResult(
                output=data.get("output") or "",
                error=data.get("error", ""),
                exit_status=data.get("exit_code") or 0,
                telemetry={"stream_result": data},
            )
        }

    def _check_background_task(
        self, session: paramiko.SSHClient, query: BackgroundTaskQuery
    ) -> Dict[str, DriverExecutionResult]:
        """Check status of a background task by PID with identity verification"""
        pid = query.pid
        data = {
            "pid": pid, "running": False, "exit_code": 0, "output_tail": None,
            "runtime_seconds": None, "killed": False, "cleaned": False,
            "identity_verified": False,
        }

        try:
            # Verify process against comm via ps
            cmd_check = f"ps -p {pid} -o pid,etime,comm --no-headers 2>/dev/null"
            out = self._execute_command(session, cmd_check, None)[cmd_check].output.strip()

            if out:
                parts = out.split()
                if len(parts) >= 3 and parts[0] == str(pid):
                    # Pull expected task ID from meta file if available
                    ident = None
                    if query.output_file:
                        meta_p = query.output_file.replace(".log", ".pid.meta")
                        cmd_m = f"cat {meta_p} 2>/dev/null"
                        res_m = self._execute_command(session, cmd_m, None)
                        ident = res_m[cmd_m].output.strip() if cmd_m in res_m else None

                    if ident and parts[2] != ident:
                        log.warning(f"PID {pid} reuse detected! '{parts[2]}' != '{ident}'")
                    else:
                        data.update({
                            "running": True,
                            "identity_verified": True if ident else False
                        })
                        try:
                            data["runtime_seconds"] = self._parse_etime(parts[1])
                        except Exception:
                            pass

                        if query.kill_if_running:
                            kill_c = (
                                f"kill -15 {pid} 2>/dev/null; "
                                "sleep 0.5; "
                                f"kill -9 {pid} 2>/dev/null"
                            )
                            self._execute_command(session, kill_c, None)
                            data.update({"killed": True, "running": False})

            if query.output_file:
                tail_c = f"tail -n {query.tail_lines} {query.output_file} 2>/dev/null"
                data["output_tail"] = self._execute_command(session, tail_c, None)[tail_c].output

            if query.cleanup_files and not data["running"]:
                if query.output_file:
                    base = query.output_file.replace(".log", "")
                    clean_c = (
                        f"rm -f {base}.log {base}.pid "
                        f"{base}.pid.ttl {base}.pid.meta 2>/dev/null"
                    )
                    self._execute_command(session, clean_c, None)
                    data["cleaned"] = True

        except Exception as e:
            log.error(f"Error checking background task: {e}")
            data["error"] = str(e)

        return {
            "task_query": DriverExecutionResult(
                output=data.get("output_tail") or "",
                error=data.get("error", ""),
                exit_status=data.get("exit_code") or 0,
                telemetry={"task_query": data},
            )
        }

    def _parse_etime(self, etime: str) -> int:
        """Parse ps etime format to seconds"""
        # Format: [[DD-]HH:]MM:SS
        total_seconds = 0

        # Handle days
        if "-" in etime:
            days_part, etime = etime.split("-")
            total_seconds += int(days_part) * 86400

        parts = etime.split(":")
        if len(parts) == 3:  # HH:MM:SS
            total_seconds += int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
        elif len(parts) == 2:  # MM:SS
            total_seconds += int(parts[0]) * 60 + int(parts[1])
        else:  # SS
            total_seconds += int(parts[0])

        return total_seconds

    def _cleanup_expired_tasks(self, session: paramiko.SSHClient, ttl: int):
        """Clean up expired temporary files on the remote host"""
        try:
            # Find all .ttl files in /tmp/netpulse_*
            find_cmd = "ls /tmp/netpulse_*.ttl 2>/dev/null"
            find_result = self._execute_command(session, find_cmd, None)
            ttl_files = find_result[find_cmd].output.strip().split()

            if not ttl_files:
                return

            current_time = int(time.time())
            files_to_remove = []

            for ttl_file in ttl_files:
                try:
                    # Read creation time
                    read_cmd = f"cat {ttl_file} 2>/dev/null"
                    read_result = self._execute_command(session, read_cmd, None)
                    creation_time_str = read_result[read_cmd].output.strip()
                    if not creation_time_str:
                        continue

                    creation_time = int(creation_time_str)
                    if current_time - creation_time > ttl:
                        # Expired, mark for removal
                        # ttl_file is like /tmp/netpulse_xxx.pid.ttl or /tmp/netpulse_xxx.ttl
                        base_path = ttl_file.replace(".ttl", "")
                        files_to_remove.extend([
                            ttl_file,
                            base_path,                       # The .pid file
                            base_path.replace(".pid", ".log"), # The .log file
                            base_path + ".meta"              # The .meta file
                        ])
                except Exception:
                    continue

            if files_to_remove:
                rm_cmd = f"rm -f {' '.join(files_to_remove)} 2>/dev/null"
                self._execute_command(session, rm_cmd, None)
        except Exception as e:
            log.warning(f"Failed to cleanup expired tasks: {e}")

    def _list_active_tasks(self, session: paramiko.SSHClient) -> List[Dict[str, Any]]:
        """List all active background tasks on the remote host by scanning meta files"""
        tasks = []
        try:
            # 1. Scan for all .meta files
            ls_cmd = "ls /tmp/netpulse_*.pid.meta 2>/dev/null"
            meta_files = self._execute_command(session, ls_cmd, None)[ls_cmd].output.strip().split()

            for meta_f in meta_files:
                try:
                    # 2. Get task identity and PID
                    cmd_m = f"cat {meta_f}"
                    task_id = self._execute_command(session, cmd_m, None)[cmd_m].output.strip()
                    pid_f = meta_f.replace(".meta", "")
                    cmd_p = f"cat {pid_f}"
                    pid_out = self._execute_command(session, cmd_p, None)[cmd_p].output.strip()

                    if not pid_out.isdigit():
                        continue

                    pid = int(pid_out)

                    # 3. Verify process is still running with this identity
                    ps_cmd = f"ps -p {pid} -o comm= --no-headers 2>/dev/null"
                    comm = self._execute_command(session, ps_cmd, None)[ps_cmd].output.strip()

                    if comm == task_id:
                        tasks.append({
                            "task_id": task_id,
                            "pid": pid,
                            "type": "stream" if "stream" in meta_f else "background",
                            "pid_file": pid_f,
                            "meta_file": meta_f,
                            "log_file": pid_f.replace(".pid", ".log")
                        })
                except Exception:
                    continue
        except Exception as e:
            log.warning(f"Error listing active tasks: {e}")

        return tasks

    def disconnect(self, session: paramiko.SSHClient, reset: bool = False):
        """
        Disconnect the session.

        When keepalive is enabled, the connection is kept alive for reuse
        unless reset=True is specified.
        """
        # If keepalive is enabled and not resetting, keep the connection
        if self.conn_args.keepalive and not reset:
            return

        with self._monitor_lock:
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
            finally:
                if self.conn_args.keepalive:
                    self._set_persisted_session(None, None)

    def _upload_file(
        self,
        session: paramiko.SSHClient,
        local_path: str,
        remote_path: str,
        resume: bool = False,
        recursive: bool = False,
        sync_mode: str = "full",
        chunk_size: int = 32768,
        chmod: Optional[str] = None,
    ) -> dict:
        try:
            sftp = session.open_sftp()
            try:
                # Handle recursive upload
                if recursive and os.path.isdir(local_path):
                    total_bytes = 0
                    files_transferred = 0
                    files_skipped = 0

                    for root, dirs, files in os.walk(local_path):
                        # Create remote directories
                        rel_path = os.path.relpath(root, local_path)
                        if rel_path == ".":
                            dest_dir = remote_path
                        else:
                            dest_dir = os.path.join(remote_path, rel_path).replace("\\", "/")

                        try:
                            sftp.mkdir(dest_dir)
                        except IOError:
                            pass  # Directory might already exist

                        for file in files:
                            local_file = os.path.join(root, file)
                            remote_file = os.path.join(dest_dir, file).replace("\\", "/")

                            res = self._upload_file(
                                session,
                                local_file,
                                remote_file,
                                resume=resume,
                                recursive=False,
                                sync_mode=sync_mode,
                                chunk_size=chunk_size,
                                chmod=chmod,
                            )
                            if res.get("success"):
                                total_bytes += res.get("bytes_transferred", 0)
                                if res.get("skipped"):
                                    files_skipped += 1
                                else:
                                    files_transferred += 1

                    return {
                        "success": True,
                        "local_path": local_path,
                        "remote_path": remote_path,
                        "bytes_transferred": total_bytes,
                        "files_transferred": files_transferred,
                        "files_skipped": files_skipped,
                        "recursive": True,
                    }

                # Single file upload logic
                if not os.path.exists(local_path):
                    raise FileNotFoundError(f"Local file not found: {local_path}")

                local_size = os.path.getsize(local_path)
                remote_size = 0
                remote_exists = False

                try:
                    remote_attrs = sftp.stat(remote_path)
                    remote_size = remote_attrs.st_size
                    remote_exists = True
                except (FileNotFoundError, IOError):
                    pass

                # Hash-based sync check
                if sync_mode == "hash" and remote_exists:
                    local_md5 = self._get_local_md5(local_path)
                    remote_md5 = self._get_remote_md5(session, remote_path)
                    if local_md5 == remote_md5:
                        return {
                            "success": True,
                            "local_path": local_path,
                            "remote_path": remote_path,
                            "bytes_transferred": 0,
                            "total_bytes": local_size,
                            "skipped": True,
                            "sync_mode": "hash",
                        }

                if resume and remote_exists:
                    if remote_size >= local_size:
                        return {
                            "success": True,
                            "local_path": local_path,
                            "remote_path": remote_path,
                            "bytes_transferred": local_size,
                            "total_bytes": local_size,
                            "resumed": False,
                        }

                with open(local_path, "rb") as local_file:
                    if resume and remote_size > 0:
                        local_file.seek(remote_size)

                    mode = "ab" if (resume and remote_size > 0) else "wb"
                    remote_file = sftp.file(remote_path, mode)

                    try:
                        bytes_transferred = remote_size
                        while True:
                            chunk = local_file.read(chunk_size)
                            if not chunk:
                                break
                            remote_file.write(chunk)
                            bytes_transferred += len(chunk)

                        remote_file.close()

                        # Set permissions if requested
                        if chmod:
                            try:
                                # Convert octal string '0755' to int
                                mode = int(chmod, 8)
                                sftp.chmod(remote_path, mode)
                            except Exception as e:
                                log.warning(f"Failed to set chmod {chmod} on {remote_path}: {e}")

                        return {
                            "success": True,
                            "local_path": local_path,
                            "remote_path": remote_path,
                            "bytes_transferred": bytes_transferred,
                            "total_bytes": local_size,
                            "resumed": resume and remote_size > 0,
                        }
                    except Exception:
                        remote_file.close()
                        raise
            finally:
                sftp.close()
        except Exception as e:
            log.error(f"Error uploading file {local_path}: {e}")
            raise

    def _download_file(
        self,
        session: paramiko.SSHClient,
        remote_path: str,
        local_path: str,
        resume: bool = False,
        recursive: bool = False,
        sync_mode: str = "full",
        chunk_size: int = 32768,
    ) -> dict:
        try:
            sftp = session.open_sftp()
            try:
                # Handle recursive download
                try:
                    remote_attrs = sftp.stat(remote_path)
                    if recursive and S_ISDIR(remote_attrs.st_mode):
                        total_bytes = 0
                        files_transferred = 0
                        files_skipped = 0

                        if not os.path.exists(local_path):
                            os.makedirs(local_path)

                        for entry in sftp.listdir_attr(remote_path):
                            remote_entry = os.path.join(remote_path, entry.filename).replace(
                                "\\", "/"
                            )
                            local_entry = os.path.join(local_path, entry.filename)

                            if S_ISDIR(entry.st_mode):
                                res = self._download_file(
                                    session,
                                    remote_entry,
                                    local_entry,
                                    resume=resume,
                                    recursive=True,
                                    sync_mode=sync_mode,
                                    chunk_size=chunk_size,
                                )
                            else:
                                res = self._download_file(
                                    session,
                                    remote_entry,
                                    local_entry,
                                    resume=resume,
                                    recursive=False,
                                    sync_mode=sync_mode,
                                    chunk_size=chunk_size,
                                )

                            if res.get("success"):
                                total_bytes += res.get("bytes_transferred", 0)
                                if res.get("skipped"):
                                    files_skipped += 1
                                else:
                                    files_transferred += 1

                        return {
                            "success": True,
                            "local_path": local_path,
                            "remote_path": remote_path,
                            "bytes_transferred": total_bytes,
                            "files_transferred": files_transferred,
                            "files_skipped": files_skipped,
                            "recursive": True,
                        }
                except (FileNotFoundError, IOError):
                    raise FileNotFoundError(f"Remote path not found: {remote_path}")

                # Single file download logic
                remote_size = remote_attrs.st_size
                local_size = 0
                local_exists = os.path.exists(local_path)

                # Hash-based sync check
                if sync_mode == "hash" and local_exists:
                    local_md5 = self._get_local_md5(local_path)
                    remote_md5 = self._get_remote_md5(session, remote_path)
                    if local_md5 == remote_md5:
                        return {
                            "success": True,
                            "local_path": local_path,
                            "remote_path": remote_path,
                            "bytes_transferred": 0,
                            "total_bytes": remote_size,
                            "skipped": True,
                            "sync_mode": "hash",
                        }

                if resume and local_exists:
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
                            "total_bytes": remote_size,
                            "resumed": resume and local_size > 0,
                        }
                    except Exception:
                        remote_file.close()
                        raise
            finally:
                sftp.close()
        except Exception as e:
            log.error(f"Error downloading file {remote_path}: {e}")
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
