import hashlib
import logging
import os
import signal
import sys
import threading
from io import StringIO
from stat import S_ISDIR
from typing import ClassVar, Dict, Optional

import paramiko

from ... import renderers
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

        # Render commands if context is provided
        context = (
            (
                self.args.get("context")
                if isinstance(self.args, dict)
                else getattr(self.args, "context", None)
            )
            if self.args
            else None
        )
        if context:
            command = [self._render(cmd, context) for cmd in command]

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
                # Check if background execution is requested (function 3)
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
            raise e

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
                cmd_after = file_transfer_op.execute_command
                if self.args and getattr(self.args, "context", None):
                    cmd_after = self._render(cmd_after, self.args.context)

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

        # Render config if context is provided
        context = (
            (
                self.args.get("context")
                if isinstance(self.args, dict)
                else getattr(self.args, "context", None)
            )
            if self.args
            else None
        )
        if context:
            config = [self._render(cfg, context) for cfg in config]

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
                if self.args and self.args.environment:
                    cmd = self._apply_env_to_command(cmd, self.args.environment)

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

    def _render(self, template: str, context: dict) -> str:
        """Render a string using Jinja2 renderer."""
        try:
            # Use the existing Jinja2 plugin
            renderer_cls = renderers.get("jinja2")
            if not renderer_cls:
                log.warning("Jinja2 renderer not found, returning raw template")
                return template

            # Case: renderer_cls is a class, we need to instantiate it
            # The Jinja2Renderer.__init__ expects (source, options)
            renderer = renderer_cls(source=template)
            return renderer.render(context)
        except Exception as e:
            log.error(f"Error in Jinja2 rendering: {e}")
            # If rendering fails, we might want to return the original template
            # or raise. Since this is an explicit feature, raising is safer.
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
            if args.bufsize != -1:
                exec_kwargs["bufsize"] = args.bufsize
        exec_cmd = cmd
        if args and args.environment:
            exec_cmd = self._apply_env_to_command(cmd, args.environment)

        _stdin, stdout, stderr = session.exec_command(exec_cmd, **exec_kwargs)
        output = stdout.read().decode("utf-8", errors="replace")
        error = stderr.read().decode("utf-8", errors="replace")
        exit_status = stdout.channel.recv_exit_status()

        # Try to parse JSON for a better experience
        output_json = None
        if output.strip().startswith(("{", "[")):
            try:
                import json
                output_json = json.loads(output)
            except Exception:
                pass

        return {
            cmd: {
                "output": output,
                "output_json": output_json,
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
        script_content = args.script_content
        if args.context:
            script_content = self._render(script_content, args.context)

        stdin.write(script_content)
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
        result_key = next(iter(exec_result.keys()))
        exec_result[result_key]["background_task"] = {
            "pid": pid,
            "pid_file": pid_file,
            "output_file": output_file,
            "command": cmd,
        }

        return exec_result

    def _execute_stream_command(
        self, session: paramiko.SSHClient, cmd: str, args: ParamikoSendCommandArgs
    ) -> dict:
        """Execute command in streaming mode (returns session_id for polling output)"""
        import uuid

        # Generate unique session ID
        session_id = str(uuid.uuid4())[:12]

        # Determine output and PID file paths
        output_file = f"/tmp/netpulse_stream_{session_id}.log"
        pid_file = f"/tmp/netpulse_stream_{session_id}.pid"

        # Build background command with nohup
        bg_cmd = f"nohup {cmd} > {output_file} 2>&1 & echo $! > {pid_file}"

        # Execute the background command
        exec_result = self._execute_command(session, bg_cmd, args)

        # Read PID from remote file
        pid = None
        if exec_result[bg_cmd]["exit_status"] == 0:
            try:
                read_pid_cmd = f"cat {pid_file}"
                pid_result = self._execute_command(session, read_pid_cmd, args)
                if read_pid_cmd in pid_result:
                    pid_output = pid_result[read_pid_cmd]["output"].strip()
                    if pid_output:
                        pid = int(pid_output)
            except (ValueError, KeyError) as e:
                log.warning(f"Failed to read PID from {pid_file}: {e}")

        return {
            "stream": {
                "session_id": session_id,
                "pid": pid,
                "output_file": output_file,
                "command": cmd,
            }
        }

    def _query_stream(self, session: paramiko.SSHClient, query: StreamQuery) -> dict:
        """Query streaming command output by session_id"""
        import time

        session_id = query.session_id
        output_file = f"/tmp/netpulse_stream_{session_id}.log"
        pid_file = f"/tmp/netpulse_stream_{session_id}.pid"

        result = {
            "stream_result": {
                "session_id": session_id,
                "completed": False,
                "exit_code": None,
                "output": None,
                "output_bytes": 0,
                "runtime_seconds": None,
                "killed": False,
                "cleaned": False,
            }
        }

        try:
            # Read PID
            pid = None
            read_pid_cmd = f"cat {pid_file} 2>/dev/null"
            pid_result = self._execute_command(session, read_pid_cmd, None)
            pid_output = pid_result[read_pid_cmd]["output"].strip()
            if pid_output:
                try:
                    pid = int(pid_output)
                except ValueError:
                    pass

            # Check if process is running
            if pid:
                check_cmd = f"ps -p {pid} -o pid,etime --no-headers 2>/dev/null"
                check_result = self._execute_command(session, check_cmd, None)
                check_output = check_result[check_cmd]["output"].strip()

                if check_output and str(pid) in check_output:
                    # Still running
                    result["stream_result"]["completed"] = False

                    # Parse runtime
                    try:
                        parts = check_output.split()
                        if len(parts) >= 2:
                            result["stream_result"]["runtime_seconds"] = self._parse_etime(parts[1])
                    except (IndexError, ValueError):
                        pass

                    # Kill if requested
                    if query.kill:
                        kill_cmd = (
                            f"kill -15 {pid} 2>/dev/null; "
                            f"sleep 0.5; "
                            f"kill -9 {pid} 2>/dev/null"
                        )
                        self._execute_command(session, kill_cmd, None)
                        result["stream_result"]["killed"] = True
                        result["stream_result"]["completed"] = True
                        time.sleep(0.5)
                else:
                    result["stream_result"]["completed"] = True
                    result["stream_result"]["exit_code"] = 0  # Assume success

            # Read output (tail or from offset)
            if query.offset > 0:
                # Read from offset using dd
                read_cmd = (
                    f"dd if={output_file} bs=1 skip={query.offset} 2>/dev/null "
                    f"| tail -n {query.lines}"
                )
            else:
                read_cmd = f"tail -n {query.lines} {output_file} 2>/dev/null"

            output_result = self._execute_command(session, read_cmd, None)
            output = output_result[read_cmd]["output"]
            result["stream_result"]["output"] = output

            # Get file size for next offset
            size_cmd = f"stat -c%s {output_file} 2>/dev/null || echo 0"
            size_result = self._execute_command(session, size_cmd, None)
            try:
                result["stream_result"]["output_bytes"] = int(
                    size_result[size_cmd]["output"].strip()
                )
            except ValueError:
                pass

            # Cleanup if requested and completed
            if query.cleanup and result["stream_result"]["completed"]:
                cleanup_cmd = f"rm -f {output_file} {pid_file} 2>/dev/null"
                self._execute_command(session, cleanup_cmd, None)
                result["stream_result"]["cleaned"] = True

        except Exception as e:
            log.error(f"Error querying stream: {e}")
            result["stream_result"]["error"] = str(e)

        return result

    def _check_background_task(
        self, session: paramiko.SSHClient, query: BackgroundTaskQuery
    ) -> dict:
        """Check status of a background task by PID"""
        import time

        pid = query.pid
        result = {
            "task_query": {
                "pid": pid,
                "running": False,
                "exit_code": None,
                "output_tail": None,
                "runtime_seconds": None,
                "killed": False,
                "cleaned": False,
            }
        }

        try:
            # Check if process is running
            check_cmd = f"ps -p {pid} -o pid,etime --no-headers 2>/dev/null"
            check_result = self._execute_command(session, check_cmd, None)
            check_output = check_result[check_cmd]["output"].strip()

            if check_output and str(pid) in check_output:
                result["task_query"]["running"] = True

                # Parse elapsed time (format: [[DD-]HH:]MM:SS)
                try:
                    parts = check_output.split()
                    if len(parts) >= 2:
                        etime = parts[1]
                        # Parse elapsed time to seconds
                        runtime = self._parse_etime(etime)
                        result["task_query"]["runtime_seconds"] = runtime
                except (IndexError, ValueError):
                    pass

                # Kill if requested
                if query.kill_if_running:
                    kill_cmd = (
                        f"kill -15 {pid} 2>/dev/null; "
                        f"sleep 1; "
                        f"kill -9 {pid} 2>/dev/null; "
                        "echo done"
                    )
                    self._execute_command(session, kill_cmd, None)
                    result["task_query"]["killed"] = True
                    result["task_query"]["running"] = False
                    time.sleep(0.5)  # Give it time to die

            # Get output tail if output file is specified
            if query.output_file:
                tail_cmd = f"tail -n {query.tail_lines} {query.output_file} 2>/dev/null"
                tail_result = self._execute_command(session, tail_cmd, None)
                output_tail = tail_result[tail_cmd]["output"]
                if output_tail:
                    result["task_query"]["output_tail"] = output_tail

            # Try to get exit code if task is not running
            if not result["task_query"]["running"]:
                # Check via /proc if available
                exit_cmd = f"cat /proc/{pid}/stat 2>/dev/null || echo 'not_found'"
                exit_result = self._execute_command(session, exit_cmd, None)
                if "not_found" in exit_result[exit_cmd]["output"]:
                    # Process exited, exit code not directly available
                    result["task_query"]["exit_code"] = 0  # Assume success if no error in output

            # Cleanup files if requested and task is complete
            if query.cleanup_files and not result["task_query"]["running"]:
                cleanup_files = []
                if query.output_file:
                    cleanup_files.append(query.output_file)
                    # Also try to cleanup related pid file
                    pid_file = query.output_file.replace(".log", ".pid")
                    cleanup_files.append(pid_file)

                if cleanup_files:
                    cleanup_cmd = f"rm -f {' '.join(cleanup_files)} 2>/dev/null"
                    self._execute_command(session, cleanup_cmd, None)
                    result["task_query"]["cleaned"] = True

        except Exception as e:
            log.error(f"Error checking background task: {e}")
            result["task_query"]["error"] = str(e)

        return result

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
