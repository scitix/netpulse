import logging
from inspect import signature

from napalm.base import NetworkDriver, get_network_driver

from .. import BaseDriver
from .model import (
    DriverConnectionArgs,
    NapalmCliArgs,
    NapalmCommitConfigArgs,
    NapalmConnectionArgs,
    NapalmExecutionRequest,
)

log = logging.getLogger(__name__)

# Netmiko device types -> NAPALM ones
# See napalm/_SUPPORTED_DRIVERS.py
NETMIKO_DEVICE_TYPE_MAP = {
    "arista_eos": "eos",
    "cisco_ios": "ios",
    "cisco_xr": "iosxr",
    "juniper": "junos",
    "nxos": "nxos",
    "cisco_nxos_ssh": "nxos_ssh",
}


class NapalmDriver(BaseDriver):
    driver_name = "napalm"

    @classmethod
    def from_execution_request(cls, req: NapalmExecutionRequest) -> "NapalmDriver":
        """
        Create driver instance from an execution request.
        """
        if not isinstance(req, NapalmExecutionRequest):
            req = NapalmExecutionRequest.model_validate(req.model_dump())
            req.connection_args = cls.convert_conn_args(req.connection_args)

        # Set default driver_args if not provided
        if req.driver_args is None:
            req.driver_args = NapalmCliArgs() if req.command else NapalmCommitConfigArgs()

        return cls(conn_args=req.connection_args, args=req.driver_args, dry_run=req.dry_run)

    @classmethod
    def validate(cls, req: NapalmExecutionRequest) -> None:
        """
        Validate the request without creating the driver instance.

        Raises:
            pydantic.ValidationError: If the request model validation fails
                (e.g., missing required fields, invalid field types).
            ValueError: If device_type is None in connection_args.
        """
        # Validate the request model
        if not isinstance(req, NapalmExecutionRequest):
            req = NapalmExecutionRequest.model_validate(req.model_dump())

        # Validate connection args and device_type conversion
        cls.convert_conn_args(req.connection_args)

    @classmethod
    def convert_conn_args(cls, conn_args: DriverConnectionArgs) -> NapalmConnectionArgs:
        """
        Convert connection arguments to NAPALM format.

        - host -> hostname (handled by Pydantic alias)
        - device_type -> device_type (Netmiko convention to NAPALM convention)
        """
        if conn_args.device_type is None:
            raise ValueError("device_type is None")

        # Convert device_type from Netmiko to NAPALM convention (if needed)
        conn_args.device_type = NETMIKO_DEVICE_TYPE_MAP.get(  # type: ignore
            conn_args.device_type,
            conn_args.device_type,  # default to itself
        )

        return (
            conn_args
            if isinstance(conn_args, NapalmConnectionArgs)
            else NapalmConnectionArgs.model_validate(conn_args)
        )

    def __init__(
        self,
        conn_args: NapalmConnectionArgs,
        args: NapalmCliArgs | NapalmCommitConfigArgs,
        dry_run: bool = False,
        **kwargs,
    ):
        """
        Initialize the NAPALM driver.
        """
        log.debug(f"Initializing NAPALM driver with {conn_args}")

        self.device = conn_args.device_type
        self.dry_run = dry_run

        self.conn_args = conn_args
        self.args = args

        self.conn_args_dict: dict = {}

        try:
            # Convert parameters format to NAPALM format
            conn_args_dict = conn_args.model_dump(by_alias=True, exclude_none=True)
            del conn_args_dict["device_type"]
        except KeyError as e:
            log.error(f"Failed to init NAPALM driver: {e}")
            raise e

        # Handle optional arguments
        optional_args = conn_args.optional_args if conn_args.optional_args else {}

        # Set connection args
        self.conn_args_dict = conn_args_dict
        self.conn_args_dict["optional_args"] = optional_args

    def connect(self) -> NetworkDriver:
        """
        Connect to the device and return the session.
        """
        try:
            log.debug(f"Connecting to device: {self.conn_args.host} ({self.device})")
            driver = get_network_driver(name=self.device)
            return driver(**self.conn_args_dict)
        except Exception as e:
            log.error(f"Connection failed: {e}")
            raise e

    def send(self, session: NetworkDriver, command: list[str]) -> dict[str, str]:
        """
        Send commands to the device.
        """
        assert isinstance(self.args, NapalmCliArgs)

        if not command:
            log.warning("No command provided")
            return {}

        commands = command if isinstance(command, list) else [command]
        result = {}

        try:
            session.open()
        except Exception as e:
            log.error(f"Failed to open session: {e}")
            raise e

        for cmd in commands:
            if hasattr(session, str(cmd)):
                # Calling NAPALM method
                method = getattr(session, str(cmd))
                method_params = signature(method).parameters

                # Filter arguments based on method parameters
                args = {}
                if self.args:
                    dumped = self.args.model_dump(exclude_none=True)
                    args = {k: v for k, v in dumped if k in method_params}

                try:
                    log.info(f"Executing NAPLAM method: {cmd} with args: {args}")
                    result[cmd] = method(**args)
                except Exception as e:
                    log.error(f"NAPLAM method execution failed: {e}")
                    raise e

            else:
                # Use CLI command
                try:
                    log.info(f"Executing CLI command: {cmd}")
                    resp = session.cli([cmd], encoding=self.args.encoding)
                    result[cmd] = resp[cmd]
                except Exception as e:
                    log.error(f"CLI command execution failed: {e}")
                    raise e

        return result

    def config(self, session: NetworkDriver, cfg: list[str]):
        """
        Configure the device.
        """
        assert isinstance(self.args, NapalmCommitConfigArgs)

        if not cfg:
            log.warning("No configuration provided")
            return {}

        # Process config format
        if isinstance(cfg, list):
            cfg_text = cfg[0] if len(cfg) == 1 else "\n".join(cfg)
        else:
            cfg_text = str(cfg)

        try:
            session.open()
        except Exception as e:
            log.error(f"Failed to open session: {e}")
            raise e

        # Load candidate configuration
        try:
            session.load_merge_candidate(config=cfg_text)
            diff = session.compare_config()
        except Exception as e:
            log.error(f"Configuration comparison failed: {e}")
            raise e

        log.debug(f"Configuration diff: {diff[:50]}...")

        # Apply or discard configuration
        try:
            if self.dry_run:
                log.info("Dry-run mode: not committing configuration")
                session.discard_config()
            else:
                log.info(f"Committing configuration: {self.args}")
                session.commit_config(**self.args.model_dump(exclude_none=True))
        except Exception as e:
            log.error(f"Configuration commit failed: {e}")
            raise e

        result = [diff]
        return result

    def disconnect(self, session):
        """
        Disconnect from the device.
        """
        try:
            log.debug("Disconnecting from device")
            if session:
                session.close()
            return True
        except Exception as e:
            log.error(f"Disconnection failed: {e}")
            raise e


__all__ = ["NapalmDriver"]
