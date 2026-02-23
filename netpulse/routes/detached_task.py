from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query

from ..models.request import DetachedTaskDiscoveryRequest
from ..models.response import DetachedTaskInResponse
from ..services.manager import g_mgr
from .device import _resolve_request_credentials

router = APIRouter(tags=["detached-task"])


@router.get("/detached-tasks", response_model=List[DetachedTaskInResponse])
def list_detached_tasks(
    status: Optional[str] = Query(
        None, description="Filter by status (running/completed/launching)"
    ),
):
    """List all registered detached tasks."""
    tasks = g_mgr.list_detached_tasks(status=status)
    # Convert dict value to list
    return list(tasks.values())


@router.get("/detached-tasks/{task_id}")
def query_detached_task(
    task_id: str,
    offset: Optional[int] = Query(None, ge=0, description="Byte offset to read from log file"),
):
    """
    Synchronously query a detached task's logs and status.
    Returns the latest output and task metadata.
    """
    try:
        return g_mgr.query_detached_task(task_id, offset)
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/detached-tasks/{task_id}")
def kill_detached_task(task_id: str):
    """
    Synchronously terminate a detached task and cleanup its resources.
    """
    success = g_mgr.kill_detached_task(task_id)
    if not success:
        raise HTTPException(status_code=500, detail=f"Failed to kill detached task {task_id}")
    return {"status": "killed", "task_id": task_id}


@router.post("/detached-tasks/discover")
def discover_detached_tasks(req: DetachedTaskDiscoveryRequest):
    """
    Scan a device for active detached tasks and sync the registry.
    """
    _resolve_request_credentials(req)
    try:
        return g_mgr.discover_detached_tasks(req.connection_args, req.driver)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
