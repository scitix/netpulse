import logging
from typing import TYPE_CHECKING, Dict, Optional

if TYPE_CHECKING:
    from ....models.driver import DriverExecutionResult

import pyeapi

from ....models.driver import DriverExecutionResult
from .. import BaseDriver
from .model import (
    PyeapiArg,
    PyeapiConnectionArg,
    PyeapiDeviceTestInfo,
    PyeapiExecutionRequest,
)

log = logging.getLogger(__name__)


class PyeapiDriver(BaseDriver):
    driver_name: str = "pyeapi"

    @classmethod
    def from_execution_request(cls, req: PyeapiExecutionRequest) -> "PyeapiDriver":
        if not isinstance(req, PyeapiExecutionRequest):
            req = PyeapiExecutionRequest.model_validate(req.model_dump())
        return cls(
            conn_args=req.connection_args,
            enabled=req.enable_mode,
            save=req.save,
            args=req.driver_args,
            staged_file_id=req.staged_file_id,
        )

    @classmethod
    def validate(cls, req: PyeapiExecutionRequest) -> None:
        """
        Validate the request without creating the driver instance.

        Raises:
            pydantic.ValidationError: If the request model validation fails
                (e.g., missing required fields, invalid field types).
        """
        # Validate the request model using Pydantic
        if not isinstance(req, PyeapiExecutionRequest):
            PyeapiExecutionRequest.model_validate(req.model_dump())

    def __init__(
        self,
        conn_args: PyeapiConnectionArg,
        enabled: bool,
        save: bool = True,
        args: Optional[PyeapiArg] = None,
        staged_file_id: Optional[str] = None,
        **kwargs,
    ):
        """
        Init the driver with arguments.
        """
        super().__init__(staged_file_id=staged_file_id, **kwargs)
        self.conn_args = conn_args
        self.enabled = enabled
        self.save = save
        self.args = args.model_dump() if args else {}
        self.connection = None

    def connect(self):
        """
        Connect to the device and return the connection object.
        """
        try:
            self.connection = pyeapi.connect(
                return_node=True, **self.conn_args.model_dump(), **self.args
            )
        except Exception as e:
            log.error(f"Error in connecting: {e}")
            raise e
        return self.connection

    def send(
        self, session: "pyeapi.client.Node", command: list[str]
    ) -> "Dict[str, DriverExecutionResult]":
        """
        Use pyeapi.Node.enable to send out commands
        """
        import time

        session = session if session else self.connection
        try:
            if session is None:
                log.error("Connection is not established")
                raise RuntimeError("Connection is not established")

            if command is None:
                log.warning("No command provided")
                return {}

            start_time = time.perf_counter()
            # session.enable returns a list of result objects for each command
            raw_results = session.enable(commands=command, send_enable=self.enabled, **self.args)
            duration = time.perf_counter() - start_time

            result = {}
            for i, cmd in enumerate(command):
                output = raw_results[i]
                result[cmd] = DriverExecutionResult(
                    output=output,
                    error="",
                    exit_status=0,
                    telemetry={"duration_seconds": round(duration / len(command), 3)},
                )
            return result
        except Exception as e:
            log.error(f"Error in pyeapi send: {e}")
            # Determine a key for the error result. If command is None or empty, use a default.
            error_key = " ".join(command) if command else "unknown_command"
            return {
                error_key: DriverExecutionResult(
                    output="",
                    error=str(e),
                    exit_status=1,
                    telemetry={"duration_seconds": 0.0},
                )
            }

    def config(
        self, session: "pyeapi.client.Node", config: Optional[list[str]] = None
    ) -> "Dict[str, DriverExecutionResult]":
        """
        Unified config result for pyeapi.
        """
        import time

        session = session if session else self.connection
        try:
            if session is None:
                log.error("Connection is not established")
                raise RuntimeError("Connection is not established")

            if not config:
                log.warning("No config provided")
                return {}

            start_time = time.perf_counter()
            full_config = config.copy()
            if self.save:
                full_config.append("write memory")

            response = session.config(commands=full_config, **self.args)
            duration = time.perf_counter() - start_time

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
            # Determine a key for the error result. If config is None or empty, use a default.
            error_key = "\n".join(config) if config else "unknown_config"
            return {
                error_key: DriverExecutionResult(
                    output="",
                    error=str(e),
                    exit_status=1,
                    telemetry={"duration_seconds": 0.0},
                )
            }

    def disconnect(self, session):
        """
        pyeapi uses HTTP/HTTPS connection, so no need to disconnect.
        """
        pass

    @classmethod
    def test(cls, connection_args: PyeapiConnectionArg) -> PyeapiDeviceTestInfo:
        conn_args = (
            connection_args
            if isinstance(connection_args, PyeapiConnectionArg)
            else PyeapiConnectionArg.model_validate(connection_args.model_dump(exclude_none=True))
        )

        pyeapi.connect(return_node=True, **conn_args.model_dump(exclude_none=True))
        return PyeapiDeviceTestInfo(
            host=conn_args.host,
            transport=conn_args.transport or "http",
        )


__all__ = ["PyeapiDriver"]
