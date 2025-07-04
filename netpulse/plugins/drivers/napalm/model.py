from typing import Any, Optional

from pydantic import ConfigDict, Field

from ....models import (
    DriverArgs,
    DriverConnectionArgs,
    DriverName,
)
from ....models.request import PullingRequest, PushingRequest


class NapalmConnectionArgs(DriverConnectionArgs):
    device_type: str = Field(..., description="Device type in NAPALM format")
    host: str = Field(..., description="Device hostname or IP address", alias="hostname")
    timeout: Optional[int] = Field(
        None, description="Time in seconds to wait for the device to respond"
    )
    optional_args: Optional[dict[str, Any]] = Field(
        None, description="Optional arguments for NAPALM driver"
    )

    model_config = ConfigDict(populate_by_name=True)


class NapalmPullingArgs(DriverArgs):
    """
    Refer to `napalm.base.NetworkDriver.cli()` for details
    """

    encoding: Optional[str] = Field("text", description="Option `encoding` in cli() of NAPALM")
    model_config = ConfigDict(extra="allow")


class NapalmPushingArgs(DriverArgs):
    """
    Refer to `napalm.base.NetworkDriver.commit_config()` for details
    """

    message: Optional[str] = Field(
        None, description="Option `message` in commit_config() of NAPALM"
    )
    revert_in: Optional[int] = Field(
        None, description="Option `revert_in` in commit_config() of NAPALM"
    )
    model_config = ConfigDict(extra="allow")


class NapalmPullingRequest(PullingRequest):
    """
    NAPALM pulling request
    """

    driver: DriverName = "napalm"
    connection_args: NapalmConnectionArgs
    args: Optional[NapalmPullingArgs] = None
    enable_mode: Optional[bool] = False

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "driver": "napalm",
                "queue_strategy": "fifo",
                "connection_args": {
                    "device_type": "cisco_ios",
                    "host": "172.17.0.1",
                    "username": "admin",
                    "password": "admin",
                    "optional_args": {"port": 22},
                },
                "command": ["get_facts", "get_interfaces"],
            }
        }
    )


class NapalmPushingRequest(PushingRequest):
    """
    NAPALM pushing request
    """

    driver: DriverName = "napalm"
    connection_args: NapalmConnectionArgs
    args: Optional[NapalmPushingArgs] = None
    dry_run: Optional[bool] = Field(
        False,
        description="If True, the config will not be pushed to the device.",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "driver": "napalm",
                "queue_strategy": "fifo",
                "connection_args": {
                    "device_type": "cisco_ios",
                    "host": "172.17.0.1",
                    "username": "admin",
                    "password": "admin",
                },
                "config": "hostname router1\ninterface GigabitEthernet0/1\n description WAN Link",
                "dry_run": False,
            }
        }
    )
