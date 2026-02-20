from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query

from ..models.response import JobInResponse, WorkerInResponse
from ..services.manager import g_mgr
from ..utils import g_config

router = APIRouter(tags=["manage"])


@router.get("/jobs", response_model=List[JobInResponse])
def get_jobs(
    queue: Optional[str] = Query(None, description="Filter by queue name"),
    status: Optional[str] = Query(None, description="Filter by job status"),
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

    return g_mgr.get_job_list(q_name=q_name, status=status)


@router.get("/jobs/{id}", response_model=JobInResponse)
def get_job(id: str):
    resp = g_mgr.get_job_list_by_ids([id])
    if not resp:
        raise HTTPException(status_code=404, detail=f"Job {id} not found")
    return resp[0]


@router.delete("/jobs/{id}")
def delete_job(id: str):
    """
    Cancel a queued job.
    """
    resp = g_mgr.cancel_job(id=id)
    if not resp:
        raise HTTPException(status_code=404, detail=f"Job {id} not found or not in queued state")
    return {"id": id}


@router.delete("/jobs")
def delete_jobs(
    queue: Optional[str] = Query(None, description="Filter by queue name"),
    host: Optional[str] = Query(None, description="Filter by pinned host name"),
):
    q_name = None
    if host:
        q_name = g_config.get_host_queue_name(host)
    if queue:
        q_name = queue

    resp = g_mgr.cancel_job(q_name=q_name)
    return resp


@router.get("/workers", response_model=List[WorkerInResponse])
def get_workers(
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

    return g_mgr.get_worker_list(q_name=q_name)


@router.delete("/workers/{name}")
def delete_worker(name: str):
    killed = g_mgr.kill_worker(name=name)
    if not killed:
        raise HTTPException(status_code=404, detail=f"Worker {name} not found")
    return {"name": name}


@router.delete("/workers")
def delete_workers(
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

    killed = g_mgr.kill_worker(q_name=q_name)
    return killed


@router.get("/health")
def health_check():
    return {"status": "ok"}
