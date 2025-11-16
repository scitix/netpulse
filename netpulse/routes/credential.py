import logging

from fastapi import APIRouter, HTTPException

from ..models.credential import (
    VaultCredentialBatchReadRequest,
    VaultCredentialCreateRequest,
    VaultCredentialDeleteRequest,
    VaultCredentialListRequest,
    VaultCredentialMetadataRequest,
    VaultCredentialReadRequest,
    VaultTestConnectionRequest,
)
from ..models.response import BaseResponse
from ..plugins.credentials.exceptions import (
    CredentialAccessDenied,
    CredentialError,
    CredentialNotFound,
    VaultConnectionError,
)
from ..services.vault_manager import g_vault_manager

log = logging.getLogger(__name__)

router = APIRouter(prefix="/credential", tags=["credential"])


@router.post("/vault/test", response_model=BaseResponse)
def test_vault_connection(req: VaultTestConnectionRequest):
    """Test Vault connection."""
    result = g_vault_manager.test_connection()
    if result.get("success"):
        return BaseResponse(code=200, message="Vault connection successful", data=result)
    return BaseResponse(code=-1, message="Vault connection failed", data=result)


@router.post("/vault/create", response_model=BaseResponse)
def create_vault_credential(req: VaultCredentialCreateRequest):
    """Create or update credential in Vault."""
    try:
        result = g_vault_manager.create_credential(
            path=req.path,
            username=req.username,
            password=req.password,
            username_key=req.username_key,
            password_key=req.password_key,
            metadata=req.metadata,
        )
        return BaseResponse(
            code=200, message="Credential created/updated successfully", data=result
        )
    except CredentialAccessDenied as e:
        raise HTTPException(status_code=403, detail=str(e))
    except VaultConnectionError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except CredentialError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        log.error(f"Error creating Vault credential: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/vault/read", response_model=BaseResponse)
def read_vault_credential(req: VaultCredentialReadRequest):
    """Read credential from Vault (password hidden by default)."""
    try:
        result = g_vault_manager.read_credential(path=req.path, show_password=req.show_password)
        return BaseResponse(code=200, message="Credential read successfully", data=result)
    except CredentialNotFound as e:
        raise HTTPException(status_code=404, detail=str(e))
    except CredentialAccessDenied as e:
        raise HTTPException(status_code=403, detail=str(e))
    except VaultConnectionError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except CredentialError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        log.error(f"Error reading Vault credential: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/vault/delete", response_model=BaseResponse)
def delete_vault_credential(req: VaultCredentialDeleteRequest):
    """Delete credential from Vault."""
    try:
        result = g_vault_manager.delete_credential(path=req.path)
        return BaseResponse(code=200, message="Credential deleted successfully", data=result)
    except CredentialNotFound as e:
        raise HTTPException(status_code=404, detail=str(e))
    except CredentialAccessDenied as e:
        raise HTTPException(status_code=403, detail=str(e))
    except VaultConnectionError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except CredentialError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        log.error(f"Error deleting Vault credential: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/vault/list", response_model=BaseResponse)
def list_vault_credentials(req: VaultCredentialListRequest):
    """List credential paths in Vault."""
    try:
        paths = g_vault_manager.list_credentials(
            path_prefix=req.path_prefix, recursive=req.recursive
        )
        return BaseResponse(
            code=200,
            message="Credentials listed successfully",
            data={"paths": paths, "count": len(paths)},
        )
    except CredentialAccessDenied as e:
        raise HTTPException(status_code=403, detail=str(e))
    except VaultConnectionError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except CredentialError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        log.error(f"Error listing Vault credentials: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/vault/metadata", response_model=BaseResponse)
def get_vault_credential_metadata(req: VaultCredentialMetadataRequest):
    """Get credential metadata from Vault."""
    try:
        result = g_vault_manager.get_metadata(path=req.path)
        return BaseResponse(code=200, message="Metadata retrieved successfully", data=result)
    except CredentialNotFound as e:
        raise HTTPException(status_code=404, detail=str(e))
    except CredentialAccessDenied as e:
        raise HTTPException(status_code=403, detail=str(e))
    except VaultConnectionError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except CredentialError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        log.error(f"Error getting Vault credential metadata: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/vault/batch-read", response_model=BaseResponse)
def batch_read_vault_credentials(req: VaultCredentialBatchReadRequest):
    """Batch read credentials from Vault."""
    try:
        result = g_vault_manager.batch_read_credentials(
            paths=req.paths, show_password=req.show_password
        )
        message = (
            f"Batch read completed: {result['succeeded']} succeeded, {result['failed']} failed"
        )
        return BaseResponse(code=200, message=message, data=result)
    except VaultConnectionError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except CredentialError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        log.error(f"Error batch reading Vault credentials: {e}")
        raise HTTPException(status_code=500, detail=str(e))
