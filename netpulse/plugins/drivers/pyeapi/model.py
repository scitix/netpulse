from typing import Optional

from pydantic import ConfigDict, Field

from ....models import DriverArgs, DriverConnectionArgs
from ....models.request import PullingRequest, PushingRequest


class PyeapiConnectionArg(DriverConnectionArgs):
    """
    Arguments for Pyeapi connect.
    See pyeapi.connect for more details.
    """

    transport: Optional[str] = None
    host: str = Field("localhost", description="The hostname or IP address of the device.")
    username: str = Field("admin", description="The username to authenticate with.")
    password: str = Field("", description="The password to authenticate with.")
    port: Optional[int] = Field(None, description="Determined by the transport by default.")
    key_file: Optional[str] = None
    cert_file: Optional[str] = None
    ca_file: Optional[str] = None
    timeout: int = Field(60, description="The timeout value for the connection.")


class PyeapiArg(DriverArgs):
    """
    Extra arguments for Pyeapi driver.
    """

    model_config = ConfigDict(extra="allow")


class PyeapiPullingRequest(PullingRequest):
    connection_args: PyeapiConnectionArg
    args: Optional[PyeapiArg] = None
    enable_mode: bool = False

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "driver": "pyeapi",
                "queue_strategy": "fifo",
                "connection_args": {
                    "host": "172.17.0.1",
                    "username": "admin",
                    "password": "admin",
                    "transport": "https",
                },
                "command": ["show version", "show interfaces"],
            }
        }
    )


class PyeapiPushingRequest(PushingRequest):
    connection_args: PyeapiConnectionArg
    args: Optional[PyeapiArg] = None
    enable_mode: bool = True
    save: bool = True

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "driver": "pyeapi",
                "queue_strategy": "fifo",
                "connection_args": {
                    "host": "172.17.0.1",
                    "username": "admin",
                    "password": "admin",
                    "transport": "https",
                },
                "config": "hostname test-device",
                "save": True,
            }
        }
    )
