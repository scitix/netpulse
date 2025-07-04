from typing import Optional

from fastapi import APIRouter, Query

from ..models.response import (
    BaseResponse,
    DeleteJobResponse,
    DeleteWorkerResponse,
    GetJobResponse,
    GetWorkerResponse,
)
from ..services.manager import g_mgr
from ..utils import g_config

router = APIRouter(prefix="", tags=["manage"])


@router.get("/job", response_model=GetJobResponse)
def get_jobs(
    id: Optional[str] = Query(None, description="Get the exact job by ID, overrides all filters"),
    queue: Optional[str] = Query(None, description="Filter by queue name"),
    status: Optional[str] = Query(None, description="Filter by job status"),
    node: Optional[str] = Query(None, description="Filter by node name"),
    host: Optional[str] = Query(None, description="Filter by pinned host name"),
):
    if id:
        resp = g_mgr.get_job_list_by_ids([id])
        return GetJobResponse(code=0, message="success", data=resp)

    q_name = None
    if host:
        q_name = g_config.get_host_queue_name(host)
    if node:
        q_name = g_config.get_node_queue_name(node)
    if queue:
        q_name = queue

    resp = g_mgr.get_job_list(q_name=q_name, status=status)
    return GetJobResponse(code=0, message="success", data=resp)


@router.delete("/job", response_model=DeleteJobResponse)
def delete_jobs(
    id: Optional[str] = Query(
        None, description="Delete the exact job by ID, overrides all filters"
    ),
    queue: Optional[str] = Query(None, description="Filter by queue name"),
    host: Optional[str] = Query(None, description="Filter by pinned host name"),
):
    """
    This can only delete "queued" jobs, i.e.,
    cancel jobs that is not yet started.
    """
    if id:
        resp = g_mgr.cancel_job(id=id)
        return DeleteJobResponse(code=0, message="success", data=resp)

    q_name = None
    if host:
        q_name = g_config.get_host_queue_name(host)
    if queue:
        q_name = queue

    resp = g_mgr.cancel_job(q_name=q_name)
    return DeleteJobResponse(code=0, message="success", data=resp)


# Get all running workers
@router.get("/worker", response_model=GetWorkerResponse)
def get_workers(
    queue: Optional[str] = Query(None, description="Filter by queue name, overrides other filters"),
    node: Optional[str] = Query(None, description="Filter by node name"),
    host: Optional[str] = Query(None, description="Filter by pinned host name"),
):
    q_name = None
    if host:
        q_name = g_config.get_host_queue_name(host)
    if node:
        q_name = g_config.get_node_queue_name(node)
    if queue:
        q_name = queue

    resp = g_mgr.get_worker_list(q_name=q_name)
    return GetWorkerResponse(code=0, message="success", data=resp)


@router.delete("/worker", response_model=DeleteWorkerResponse)
def delete_workers(
    name: Optional[str] = Query(None, description="Worker name to delete"),
    queue: Optional[str] = Query(None, description="Filter by queue name"),
    node: Optional[str] = Query(None, description="Filter by node name"),
    host: Optional[str] = Query(None, description="Filter by pinned host name"),
):
    q_name = None
    if host:
        q_name = g_config.get_host_queue_name(host)
    if node:
        q_name = g_config.get_node_queue_name(node)
    if queue:
        q_name = queue
    if name:  # override all filters
        q_name = None

    killed = g_mgr.kill_worker(q_name=q_name, name=name)
    return DeleteWorkerResponse(code=0, message="success", data=killed)


@router.get("/health", response_model=BaseResponse)
def health_check():
    return BaseResponse(code=0, message="success", data="ok")
