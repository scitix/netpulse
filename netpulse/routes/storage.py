import logging
import os

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from ..utils import g_config

router = APIRouter(prefix="/storage", tags=["storage"])
log = logging.getLogger(__name__)


@router.get("/fetch/{file_id:path}")
async def fetch_staged_file(file_id: str):
    """
    Fetch a staged download file by its ID (relative path in downloads directory).
    """
    staging_dir = str(g_config.storage.staging)
    download_dir = os.path.join(staging_dir, "downloads")

    # Path traversal protection - ensure result is within download_dir
    download_dir_abs = os.path.abspath(download_dir)
    file_path = os.path.abspath(os.path.join(download_dir_abs, file_id))

    # Requirement: file_path must be inside download_dir_abs
    # We check if the relative path starts with '..'
    rel = os.path.relpath(file_path, download_dir_abs)
    if rel.startswith(".."):
        log.warning(f"Blocking potential path traversal attempt: {file_id}. rel={rel}")
        raise HTTPException(status_code=403, detail="Forbidden")

    if not os.path.exists(file_path):
        log.error(f"File not found in staging: {file_path}")
        raise HTTPException(status_code=404, detail="File not found")

    log.info(f"Serving download file: {file_path}")
    return FileResponse(
        path=file_path, filename=os.path.basename(file_path), media_type="application/octet-stream"
    )
