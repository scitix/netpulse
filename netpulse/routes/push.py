import logging

from fastapi import APIRouter

from ..models.request import BatchPushingRequest, PushingRequest
from ..models.response import BatchSubmitJobResponse, SubmitJobResponse
from ..services.manager import g_mgr

log = logging.getLogger(__name__)

router = APIRouter(prefix="/push", tags=["push"])


@router.post("/", response_model=SubmitJobResponse, status_code=201)
def push(req: PushingRequest):
    if req.driver is None:
        raise ValueError("driver is required for this request")
    resp = g_mgr.push_to_device(req)
    return SubmitJobResponse(code=0, message="success", data=resp)


@router.post("/batch", response_model=BatchSubmitJobResponse, status_code=201)
def pull_in_batch(req: BatchPushingRequest):
    if req.driver is None:
        raise ValueError("driver is required for this request")
    if req.connection_args is None:
        raise ValueError("connection_args is required for this request")

    # Create base request template excluding devices
    base_req = PushingRequest.model_validate(req.model_dump(exclude={"devices"}))

    expanded: list[PushingRequest] = []
    for device in req.devices:
        # Generate connection_args with device-specific overrides
        connection_args = req.connection_args.model_copy(
            update=device.model_dump(exclude_defaults=True, exclude_none=True, exclude_unset=True),
            deep=True,
        )
        connection_args.enforced_field_check()

        # Create device-specific request with updated connection
        per_device_req = base_req.model_copy(update={"connection_args": connection_args}, deep=True)
        expanded.append(per_device_req)

    result = g_mgr.push_to_batch_devices(expanded)
    if result is None:
        return BatchSubmitJobResponse(code=0, message="success", data=None)

    data = BatchSubmitJobResponse.BatchSubmitJobData(
        succeeded=result[0],
        failed=result[1],
    )
    return BatchSubmitJobResponse(code=0, message="success", data=data)
