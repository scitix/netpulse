import logging
import time
from datetime import datetime
from typing import Optional, Tuple

from fastapi import APIRouter

from ..models.common import DriverConnectionArgs
from ..models.request import (
    BatchDeviceRequest,
    ConnectionTestRequest,
    DeviceRequest,
    PullingRequest,
    PushingRequest,
)
from ..models.response import BatchSubmitJobResponse, ConnectionTestResponse, SubmitJobResponse
from ..services.manager import g_mgr

log = logging.getLogger(__name__)

router = APIRouter(prefix="/device", tags=["device"])


@router.post("/execute", response_model=SubmitJobResponse, status_code=201)
def execute_device_operation(req: DeviceRequest):
    if req.is_pull_operation():
        pull_req = req.to_pulling_request()
        pull_req.connection_args.enforced_field_check()
        job = g_mgr.pull_from_device(pull_req)
        return SubmitJobResponse(code=0, message="success", data=job)
    else:
        push_req = req.to_pushing_request()
        push_req.connection_args.enforced_field_check()
        job = g_mgr.push_to_device(push_req)
        return SubmitJobResponse(code=0, message="success", data=job)


@router.post("/bulk", response_model=BatchSubmitJobResponse, status_code=201)
def bulk_device_operation(req: BatchDeviceRequest):
    if req.is_pull_operation():
        batch_pull_req = req.to_batch_pulling_request()
        base_req = PullingRequest.model_validate(batch_pull_req.model_dump(exclude={"devices"}))

        expanded = []
        for device in batch_pull_req.devices:
            connection_args = batch_pull_req.connection_args.model_copy(
                update=device.model_dump(
                    exclude_defaults=True, exclude_none=True, exclude_unset=True
                ),
                deep=True,
            )
            connection_args.enforced_field_check()

            per_device_req = base_req.model_copy(
                update={"connection_args": connection_args}, deep=True
            )
            expanded.append(per_device_req)

        result = g_mgr.pull_from_batch_devices(expanded)
        if result is None:
            return BatchSubmitJobResponse(code=0, message="success", data=None)
        data = BatchSubmitJobResponse.BatchSubmitJobData(
            succeeded=result[0],
            failed=result[1],
        )
        return BatchSubmitJobResponse(code=0, message="success", data=data)
    else:
        batch_push_req = req.to_batch_pushing_request()
        base_req = PushingRequest.model_validate(batch_push_req.model_dump(exclude={"devices"}))

        expanded = []
        for device in batch_push_req.devices:
            connection_args = batch_push_req.connection_args.model_copy(
                update=device.model_dump(
                    exclude_defaults=True, exclude_none=True, exclude_unset=True
                ),
                deep=True,
            )
            connection_args.enforced_field_check()

            per_device_req = base_req.model_copy(
                update={"connection_args": connection_args}, deep=True
            )
            expanded.append(per_device_req)

        result = g_mgr.push_to_batch_devices(expanded)
        if result is None:
            return BatchSubmitJobResponse(code=0, message="success", data=None)
        data = BatchSubmitJobResponse.BatchSubmitJobData(
            succeeded=result[0],
            failed=result[1],
        )
        return BatchSubmitJobResponse(code=0, message="success", data=data)


@router.post("/test-connection", response_model=ConnectionTestResponse, status_code=200)
def test_device_connection(req: ConnectionTestRequest):
    req.connection_args.enforced_field_check()

    start_time = time.time()
    success, error_message, device_info = _test_connection(req.driver, req.connection_args)
    connection_time = time.time() - start_time

    data = ConnectionTestResponse.ConnectionTestData(
        success=success,
        connection_time=connection_time,
        error_message=error_message,
        device_info=device_info,
        timestamp=datetime.now().astimezone(),
    )

    return ConnectionTestResponse(
        code=0,
        message="Connection test completed" if success else "Connection test failed",
        data=data,
    )


def _test_connection(
    driver: str, connection_args: DriverConnectionArgs
) -> Tuple[bool, Optional[str], Optional[dict]]:
    try:
        if driver == "netmiko":
            return _test_netmiko_connection(connection_args)
        elif driver == "napalm":
            return _test_napalm_connection(connection_args)
        elif driver == "pyeapi":
            return _test_pyeapi_connection(connection_args)
        else:
            return False, f"Unsupported driver: {driver}", None

    except Exception as e:
        return False, str(e), None


def _test_netmiko_connection(
    connection_args: DriverConnectionArgs,
) -> Tuple[bool, Optional[str], Optional[dict]]:
    try:
        from netmiko import ConnectHandler

        test_args = connection_args.model_dump(exclude_none=True)
        connection = ConnectHandler(**test_args)

        device_info = {
            "prompt": connection.find_prompt(),
            "device_type": test_args.get("device_type"),
            "host": test_args.get("host"),
        }

        connection.disconnect()

        return True, None, device_info

    except Exception as e:
        return False, str(e), None


def _test_napalm_connection(
    connection_args: DriverConnectionArgs,
) -> Tuple[bool, Optional[str], Optional[dict]]:
    try:
        import napalm

        test_args = connection_args.model_dump(exclude_none=True)

        driver_name = test_args.get("driver") or test_args.get("device_type")
        if not driver_name:
            return False, "Driver name not specified for NAPALM", None

        host = test_args.get("host") or test_args.get("hostname")
        if not host:
            return False, "Host address not specified for NAPALM", None

        driver = napalm.get_network_driver(driver_name)
        device = driver(
            hostname=host,
            username=test_args.get("username"),
            password=test_args.get("password"),
            optional_args=test_args.get("optional_args", {}),
        )

        device.open()
        device_info = {"driver": driver_name, "host": host, "connection_type": "napalm"}
        device.close()

        return True, None, device_info

    except Exception as e:
        return False, str(e), None


def _test_pyeapi_connection(
    connection_args: DriverConnectionArgs,
) -> Tuple[bool, Optional[str], Optional[dict]]:
    try:
        import pyeapi

        test_args = connection_args.model_dump(exclude_none=True)
        node = pyeapi.connect(**test_args)

        _ = node.enable("show version")

        device_info = {
            "host": test_args.get("host"),
            "connection_type": "pyeapi",
            "api_version": "eAPI",
        }

        return True, None, device_info

    except Exception as e:
        return False, str(e), None
