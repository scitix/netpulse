import hashlib
import logging
import os
import shlex
import signal
import sys
import threading
import time
from io import StringIO
from stat import S_ISDIR
from typing import Any, ClassVar, Dict, List, Optional, Tuple

import paramiko

from ....models.common import FileTransferModel
from ....models.driver import DriverExecutionResult
from .. import BaseDriver
from .model import (
    ParamikoConnectionArgs,
    ParamikoDeviceTestInfo,
    ParamikoExecutionRequest,
    ParamikoSendCommandArgs,
    ParamikoSendConfigArgs,
)

log = logging.getLogger(__name__)

# File and process prefix for detached tasks
DETACHED_TASK_FILE_PREFIX = "np"
# Process name prefix for easy identification via `ps`
DETACHED_TASK_PROCESS_PREFIX = "np_"


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
        return cls(
            args=req.driver_args,
            conn_args=req.connection_args,
            staged_file_id=req.staged_file_id,
            job_id=getattr(req, "id", None),
            file_transfer=req.file_transfer,
        )

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
            req = ParamikoExecutionRequest.model_validate(req.model_dump())

    def __init__(
        self,
        args: Optional[ParamikoSendCommandArgs | ParamikoSendConfigArgs],
        conn_args: ParamikoConnectionArgs,
        staged_file_id: Optional[str] = None,
        file_transfer: Optional[Any] = None,
        **kwargs,
    ):
        super().__init__(staged_file_id=staged_file_id, **kwargs)
        self.args = args
        self.conn_args = conn_args
        self.file_transfer = file_transfer

    def connect(self) -> paramiko.SSHClient:
        try:
            # Optimistically check for persisted session
            session = self._get_persisted_session(self.conn_args)
            if session:
                log.info("Reusing existing Paramiko connection")
                self._session_reused = True
                return session

            # Create new connection
            log.info(f"Creating new Paramiko connection to {self.conn_args.host}...")
            if self.conn_args.proxy_host:
                session = self._connect_via_proxy()
            else:
                session = self._connect_direct()

            # Persist session if keepalive is enabled
            if self.conn_args.keepalive:
                self._session_reused = False  # New connection
                self._set_persisted_session(session, self.conn_args)

            # Cleanup expired task files on the remote host
            self._cleanup_expired_tasks(session)

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

    def send(self, session: paramiko.SSHClient, command: list[str]) -> list[DriverExecutionResult]:
        # Check if log reading is requested (for task management)
        if (
            self.args
            and isinstance(self.args, ParamikoSendCommandArgs)
            and self.args.read_detached_task_logs is not None
        ):
            log_query = self.args.read_detached_task_logs
            return self._read_logs(session, log_query.get("task_id"), log_query.get("offset", 0))

        if (
            self.args
            and isinstance(self.args, ParamikoSendCommandArgs)
            and getattr(self.args, "list_active_detached_tasks", False)
        ):
            tasks = self._list_active_tasks(session)
            return [
                DriverExecutionResult(
                    command="list_active_detached_tasks",
                    output=f"Found {len(tasks)} active detached tasks",
                    error="",
                    exit_status=0,
                    metadata={"active_tasks": tasks},
                )
            ]

        # Check for top-level file transfer first
        if self.file_transfer:
            log.debug(f"Top-level file transfer detected: {self.file_transfer}")
            return self._handle_file_transfer(session, self.file_transfer, skip_exec=False)

        if (
            self.args
            and isinstance(self.args, ParamikoSendCommandArgs)
            and getattr(self.args, "file_transfer", None) is not None
        ):
            ft_op = getattr(self.args, "file_transfer")
            log.debug(f"Nested file transfer detected: {ft_op}")
            return self._handle_file_transfer(session, ft_op, skip_exec=False)

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
            return []

        start_time = time.perf_counter()
        try:
            result = []
            for cmd in command:
                exec_result = self._execute_command(session, cmd, self.args)
                result.append(exec_result)
            return result
        except Exception as e:
            log.error(f"Error in send: {e}")
            return [
                DriverExecutionResult(
                    command=" ".join(command) if command else "error",
                    output="",
                    error=str(e),
                    exit_status=1,
                    metadata=self._get_base_metadata(start_time),
                )
            ]

    def _get_detached_dir(self) -> str:
        """Get the user-isolated directory for detached task files."""
        user = self.conn_args.username
        return f"/tmp/np-detached-{user}"

    # =========================================================================
    # Detach Implementation (Standardized)
    # =========================================================================

    def launch_detached(
        self, session: paramiko.SSHClient, cmd: str, task_id: str
    ) -> list[DriverExecutionResult]:
        """
        Launch a command in the background on the remote host with advanced features.
        Supports standard commands, script content, or execution after file transfer.
        """
        detached_dir = self._get_detached_dir()
        # Ensure detached task directory exists with correct permissions
        self._execute_command(session, f"mkdir -p {detached_dir} && chmod 700 {detached_dir}", None)

        output_file = f"{detached_dir}/{DETACHED_TASK_FILE_PREFIX}_{task_id}.log"
        pid_file = f"{detached_dir}/{DETACHED_TASK_FILE_PREFIX}_{task_id}.pid"
        meta_file = f"{pid_file}.meta"
        age_file = f"{pid_file}.age"

        proc_name = f"{DETACHED_TASK_PROCESS_PREFIX}{task_id}"

        # Determine the actual command to run
        final_cmd = cmd

        # Case 1: Standardized Top-level File Transfer + Detached Execution
        if self.file_transfer and self.file_transfer.operation == "upload":
            log.info(f"Detached: Performing upload before launch for task {task_id}")
            up_res = self._handle_file_transfer(session, self.file_transfer, skip_exec=True)
            up_key = f"file_transfer_{self.file_transfer.operation}"
            if up_res.get(up_key) and up_res[up_key].exit_status == 0:
                if self.file_transfer.execute_after_upload and self.file_transfer.execute_command:
                    final_cmd = self.file_transfer.execute_command
            else:
                return up_res

        # Case 2: Legacy/Nested File Transfer or Script Content
        elif self.args and isinstance(self.args, ParamikoSendCommandArgs):
            # Safe check for nested file_transfer
            ft_op = getattr(self.args, "file_transfer", None)
            if ft_op and ft_op.operation == "upload":
                log.info(f"Detached: Performing nested upload before launch for task {task_id}")
                up_res = self._handle_file_transfer(session, ft_op, skip_exec=True)
                up_key = f"file_transfer_{ft_op.operation}"
                if up_res.get(up_key) and up_res[up_key].exit_status == 0:
                    if ft_op.execute_after_upload and ft_op.execute_command:
                        final_cmd = ft_op.execute_command
                else:
                    return up_res

            # Case 3: Script Content + Detached Execution
            elif self.args.script_content:
                log.info(f"Detached: Writing script content for task {task_id}")
                script_path = f"{detached_dir}/{DETACHED_TASK_FILE_PREFIX}_{task_id}.sh"
                content_quoted = shlex.quote(self.args.script_content)
                write_cmd = f"printf %s {content_quoted} > {script_path} && chmod +x {script_path}"
                self._execute_command(session, write_cmd, None)
                interpreter = self.args.script_interpreter or "bash"
                final_cmd = f"{interpreter} {script_path}"

        if not final_cmd:
            return {
                "launch": DriverExecutionResult(
                    output="",
                    error="No command provided for detached execution.",
                    exit_status=1,
                    metadata={},
                )
            }

        # Handle working directory
        if self.args and getattr(self.args, "working_directory", None):
            final_cmd = f"cd {self.args.working_directory} && {final_cmd}"

        # 1. Handle Environment Variables Persistence
        if self.args and getattr(self.args, "environment", None):
            final_cmd = self._apply_env_to_command(final_cmd, self.args.environment)

        # 2. Handle Sudo if requested
        # We put the final commands and cleanup inside a single script payload
        # This ensures the shell replacement via exec maintains sequential execution
        inner_script = (
            f"{final_cmd}\nRET=$?\necho $RET > {pid_file}.exit\ndate +%s >> {age_file}\nexit $RET"
        )
        safe_cmd = shlex.quote(inner_script)

        # We exec the customized bash. The PID will remain the same as the nohup setsid launcher.
        wrapped_cmd = f"exec -a {proc_name} bash -c {safe_cmd}"

        # 3. Construct the background launch wrapper
        # Inject the task_id and command into meta_file
        cmd_meta_safe = shlex.quote(cmd)

        # Max log size 1GB, keep last 700MB
        log_max = 1073741824
        log_keep = 734003200

        # Watcher loop that runs in the background and rotates the file
        watcher_script = (
            f"while kill -0 $MAIN_PID 2>/dev/null; do "
            f"sleep 60; "
            f"size=$(stat -c%s {output_file} 2>/dev/null || echo 0); "
            f"if [ $size -gt {log_max} ]; then "
            f"tail -c {log_keep} {output_file} > {output_file}.tmp 2>/dev/null "
            f"&& cp -f {output_file}.tmp {output_file} 2>/dev/null; "
            f"fi; "
            f"done"
        )

        bg_launch = (
            f"echo {int(time.time())} > {age_file}; "
            f"nohup setsid bash -c {shlex.quote(wrapped_cmd)} "
            f"</dev/null >> {output_file} 2>&1 & "
            f"MAIN_PID=$!; "
            f"echo $MAIN_PID > {pid_file}; "
            f"echo {task_id} > {meta_file}; "
            f"echo {cmd_meta_safe} >> {meta_file}; "
            f"( {watcher_script} ) &"
        )

        # Apply sudo wrapping
        if self.args and getattr(self.args, "sudo", False):
            sudo_prefix = "sudo -S "
            bg_launch = f"{sudo_prefix}bash -c {shlex.quote(bg_launch)}"

        start_time = time.perf_counter()
        _stdin, stdout, _stderr = session.exec_command(
            bg_launch, get_pty=bool(getattr(self.args, "sudo", False))
        )

        if (
            self.args
            and getattr(self.args, "sudo", False)
            and getattr(self.args, "sudo_password", None)
        ):
            _stdin.write(f"{self.args.sudo_password}\n")
            _stdin.flush()

        exit_status = stdout.channel.recv_exit_status()

        # Read PID from file
        pid = None
        if exit_status == 0:
            pid_out = self._read_remote_file(session, pid_file)
            if pid_out and pid_out.isdigit():
                pid = int(pid_out)

        # Wait a brief moment to catch immediate failures (command not found, syntax errors, etc.)
        time.sleep(0.5)

        running = False
        if pid:
            running, _ = self._is_task_running(session, task_id)

        metadata = self._get_base_metadata(start_time)
        metadata.update(
            {
                "task_id": task_id,
                "pid": pid,
                "log_file": output_file,
                "pid_file": pid_file,
                "meta_file": meta_file,
                "age_file": age_file,
                "command": cmd,
                "is_running": running,
                "created_at": time.time(),
            }
        )

        output = f"Task {task_id} launched."
        error = ""
        final_exit = exit_status

        if exit_status == 0 and pid and not running:
            # Task exited rapidly (either failed or completed super fast)
            log_output = self._read_remote_file(session, output_file) or ""
            exit_code_str = self._read_remote_file(session, f"{pid_file}.exit")
            final_exit = int(exit_code_str) if exit_code_str and exit_code_str.isdigit() else 1
            output = log_output.strip() or f"Task {task_id} exited rapidly."
            error = log_output.strip() if final_exit != 0 else ""

        return [
            DriverExecutionResult(
                command="launch",
                output=output,
                error=error,
                exit_status=final_exit,
                metadata=metadata,
            )
        ]

    def _read_logs(
        self, session: paramiko.SSHClient, task_id: str, offset: int = 0
    ) -> list[DriverExecutionResult]:
        """Read log delta from the remote log file."""
        detached_dir = self._get_detached_dir()
        log_f = f"{detached_dir}/{DETACHED_TASK_FILE_PREFIX}_{task_id}.log"

        # Check if process is still running
        running, pid = self._is_task_running(session, task_id)

        # Get current file size first to detect rotations
        size_c = f"stat -c%s {log_f} 2>/dev/null || echo 0"
        size_res = self._execute_command(session, size_c, None)
        file_size = int(size_res.output.strip() or 0)

        # If the file shrank, a rotation happened, reset offset to read the new rotated block.
        if offset > file_size:
            offset = 0

        # Read with tail from offset (more efficient than dd bs=1 for large files)
        # tail -c +N starts at byte N (one-indexed)
        read_c = f"tail -c +{offset + 1} {log_f} 2>/dev/null" if offset > 0 else f"cat {log_f}"
        exec_res = self._execute_command(session, read_c, None)
        output = exec_res.output

        # After reading, fetch the ultimate size to use as the next offset marker
        size_res_after = self._execute_command(session, size_c, None)
        file_size_after = int(size_res_after.output.strip() or 0)

        return [
            DriverExecutionResult(
                command="query",
                output=output,
                error="",
                exit_status=0,
                metadata={
                    "task_id": task_id,
                    "is_running": running,
                    "pid": pid,
                    "next_offset": file_size_after,
                    "completed": not running,
                },
            )
        ]

    def kill_task(self, session: paramiko.SSHClient, task_id: str) -> list[DriverExecutionResult]:
        """Kill the detached task and cleanup files."""
        running, pid = self._is_task_running(session, task_id)

        start_time = time.perf_counter()
        if running and pid:
            # Task runs under setsid, so we can kill the entire process group
            # Group ID is the same as the PID of the session leader (which is our main bash wrapper)
            kill_c = (
                f"kill -15 -{pid} 2>/dev/null || kill -15 {pid} 2>/dev/null; "
                f"sleep 0.2; "
                f"kill -9 -{pid} 2>/dev/null || kill -9 {pid} 2>/dev/null"
            )
            self._execute_command(session, kill_c, None)

        # Cleanup files
        detached_dir = self._get_detached_dir()
        prefix = f"{DETACHED_TASK_FILE_PREFIX}_{task_id}"
        # We also cleanup potential script files (.sh)
        cleanup_c = (
            f"rm -f {detached_dir}/{prefix}.log {detached_dir}/{prefix}.pid* "
            f"{detached_dir}/{prefix}.sh 2>/dev/null"
        )
        self._execute_command(session, cleanup_c, None)

        return [
            DriverExecutionResult(
                command="kill",
                output=f"Task {task_id} killed and cleaned up.",
                error="",
                exit_status=0,
                metadata=self._get_base_metadata(start_time),
            )
        ]

    def _is_task_running(
        self, session: paramiko.SSHClient, task_id: str
    ) -> Tuple[bool, Optional[int]]:
        """Verify process status using PID and command identity."""
        detached_dir = self._get_detached_dir()
        pid_f = f"{detached_dir}/{DETACHED_TASK_FILE_PREFIX}_{task_id}.pid"
        pid_out = self._read_remote_file(session, pid_f)
        if not pid_out or not pid_out.isdigit():
            return False, None

        pid = int(pid_out)
        proc_name = f"{DETACHED_TASK_PROCESS_PREFIX}{task_id}"
        check_c = f"ps -p {pid} -o args= 2>/dev/null"
        check_res = self._execute_command(session, check_c, None)
        comm = check_res.output.strip()

        # PID matches and the command line contains our injected process name
        return (proc_name in comm, pid)

    def _read_remote_file(self, session: paramiko.SSHClient, path: str) -> Optional[str]:
        """Helper to read a small remote file."""
        cmd = f"cat {path} 2>/dev/null"
        _stdin, stdout, _stderr = session.exec_command(cmd)
        return stdout.read().decode().strip() or None

    def _apply_env_to_command(self, command: str, env: Optional[Dict[str, str]]) -> str:
        """Helper to prepend environment variables to a command string"""
        if not env:
            return command
        # Build export commands
        env_exports = [f"export {k}='{v}'" for k, v in env.items()]
        return f"{' && '.join(env_exports)} && {command}"

    def _handle_file_transfer(
        self, session: paramiko.SSHClient, file_transfer_op, skip_exec: bool = False
    ) -> dict:
        if not isinstance(file_transfer_op, FileTransferModel):
            file_transfer_op = FileTransferModel.model_validate(file_transfer_op)

        try:
            import time

            start_time = time.perf_counter()
            if file_transfer_op.operation == "upload":
                # Use staged file path if available
                effective_local_path = self._get_effective_source_path(file_transfer_op.local_path)
                if not effective_local_path:
                    raise ValueError("No local path or staged file provided for upload.")

                result = self._upload_file(
                    session,
                    effective_local_path,
                    file_transfer_op.remote_path,
                    file_transfer_op.resume,
                    file_transfer_op.recursive,
                    file_transfer_op.sync_mode,
                    file_transfer_op.chunk_size,
                    file_transfer_op.chmod,
                )
            elif file_transfer_op.operation == "download":
                effective_local_path = self._get_effective_dest_path(
                    file_transfer_op.local_path, os.path.basename(file_transfer_op.remote_path)
                )
                result = self._download_file(
                    session,
                    file_transfer_op.remote_path,
                    effective_local_path,
                    resume=file_transfer_op.resume,
                    recursive=file_transfer_op.recursive,
                    sync_mode=file_transfer_op.sync_mode,
                    chunk_size=file_transfer_op.chunk_size,
                )
            else:
                raise ValueError(f"Unsupported operation: {file_transfer_op.operation}")

            bytes_used = result.get("transferred_bytes", 0)
            total_bytes = result.get("total_bytes", 0)

            op_key = f"{file_transfer_op.operation} {file_transfer_op.remote_path}"
            transfer_metadata = self._get_base_metadata(start_time)
            transfer_metadata.update(
                {
                    "transferred_bytes": bytes_used,
                    "total_bytes": total_bytes,
                    "transfer_success": bool(result.get("success")),
                    "md5_verified": bool(
                        result.get("success") and file_transfer_op.sync_mode == "hash"
                    ),
                    "local_path": result.get("local_path"),
                    "remote_path": result.get("remote_path"),
                }
            )
            transfer_result = [
                DriverExecutionResult(
                    command=op_key,
                    output=f"File transfer completed: {bytes_used}/{total_bytes} bytes",
                    error="",
                    exit_status=0 if result.get("success") else 1,
                    metadata=transfer_metadata,
                )
            ]

            # Execute command after upload if requested
            if (
                not skip_exec
                and file_transfer_op.operation == "upload"
                and file_transfer_op.execute_after_upload
                and file_transfer_op.execute_command
            ):
                cmd_after = file_transfer_op.execute_command

                log.debug(f"Executing command after upload: {cmd_after}")
                exec_result = self._execute_command(session, cmd_after, self.args)
                transfer_result.append(exec_result)

                # Cleanup remote file if requested
                if file_transfer_op.cleanup_after_exec:
                    log.debug(f"Cleaning up remote file: {file_transfer_op.remote_path}")
                    cleanup_result = self._execute_command(
                        session, f"rm -f {file_transfer_op.remote_path}", self.args
                    )
                    transfer_result.append(cleanup_result)

            return transfer_result
        except Exception as e:
            log.error(f"Error in file transfer: {e}")
            return [
                DriverExecutionResult(
                    command=f"file_transfer_{file_transfer_op.operation}",
                    output="",
                    error=str(e),
                    exit_status=1,
                    metadata={},
                )
            ]

    def config(self, session: paramiko.SSHClient, config: list[str]) -> list[DriverExecutionResult]:
        """Execute configuration lines and return unified rich result"""
        if self.args and isinstance(self.args, ParamikoSendConfigArgs) and self.args.sudo:
            if not self.args.sudo_password and self.conn_args.password:
                self.args.sudo_password = self.conn_args.password

        # Handle File Transfer (Config path redirect)
        if self.args and getattr(self.args, "file_transfer", None):
            log.info(f"File transfer (via config) detected: {self.args.file_transfer.operation}")
            return self._handle_file_transfer(session, self.args.file_transfer, skip_exec=False)

        if not config:
            log.warning("No configuration provided")
            return []

        config_start_time = time.perf_counter()
        try:
            full_output = []
            full_error = []
            total_duration = 0.0
            overall_exit_status = 0

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
                _stdin, stdout, stderr = session.exec_command(cmd, **exec_kwargs)

                if (
                    self.args
                    and isinstance(self.args, ParamikoSendConfigArgs)
                    and self.args.sudo
                    and self.args.sudo_password
                ):
                    _stdin.write(f"{self.args.sudo_password}\n")
                    _stdin.flush()

                out_chunk = stdout.read().decode("utf-8", errors="replace")
                err_chunk = stderr.read().decode("utf-8", errors="replace")
                exit_status = stdout.channel.recv_exit_status()
                duration = time.perf_counter() - start_time
                total_duration += duration

                # Clean sudo output
                if (
                    self.args
                    and isinstance(self.args, ParamikoSendConfigArgs)
                    and self.args.sudo
                    and self.args.sudo_password
                ):
                    out_chunk = self._clean_sudo_output(out_chunk, self.args.sudo_password)

                full_output.append(out_chunk)
                if err_chunk:
                    full_error.append(err_chunk)

                if exit_status != 0:
                    overall_exit_status = exit_status
                    # Fail-fast: Stop if stop_on_error is true (default)
                    if self.args and getattr(self.args, "stop_on_error", True):
                        log.warning(f"Config aborted at line due to error: {cfg_line}")
                        break

            metadata = self._get_base_metadata(config_start_time)
            return [
                DriverExecutionResult(
                    command="\n".join(config),
                    output="\n".join(full_output),
                    error="\n".join(full_error),
                    exit_status=overall_exit_status,
                    metadata=metadata,
                )
            ]
        except Exception as e:
            log.error(f"Error in sending config: {e}")
            return [
                DriverExecutionResult(
                    command="\n".join(config) if config else "error",
                    output="",
                    error=str(e),
                    exit_status=1,
                    metadata=self._get_base_metadata(config_start_time),
                )
            ]

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
    ) -> DriverExecutionResult:
        """Execute a single command and return result with metadata"""

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

        duration_metadata = self._get_base_metadata(start_time)

        return DriverExecutionResult(
            command=cmd,
            output=output,
            error=error,
            exit_status=exit_status,
            metadata=duration_metadata,
        )

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
    ) -> list[DriverExecutionResult]:
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
        return [
            DriverExecutionResult(
                command=f"script_execution_{interpreter}",
                output=output,
                error=error,
                exit_status=exit_status,
                metadata={
                    "duration_seconds": round(duration, 3),
                    "script_content_length": len(args.script_content),
                },
            )
        ]

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

    def _cleanup_expired_tasks(self, session: paramiko.SSHClient, retention_seconds: int = 86400):
        """
        Clean up expired detached task files on the remote host.
        A task is considered expired if it has finished and the retention period has passed.
        """
        try:
            detached_dir = self._get_detached_dir()
            cleanup_cmd = (
                f"now=$(date +%s); "
                f"if [ -d {detached_dir} ]; then "
                f"  for f in {detached_dir}/{DETACHED_TASK_FILE_PREFIX}_*.pid.age; do "
                f'    if [ -f \\"$f\\" ]; then '
                f'      line_count=$(wc -l < \\"$f\\"); '
                f'      if [ \\"$line_count\\" -ge 2 ]; then '
                f'        end_time=$(tail -n 1 \\"$f\\"); '
                f"        if [ $((now - end_time)) -gt {retention_seconds} ]; then "
                f'          base=\\"${{f%.pid.age}}\\"; '
                f'          rm -f \\"$base\\".log \\"$base\\".pid \\"$base\\".pid.*; '
                f"        fi; "
                f"      fi; "
                f"    fi; "
                f"  done; "
                f"fi"
            )
            session.exec_command(cleanup_cmd, timeout=5)
        except Exception as e:
            log.warning(f"Failed to cleanup expired detached tasks: {e}")

    def _list_active_tasks(self, session: paramiko.SSHClient) -> List[Dict[str, Any]]:
        """List active detached tasks on remote host."""
        tasks = []
        detached_dir = self._get_detached_dir()
        try:
            ls_cmd = f"ls {detached_dir}/{DETACHED_TASK_FILE_PREFIX}_*.pid.meta 2>/dev/null"
            meta_files = self._execute_command(session, ls_cmd, None).output.strip().split()

            for meta_f in meta_files:
                try:
                    cmd_m = f"cat {meta_f}"
                    meta_res = self._execute_command(session, cmd_m, None)
                    meta_out = meta_res.output.strip().splitlines()
                    if not meta_out:
                        continue

                    task_id = meta_out[0].strip()
                    task_cmd = meta_out[1].strip() if len(meta_out) > 1 else ""

                    pid_f = meta_f.replace(".meta", "")
                    cmd_p = f"cat {pid_f}"
                    pid_out = self._execute_command(session, cmd_p, None).output.strip()

                    if not pid_out.isdigit():
                        continue

                    pid = int(pid_out)
                    ps_cmd = f"ps -p {pid} -o args= --no-headers 2>/dev/null"
                    comm = self._execute_command(session, ps_cmd, None).output.strip()

                    if f"{DETACHED_TASK_PROCESS_PREFIX}{task_id}" in comm:
                        tasks.append(
                            {
                                "task_id": task_id,
                                "command": task_cmd,
                                "pid": pid,
                                "status": "running",
                                "pid_file": pid_f,
                                "meta_file": meta_f,
                                "log_file": pid_f.replace(".pid", ".log"),
                                "age_file": f"{pid_f}.age",
                            }
                        )
                except Exception:
                    continue
        except Exception as e:
            log.warning(f"Error listing active detached tasks: {e}")

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
                                total_bytes += res.get("transferred_bytes", 0)
                                if res.get("skipped"):
                                    files_skipped += 1
                                else:
                                    files_transferred += 1

                    return {
                        "success": True,
                        "local_path": local_path,
                        "remote_path": remote_path,
                        "transferred_bytes": total_bytes,
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
                            "transferred_bytes": 0,
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
                            "transferred_bytes": local_size,
                            "total_bytes": local_size,
                            "resumed": False,
                        }

                with open(local_path, "rb") as local_file:
                    if resume and remote_size > 0:
                        local_file.seek(remote_size)

                    mode = "ab" if (resume and remote_size > 0) else "wb"
                    remote_file = sftp.file(remote_path, mode)

                    try:
                        transferred_bytes = remote_size
                        while True:
                            chunk = local_file.read(chunk_size)
                            if not chunk:
                                break
                            remote_file.write(chunk)
                            transferred_bytes += len(chunk)

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
                            "transferred_bytes": transferred_bytes,
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
                                total_bytes += res.get("transferred_bytes", 0)
                                if res.get("skipped"):
                                    files_skipped += 1
                                else:
                                    files_transferred += 1

                        return {
                            "success": True,
                            "local_path": local_path,
                            "remote_path": remote_path,
                            "transferred_bytes": total_bytes,
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
                            "transferred_bytes": 0,
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
                            "transferred_bytes": remote_size,
                            "total_bytes": remote_size,
                            "resumed": False,
                        }

                remote_file = sftp.file(remote_path, "rb")
                if resume and local_size > 0:
                    remote_file.seek(local_size)

                mode = "ab" if (resume and local_size > 0) else "wb"
                with open(local_path, mode) as local_file:
                    transferred_bytes = local_size
                    try:
                        while True:
                            chunk = remote_file.read(chunk_size)
                            if not chunk:
                                break
                            local_file.write(chunk)
                            transferred_bytes += len(chunk)

                        remote_file.close()

                        return {
                            "success": True,
                            "local_path": local_path,
                            "remote_path": remote_path,
                            "transferred_bytes": transferred_bytes,
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
