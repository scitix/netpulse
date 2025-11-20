from typing import Any, Optional

from pydantic import ConfigDict, Field

from ....models import (
    DriverArgs,
    DriverConnectionArgs,
    DriverName,
)
from ....models.request import ExecutionRequest


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


class NapalmCliArgs(DriverArgs):
    """
    Refer to `napalm.base.NetworkDriver.cli()` for details
    """

    encoding: str = Field(default="text", description="Option `encoding` in cli() of NAPALM")
    model_config = ConfigDict(extra="allow")


class NapalmCommitConfigArgs(DriverArgs):
    """
    Refer to `napalm.base.NetworkDriver.commit_config()` for details
    """

    message: Optional[str] = Field(
        default=None, description="Option `message` in commit_config() of NAPALM"
    )
    revert_in: Optional[int] = Field(
        default=None, description="Option `revert_in` in commit_config() of NAPALM"
    )
    model_config = ConfigDict(extra="allow")


class NapalmExecutionRequest(ExecutionRequest):
    """
    NAPALM execution request
    """

    driver: DriverName = DriverName.NAPALM
    driver_args: Optional[NapalmCliArgs | NapalmCommitConfigArgs] = None
    connection_args: NapalmConnectionArgs

    enable_mode: bool = Field(True, description="Enter privileged mode for execution")
    dry_run: bool = Field(
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
