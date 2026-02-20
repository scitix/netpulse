import logging
import os
import signal
import sys
import threading
from typing import TYPE_CHECKING, Dict, Optional

if TYPE_CHECKING:
    from ....models.driver import DriverExecutionResult

from netmiko import BaseConnection, ConnectHandler

from .. import BaseDriver
from .model import (
    NetmikoConnectionArgs,
    NetmikoDeviceTestInfo,
    NetmikoExecutionRequest,
    NetmikoSendCommandArgs,
    NetmikoSendConfigSetArgs,
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
            req = NetmikoExecutionRequest.model_validate(obj=req.model_dump())
        return cls(
            args=req.driver_args,
            conn_args=req.connection_args,
            enabled=req.enable_mode,
            save=req.save,
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
            NetmikoExecutionRequest.model_validate(obj=req.model_dump())

    def __init__(
        self,
        args: NetmikoSendCommandArgs | NetmikoSendConfigSetArgs | None,
        conn_args: NetmikoConnectionArgs,
        enabled: bool = False,
        save: bool = True,
        **kwargs,
    ):
        self.args = args
        self.conn_args = conn_args
        self.enabled = enabled
        self.save = save

    def connect(self) -> BaseConnection:
        try:
            session = self._get_persisted_session(self.conn_args)
            if session:
                log.info("Reusing existing connection")
            else:
                log.info(f"Creating new connection to {self.conn_args.host}...")
                session = ConnectHandler(**self.conn_args.model_dump())
                if self.conn_args.keepalive:
                    self._set_persisted_session(session, self.conn_args)
            return session
        except Exception as e:
            log.error(f"Error in connecting: {e}")
            raise e

    def send(
        self, session: BaseConnection, command: list[str]
    ) -> "Dict[str, DriverExecutionResult]":
        """Execute commands and return rich results with telemetry"""
        import time

        from ....models.driver import DriverExecutionResult

        try:
            with self._monitor_lock:
                if self.enabled:
                    session.enable()

                result = {}
                for cmd in command:
                    start_time = time.perf_counter()
                    if self.args:
                        if isinstance(self.args, NetmikoSendCommandArgs):
                            response = session.send_command(cmd, **self.args.model_dump())
                        else:
                            # Filter parameters for send_command
                            cmd_args = {}
                            for attr in [
                                "read_timeout",
                                "delay_factor",
                                "max_loops",
                                "strip_prompt",
                                "strip_command",
                                "cmd_verify",
                            ]:
                                if hasattr(self.args, attr):
                                    val = getattr(self.args, attr)
                                    if val is not None:
                                        cmd_args[attr] = val
                            response = session.send_command(cmd, **cmd_args)
                    else:
                        response = session.send_command(cmd)

                    duration = time.perf_counter() - start_time
                    result[cmd] = DriverExecutionResult(
                        output=response,
                        error="",
                        exit_status=0,
                        telemetry={"duration_seconds": round(duration, 3)},
                    )
                if self.enabled:
                    session.exit_enable_mode()

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

    def config(
        self, session: BaseConnection, config: list[str]
    ) -> "Dict[str, DriverExecutionResult]":
        """Execute configuration set and return unified rich result"""
        import time

        from ....models.driver import DriverExecutionResult

        try:
            with self._monitor_lock:
                start_time = time.perf_counter()
                if self.enabled:
                    session.enable()

                if self.args:
                    if isinstance(self.args, NetmikoSendConfigSetArgs):
                        response = session.send_config_set(config, **self.args.model_dump())
                    else:
                        # Filter parameters for send_config_set
                        config_args = {}
                        for attr in [
                            "read_timeout",
                            "delay_factor",
                            "max_loops",
                            "strip_prompt",
                            "strip_command",
                            "cmd_verify",
                        ]:
                            if hasattr(self.args, attr):
                                val = getattr(self.args, attr)
                                if val is not None:
                                    config_args[attr] = val
                        response = session.send_config_set(config, **config_args)
                else:
                    response = session.send_config_set(config)

                if commit := self._commit(session):
                    response += f"\n{commit}"

                if self.save:
                    session.set_base_prompt()
                    save_res = session.save_config()
                    response += f"\n{save_res}"

                if self.enabled:
                    session.exit_enable_mode()

                duration = time.perf_counter() - start_time

            # Harmonize config result as a dict mapping the full set string to result
            # This allows rpc.py parsing to work the same way as send.
            config_key = "\n".join(config)
            return {
                config_key: DriverExecutionResult(
                    output=response,
                    error="",
                    exit_status=0,
                    telemetry={"duration_seconds": round(duration, 3)},
                )
            }
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
