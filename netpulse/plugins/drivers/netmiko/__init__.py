import logging
import os
import signal
import sys
import threading
from typing import Any, Optional

from netmiko import BaseConnection, ConnectHandler

from ....models.driver import DriverExecutionResult
from .. import BaseDriver
from .model import (
    NetmikoConnectionArgs,
    NetmikoDeviceTestInfo,
    NetmikoExecutionRequest,
    NetmikoSendCommandArgs,
)

log = logging.getLogger(__name__)


class NetmikoDriver(BaseDriver):
    """
    This driver has persistent connection support and monitor mechanism.
    But it is not concurrency safe. Only use it with rq.SimpleWorker.
    """

    driver_name = "netmiko"

    persisted_session: Optional[BaseConnection] = None
    persisted_conn_args: Optional[NetmikoConnectionArgs] = None

    _monitor_stop_event = None
    _monitor_thread = None
    _monitor_lock = threading.Lock()

    @classmethod
    def _get_persisted_session(cls, conn_args: NetmikoConnectionArgs) -> Optional[BaseConnection]:
        """
        Check if persisted session is still alive, otherwise disconnect it.
        """
        if cls.persisted_session and cls.persisted_conn_args != conn_args:
            if cls.persisted_session:
                log.warning("New connection args detected, disconnecting old session")
                # Stop monitor thread and disconnect
                with cls._monitor_lock:
                    try:
                        cls.persisted_session.disconnect()
                    except Exception as e:
                        log.error(f"Error in disconnecting old session: {e}")
                    finally:
                        cls._set_persisted_session(None, None)

        return cls.persisted_session

    @classmethod
    def _set_persisted_session(
        cls, session: Optional[BaseConnection], conn_args: Optional[NetmikoConnectionArgs]
    ) -> Optional[BaseConnection]:
        """
        Persist session and connection args. Start monitor thread.
        Caller should ensure that the session is disconnected when done.
        """
        # Clear
        if session is None:
            assert cls.persisted_conn_args is not None
            if cls.persisted_conn_args.keepalive:
                cls._stop_monitor_thread()
            cls.persisted_session = None
            cls.persisted_conn_args = None
            return None

        # Setup
        cls.persisted_session = session
        cls.persisted_conn_args = conn_args
        cls._start_monitor_thread(cls.persisted_session)

        return cls.persisted_session

    @classmethod
    def _start_monitor_thread(cls, session: BaseConnection):
        """
        session.is_alive() will send NULL to device. We rely on this to keepalive.
        However, BaseConnection is not concurrency safe, we have to use a lock.
        """
        if cls._monitor_thread and cls._monitor_thread.is_alive():
            log.info("Monitoring thread already running")
            return

        assert cls.persisted_conn_args is not None
        cls._monitor_stop_event = threading.Event()
        host = cls.persisted_conn_args.host
        timeout = cls.persisted_conn_args.keepalive

        def monitor():
            suicide = False
            log.info(f"Monitoring thread started ({host})")
            assert cls._monitor_stop_event is not None

            while not cls._monitor_stop_event.is_set():
                if cls._monitor_stop_event.wait(timeout=timeout):
                    break

                with cls._monitor_lock:
                    # Double checking
                    if cls._monitor_stop_event.is_set():
                        break

                    # Health checking
                    if not session.is_alive():
                        log.warning(f"Connection to {host} is unhealthy")
                        suicide = True
                        cls._monitor_stop_event.set()
                        break

                    # Keepalive
                    try:
                        if junk := session.clear_buffer():
                            log.debug(f"Detected junk data in keepalive: {junk}")
                        session.write_channel(session.RETURN)
                    except Exception as e:
                        log.warning(f"Error in sending keepalive to {host}: {e}")
                        suicide = True
                        cls._monitor_stop_event.set()

            log.debug(f"Monitoring thread quitting with `suicide={suicide}`.")

            # When connection is disconnected, the worker should suicide.
            if suicide:
                log.info(f"Pinned worker for {host} suicides. ")
                os.kill(os.getpid(), signal.SIGTERM)

            # This only exits from current thread
            sys.exit(0)

        cls._monitor_thread = threading.Thread(target=monitor, daemon=True)
        cls._monitor_thread.start()

    @classmethod
    def _stop_monitor_thread(cls):
        """Stop the monitor thread."""
        if cls._monitor_stop_event:
            cls._monitor_stop_event.set()
        if cls._monitor_thread and cls._monitor_thread.is_alive():
            cls._monitor_thread.join()
        cls._monitor_thread = None
        cls._monitor_stop_event = None

    @classmethod
    def from_execution_request(cls, req: NetmikoExecutionRequest):
        if not isinstance(req, NetmikoExecutionRequest):
            req = NetmikoExecutionRequest.model_validate(req.model_dump())
        return cls(
            args=req.driver_args,
            conn_args=req.connection_args,
            enabled=req.enable_mode,
            save=req.save,
            staged_file_id=req.staged_file_id,
            job_id=getattr(req, "id", None),
            file_transfer=req.file_transfer,
        )

    @classmethod
    def validate(cls, req: NetmikoExecutionRequest) -> None:
        """
        Validate the request without creating the driver instance.

        Raises:
            pydantic.ValidationError: If the request model validation fails
                (e.g., missing required fields, invalid field types).
        """
        # Validate the request model using Pydantic
        if not isinstance(req, NetmikoExecutionRequest):
            NetmikoExecutionRequest.model_validate(req.model_dump())

    def __init__(
        self,
        args: Optional[Any],
        conn_args: NetmikoConnectionArgs,
        enabled: bool = False,
        save: bool = True,
        staged_file_id: Optional[str] = None,
        file_transfer: Optional[Any] = None,
        **kwargs,
    ):
        super().__init__(staged_file_id=staged_file_id, **kwargs)
        self.args = args
        self.conn_args = conn_args
        self.enabled = enabled
        self.save = save
        self.file_transfer = file_transfer

    def connect(self) -> BaseConnection:
        try:
            session = self._get_persisted_session(self.conn_args)
            if session:
                log.info("Reusing existing connection")
                self._session_reused = True
            else:
                log.info(f"Creating new connection to {self.conn_args.host}...")
                session = ConnectHandler(**self.conn_args.model_dump())
                self._session_reused = False
                if self.conn_args.keepalive:
                    self._set_persisted_session(session, self.conn_args)
            return session
        except Exception as e:
            log.error(f"Error in connecting: {e}")
            raise e

    def send(self, session: BaseConnection, command: list[str]) -> list[DriverExecutionResult]:
        """Execute commands and return rich results with metadata"""
        import time

        from ....models.driver import DriverExecutionResult

        try:
            with self._monitor_lock:
                if self.enabled:
                    session.enable()

                # Handle File Transfer (Top-level first)
                if self.file_transfer:
                    log.info(f"Top-level file transfer detected: {self.file_transfer.operation}")
                    return self._handle_file_transfer(session, self.file_transfer)

                # Legacy check for nested file transfer
                if self.args and getattr(self.args, "file_transfer", None) is not None:
                    log.info("Nested file transfer detected")
                    return self._handle_file_transfer(session, self.args.file_transfer)

                result = []
                for cmd in command:
                    start_time = time.perf_counter()
                    cmd_args = {"cmd_verify": False}  # Default to False for exec mode
                    if self.args:
                        if isinstance(self.args, NetmikoSendCommandArgs):
                            user_args = self.args.model_dump()
                            # If user didn't explicitly set cmd_verify, we use our default False
                            if "cmd_verify" not in user_args or self.args.cmd_verify is True:
                                user_args["cmd_verify"] = False
                            response = session.send_command(cmd, **user_args)
                        else:
                            # Filter parameters for send_command
                            for attr in [
                                "read_timeout",
                                "delay_factor",
                                "max_loops",
                                "strip_prompt",
                                "strip_command",
                            ]:
                                if hasattr(self.args, attr):
                                    val = getattr(self.args, attr)
                                    if val is not None:
                                        cmd_args[attr] = val
                            response = session.send_command(cmd, **cmd_args)
                    else:
                        response = session.send_command(cmd, **cmd_args)

                    duration_metadata = self._get_base_metadata(start_time)
                    result.append(
                        DriverExecutionResult(
                            command=cmd,
                            stdout=response,
                            stderr="",
                            exit_status=0,
                            metadata=duration_metadata,
                        )
                    )
                if self.enabled:
                    session.exit_enable_mode()

            return result
        except Exception as e:
            log.error(f"Error in sending command: {e}")
            return [
                DriverExecutionResult(
                    command=" ".join(command),
                    stdout="",
                    stderr=str(e),
                    exit_status=1,
                    metadata=self._get_base_metadata(start_time),
                )
            ]

    def config(self, session: BaseConnection, config: list[str]) -> list[DriverExecutionResult]:
        """Execute configuration set and return a list of granular results"""
        import time

        from ....models.driver import DriverExecutionResult

        try:
            with self._monitor_lock:
                start_time = time.perf_counter()

                # Proactive insurance: Clear any stale hostname/prompt from session persistence
                session.set_base_prompt()

                if self.enabled:
                    session.enable()

                # Handle File Transfer (Config mode redirect)
                if self.args and getattr(self.args, "file_transfer", None) is not None:
                    log.info("File transfer (via config) detected")
                    return self._handle_file_transfer(session, self.args.file_transfer)

                # Prepare config arguments
                config_args = {}
                if self.args:
                    attrs = [
                        "read_timeout",
                        "delay_factor",
                        "max_loops",
                        "strip_prompt",
                        "strip_command",
                        "cmd_verify",
                        "error_pattern",
                        "config_mode_command",
                    ]
                    for attr in attrs:
                        if hasattr(self.args, attr):
                            val = getattr(self.args, attr)
                            if val is not None and val != "":
                                config_args[attr] = val

                # 1. Enter config mode once
                config_cmd = config_args.get("config_mode_command")
                if config_cmd:
                    session.config_mode(config_cmd)
                else:
                    session.config_mode()

                results = []
                # 2. Execute commands one by one for granular reporting
                import re

                # Base error patterns for CLI validation
                ERROR_PATTERNS = [
                    (
                        r"% (Unrecognized command|Wrong parameter|Incomplete command|"
                        r"Invalid input|Ambiguous command)"
                    ),
                    r"\^",  # Pointer to error position
                    r"Invalid input detected",
                    r"Error:",
                ]

                for i, cmd in enumerate(config):
                    line_start = time.perf_counter()
                    try:
                        # Use the original config_args without manual delay_factor overrides
                        response = session.send_config_set(
                            [cmd], enter_config_mode=False, exit_config_mode=False, **config_args
                        )

                        exit_status = 0
                        error_msg = ""
                        output_str = response if response is not None else ""

                        # Validate output for device-side errors
                        check_patterns = ERROR_PATTERNS
                        if "error_pattern" in config_args:
                            check_patterns = [config_args["error_pattern"]]

                        for pattern in check_patterns:
                            if re.search(pattern, output_str, re.IGNORECASE):
                                exit_status = 1
                                last_line = (
                                    output_str.strip().splitlines()[-1]
                                    if output_str.strip()
                                    else "Error detected"
                                )
                                error_msg = f"Device reported configuration error: {last_line}"
                                break

                        results.append(
                            DriverExecutionResult(
                                command=cmd,
                                stdout=output_str,
                                stderr=error_msg,
                                exit_status=exit_status,
                                metadata=self._get_base_metadata(line_start),
                            )
                        )

                        # Atomic: stop if a line failed validation
                        if exit_status != 0:
                            # Correctly fill in ALL remaining commands as "Skipped"
                            for skipped_cmd in config[i + 1 :]:
                                results.append(
                                    DriverExecutionResult(
                                        command=skipped_cmd,
                                        stdout="",
                                        stderr=(
                                            f"Skipped due to previous error in execution of '{cmd}'"
                                        ),
                                        exit_status=1,
                                        metadata=self._get_base_metadata(time.perf_counter()),
                                    )
                                )
                            break

                    except Exception as e:
                        log.warning(f"Exception executing config line '{cmd}': {e}")
                        results.append(
                            DriverExecutionResult(
                                command=cmd,
                                stdout="",
                                stderr=str(e),
                                exit_status=1,
                                metadata=self._get_base_metadata(line_start),
                            )
                        )
                        # Also fill in skipped for exceptions
                        for skipped_cmd in config[i + 1 :]:
                            results.append(
                                DriverExecutionResult(
                                    command=skipped_cmd,
                                    stdout="",
                                    stderr=(f"Skipped due to exception in execution of '{cmd}'"),
                                    exit_status=1,
                                    metadata=self._get_base_metadata(time.perf_counter()),
                                )
                            )
                        break
                    finally:
                        # Maintain prompt synchronization to handle sub-view changes
                        session.set_base_prompt()

                # 3. Post-execution operations (Commit/Save)
                if commit := self._commit(session):
                    if results:
                        results[-1].stdout += f"\n{commit}"

                if self.save:
                    session.set_base_prompt()
                    save_res = session.save_config()
                    if results and save_res:
                        results[-1].stdout += f"\n{save_res}"

                # 4. Exit config mode once
                session.exit_config_mode()
                if self.enabled:
                    session.exit_enable_mode()

                return results
        except Exception as e:
            log.error(f"Error in sending config: {e}")
            return [
                DriverExecutionResult(
                    command="\n".join(config),
                    stdout="",
                    stderr=str(e),
                    exit_status=1,
                    metadata=self._get_base_metadata(start_time),
                )
            ]

    def _commit(self, session: BaseConnection) -> Optional[str]:
        """
        Commit the configuration.
        This should be called after sending the configuration.

        NOTE: Caller should own the lock!
        NOTE: Some devices may not support commit. In this case, the running-config
        is already updated.
        """
        result = None
        try:
            result = session.commit()
        except (NotImplementedError, AttributeError):
            pass
        return result

    def _handle_file_transfer(
        self, session: BaseConnection, file_transfer_op: Any
    ) -> list[DriverExecutionResult]:
        """
        Handle file transfer using Netmiko's file_transfer function.
        """
        from netmiko import file_transfer

        from ....models.driver import DriverExecutionResult

        try:
            import time

            start_time = time.perf_counter()
            if file_transfer_op.operation == "upload":
                effective_local_path = self._get_effective_source_path(file_transfer_op.local_path)
                if not effective_local_path:
                    raise ValueError("No local path or staged file provided for upload.")
                source_file = effective_local_path
                dest_file = file_transfer_op.remote_path
                direction = "put"
            else:  # download
                effective_local_path = self._get_effective_dest_path(
                    file_transfer_op.local_path, os.path.basename(file_transfer_op.remote_path)
                )
                source_file = file_transfer_op.remote_path
                dest_file = effective_local_path
                direction = "get"

            # Netmiko file_transfer arguments
            transfer_args = {
                "ssh_conn": session,
                "source_file": source_file,
                "dest_file": dest_file,
                "direction": direction,
                "overwrite_file": file_transfer_op.overwrite,
            }

            results = file_transfer(**transfer_args)

            op_name = f"{file_transfer_op.operation} {file_transfer_op.remote_path}"
            transfer_metadata = self._get_base_metadata(start_time)
            transfer_metadata.update(
                {
                    "transferred_bytes": results.get("file_size", 0),
                    "transfer_success": bool(results.get("file_exists")),
                    "md5_verified": bool(results.get("file_verified")),
                    "local_path": dest_file if direction == "get" else source_file,
                    "remote_path": source_file if direction == "get" else dest_file,
                }
            )
            return [
                DriverExecutionResult(
                    command=op_name,
                    stdout=f"File transfer results: {results}",
                    stderr="",
                    exit_status=0 if results.get("file_exists") else 1,
                    metadata=transfer_metadata,
                )
            ]
        except Exception as e:
            log.error(f"Error in Netmiko file transfer: {e}")
            return [
                DriverExecutionResult(
                    command="file_transfer",
                    stdout="",
                    stderr=str(e),
                    exit_status=1,
                    metadata={"duration_seconds": 0.0},
                )
            ]

    def disconnect(self, session: BaseConnection, reset=False):
        """
        Disconnect the session and stop monitor thread.
        """
        # We only disconnect if reset is True, so that we can reuse the connection
        if not reset:
            return

        with self._monitor_lock:
            try:
                # Stop monitor thread and disconnect
                session.disconnect()
            except Exception as e:
                log.error(f"Error in disconnecting (reset): {e}")
                raise e
            finally:
                self._set_persisted_session(None, self.conn_args)

    @classmethod
    def test(cls, connection_args: NetmikoConnectionArgs) -> NetmikoDeviceTestInfo:
        conn_args = (
            connection_args
            if isinstance(connection_args, NetmikoConnectionArgs)
            else NetmikoConnectionArgs.model_validate(connection_args.model_dump(exclude_none=True))
        )

        connection = None
        try:
            test_args = conn_args.model_dump(exclude_none=True)
            connection = ConnectHandler(**test_args)
            prompt = connection.find_prompt()

            return NetmikoDeviceTestInfo(
                device_type=conn_args.device_type,
                host=conn_args.host,
                prompt=prompt,
            )
        finally:
            if connection:
                try:
                    connection.disconnect()
                except Exception:
                    log.warning("Error in disconnecting test connection", exc_info=True)


__all__ = ["NetmikoDriver"]
