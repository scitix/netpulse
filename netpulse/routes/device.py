import logging
import time
from datetime import datetime

from fastapi import APIRouter

from ..models import DriverConnectionArgs
from ..models.request import (
    BulkExecutionRequest,
    ConnectionTestRequest,
    ExecutionRequest,
)
from ..models.response import BatchSubmitJobResponse, ConnectionTestResponse, JobInResponse
from ..plugins import credentials, drivers
from ..services.manager import g_mgr
from ..utils import g_config

log = logging.getLogger(__name__)

router = APIRouter(prefix="/device", tags=["device"])


def _resolve_request_credentials(req: ExecutionRequest | ConnectionTestRequest) -> None:
    """
    Hydrate req.connection_args using a credential provider, then drop the reference.
    """
    cred_ref = getattr(req, "credential", None)
    if not g_config.credential.enabled:
        if cred_ref is None:
            return
        raise ValueError("Credential support is disabled in server configuration")

    if cred_ref is None:
        return

    if cred_ref.name is None:
        cred_ref.name = g_config.credential.name

    if cred_ref.name != g_config.credential.name:
        raise ValueError(f"Unsupported credential provider: {cred_ref.name}")

    provider_cls = credentials.get(cred_ref.name)
    if provider_cls is None:
        raise ValueError(f"Credential provider not found: {cred_ref.name}")

    try:
        # Pass raw credential config for provider-specific validation
        provider = provider_cls.from_credential_ref(cred_ref, g_config.credential)
    except Exception as exc:
        log.error(f"Error initializing credential provider '{cred_ref.name}': {exc}")
        raise

    try:
        resolved_args = provider.resolve(req=req, conn_args=req.connection_args)
    except Exception as exc:
        log.error(f"Error resolving credential via '{cred_ref.name}': {exc}")
        raise

    if not isinstance(resolved_args, DriverConnectionArgs):
        raise TypeError(
            f"Credential provider '{cred_ref.name}' must return "
            f"DriverConnectionArgs-compatible object"
        )

    req.connection_args = resolved_args
    req.credential = None


@router.post("/exec", response_model=JobInResponse, status_code=201)
def execute_on_device(req: ExecutionRequest):
    _resolve_request_credentials(req)

    if req.connection_args.host is None:
        raise ValueError("'host' in connection_args is required")

    # Enforce driver-level validation
    dobj = drivers.get(req.driver, None)
    if dobj is None:
        raise ValueError(f"Unsupported driver: {req.driver}")
    dobj.validate(req)

    return g_mgr.execute_on_device(req)


@router.post("/bulk", response_model=BatchSubmitJobResponse, status_code=201)
def execute_on_bulk_devices(req: BulkExecutionRequest):
    # Create base request template excluding devices
    base_req = ExecutionRequest.model_validate(req.model_dump(exclude={"devices"}))
    _resolve_request_credentials(base_req)

    expanded: list[ExecutionRequest] = []
    for device in req.devices:
        # Validate command/config exclusivity at device level first
        if device.command is not None and device.config is not None:
            raise ValueError(
                f"Device {device.host}: cannot specify both 'command' and 'config', choose one"
            )

        # Extract device-level command/config overrides
        device_dict = device.model_dump(
            exclude_defaults=True, exclude_none=True, exclude_unset=True
        )
        device_command = device_dict.pop("command", None)
        device_config = device_dict.pop("config", None)

        # Generate connection_args with device-specific overrides
        connection_args = base_req.connection_args.model_copy(
            update=device_dict,
            deep=True,
        )

        if connection_args.host is None:
            raise ValueError("'host' is required for each device")

        # Determine effective command/config for this device
        # Device-level override takes precedence over base request
        effective_updates = {"connection_args": connection_args}

        if device_command is not None:
            # Device specifies command, override base
            effective_updates["command"] = device_command
            effective_updates["config"] = None
        elif device_config is not None:
            # Device specifies config, override base
            effective_updates["config"] = device_config
            effective_updates["command"] = None
        # else: use base request's command/config (no changes needed)

        # Create device-specific request with updated connection and command/config
        per_device_req = base_req.model_copy(update=effective_updates, deep=True)
        expanded.append(per_device_req)

    # Early return if no devices
    if len(expanded) == 0:
        return BatchSubmitJobResponse(succeeded=[], failed=[])

    # Enforce driver-level validation, only need to check the first one
    dobj = drivers.get(req.driver, None)
    if dobj is None:
        raise ValueError(f"Unsupported driver: {req.driver}")
    dobj.validate(expanded[0])

    result = g_mgr.execute_on_bulk_devices(expanded)
    if result is None:
        return BatchSubmitJobResponse(succeeded=[], failed=[])

    return BatchSubmitJobResponse(
        succeeded=result[0],
        failed=result[1],
    )


@router.post("/test", response_model=ConnectionTestResponse, status_code=200)
def test_device_connection(req: ConnectionTestRequest):
    _resolve_request_credentials(req)

    dobj = drivers.get(req.driver, None)
    if dobj is None:
        raise ValueError(f"Unsupported driver: {req.driver}")

    start_time = time.time()
    try:
        device_info = dobj.test(req.connection_args)
        success = True
        error_message = None
    except Exception as exc:
        device_info = None
        success = False
        error_message = str(exc)
    finally:
        connection_time = time.time() - start_time

    return ConnectionTestResponse(
        success=success,
        latency=connection_time,
        error=error_message,
        result=device_info,
        timestamp=datetime.now().astimezone(),
    )
