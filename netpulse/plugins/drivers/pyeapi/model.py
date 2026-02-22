from typing import Optional

from pydantic import ConfigDict, Field

from ....models import DeviceTestInfo, DriverArgs, DriverConnectionArgs, DriverName
from ....models.request import ExecutionRequest


class PyeapiConnectionArg(DriverConnectionArgs):
    """
    Arguments for Pyeapi connect.
    See pyeapi.connect for more details.
    """

    transport: Optional[str] = None
    host: str = Field(default="localhost", description="The hostname or IP address of the device.")
    username: str = Field(default="admin", description="The username to authenticate with.")
    password: str = Field(default="", description="The password to authenticate with.")
    port: Optional[int] = Field(default=None, description="Determined by the transport by default.")
    key_file: Optional[str] = None
    cert_file: Optional[str] = None
    ca_file: Optional[str] = None
    timeout: int = Field(default=60, description="The timeout value for the connection.")


class PyeapiArg(DriverArgs):
    """
    Extra arguments for Pyeapi driver.
    """

    model_config = ConfigDict(extra="allow")


class PyeapiExecutionRequest(ExecutionRequest):
    connection_args: PyeapiConnectionArg
    driver_args: Optional[PyeapiArg] = None
    enable_mode: bool = Field(True, description="Enter privileged mode for execution")
    save: bool = Field(False, description="Save configuration after execution")

    # Internal field for file transfer bridge
    staged_file_id: Optional[str] = Field(
        default=None,
        description="Internal reference to the staged file (Multipart mode)",
    )

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
                "save": False,
            }
        }
    )


class PyeapiDeviceTestInfo(DeviceTestInfo):
    driver: DriverName = DriverName.PYEAPI
    transport: Optional[str] = None
