import logging

from fastapi import APIRouter

from ..models.request import BatchPullingRequest, PullingRequest
from ..models.response import BatchSubmitJobResponse, SubmitJobResponse
from ..services.manager import g_mgr

log = logging.getLogger(__name__)

router = APIRouter(prefix="/pull", tags=["pull"])


@router.post("/", response_model=SubmitJobResponse, status_code=201)
def pull(req: PullingRequest):
    if req.driver is None:
        raise ValueError("driver is required for this request")
    req.connection_args.enforced_field_check()
    job = g_mgr.pull_from_device(req)
    return SubmitJobResponse(code=200, message="success", data=job)


@router.post("/batch", response_model=BatchSubmitJobResponse, status_code=201)
def pull_in_batch(req: BatchPullingRequest):
    if req.driver is None:
        raise ValueError("driver is required for this request")
    if req.connection_args is None:
        raise ValueError("connection_args is required for this request")

    # Create base request template excluding devices
    base_req = PullingRequest.model_validate(req.model_dump(exclude={"devices"}))

    expanded: list[PullingRequest] = []
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

    result = g_mgr.pull_from_batch_devices(expanded)
    if result is None:
        return BatchSubmitJobResponse(code=200, message="success", data=None)

    data = BatchSubmitJobResponse.BatchSubmitJobData(
        succeeded=result[0],
        failed=result[1],
    )
    return BatchSubmitJobResponse(code=200, message="success", data=data)
