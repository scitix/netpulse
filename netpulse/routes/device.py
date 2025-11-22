import logging
import time
from datetime import datetime

from fastapi import APIRouter

from ..models.request import (
    BulkExecutionRequest,
    ConnectionTestRequest,
    ExecutionRequest,
)
from ..models.response import BatchSubmitJobResponse, ConnectionTestResponse, SubmitJobResponse
from ..plugins import drivers
from ..services.manager import g_mgr

log = logging.getLogger(__name__)

router = APIRouter(prefix="/device", tags=["device"])


@router.post("/exec", response_model=SubmitJobResponse, status_code=201)
def execute_on_device(req: ExecutionRequest):
    if req.connection_args.host is None:
        raise ValueError("'host' in connection_args is required")

    # Enforce driver-level validation
    dobj = drivers.get(req.driver, None)
    if dobj is None:
        raise ValueError(f"Unsupported driver: {req.driver}")
    dobj.validate(req)

    resp = g_mgr.execute_on_device(req)
    return SubmitJobResponse(code=201, message="success", data=resp)


@router.post("/bulk", response_model=BulkExecutionRequest, status_code=201)
def execute_on_bulk_devices(req: BulkExecutionRequest):
    # Create base request template excluding devices
    base_req = ExecutionRequest.model_validate(req.model_dump(exclude={"devices"}))

    expanded: list[ExecutionRequest] = []
    for device in req.devices:
        # Generate connection_args with device-specific overrides
        connection_args = req.connection_args.model_copy(
            update=device.model_dump(exclude_defaults=True, exclude_none=True, exclude_unset=True),
            deep=True,
        )

        if connection_args.host is None:
            raise ValueError("'host' is required for each device")

        # Create device-specific request with updated connection
        per_device_req = base_req.model_copy(update={"connection_args": connection_args}, deep=True)
        expanded.append(per_device_req)

    # Early return if no devices
    if len(expanded) == 0:
        return BatchSubmitJobResponse(code=200, message="success", data=None)

    # Enforce driver-level validation, only need to check the first one
    dobj = drivers.get(req.driver, None)
    if dobj is None:
        raise ValueError(f"Unsupported driver: {req.driver}")
    dobj.validate(expanded[0])

    result = g_mgr.execute_on_bulk_devices(expanded)
    if result is None:
        return BatchSubmitJobResponse(code=200, message="success", data=None)

    data = BatchSubmitJobResponse.BatchSubmitJobData(
        succeeded=result[0],
        failed=result[1],
    )
    return BatchSubmitJobResponse(code=200, message="success", data=data)


@router.post("/test", response_model=ConnectionTestResponse, status_code=200)
def test_device_connection(req: ConnectionTestRequest):
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

    data = ConnectionTestResponse.ConnectionTestData(
        success=success,
        latency=connection_time,
        error=error_message,
        result=device_info,
        timestamp=datetime.now().astimezone(),
    )

    return ConnectionTestResponse(
        code=200,
        message="Connection test completed" if success else "Connection test failed",
        data=data,
    )
