import logging
from typing import Optional

import pyeapi

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
        **kwargs,
    ):
        """
        Init the driver with arguments.
        """
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

    def send(self, session: "pyeapi.client.Node", command: list[str]):
        """
        Use pyeapi.Node.enable to send out commands
        """

        session = session if session else self.connection
        if session is None:
            log.error("Connection is not established")
            raise RuntimeError("Connection is not established")

        if command is None:
            log.warning("No command provided")
            return {}

        try:
            result = session.enable(commands=command, send_enable=self.enabled, **self.args)
            return result
        except Exception as e:
            raise e

    def config(self, session: "pyeapi.client.Node", config: Optional[list[str]] = None):
        """
        In pyeapi, we don't need to use session.
        """
        session = session if session else self.connection
        if session is None:
            log.error("Connection is not established")
            raise RuntimeError("Connection is not established")

        if not config:
            log.warning("No config provided")
            return {}

        try:
            if self.save:
                config.append("write memory")

            result = session.config(commands=config, **self.args)
            return result
        except Exception as e:
            log.error(f"Error in sending config: {e}")
            raise e

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
