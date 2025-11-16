from typing import Dict, Optional

from pydantic import BaseModel, Field


class VaultCredentialCreateRequest(BaseModel):
    """Request model for creating/updating Vault credentials."""

    path: str = Field(..., description="Credential path in Vault")
    username: str = Field(..., description="Username")
    password: str = Field(..., description="Password")
    username_key: Optional[str] = Field("username", description="Username field name in Vault")
    password_key: Optional[str] = Field("password", description="Password field name in Vault")
    metadata: Optional[Dict[str, str]] = Field(None, description="Additional metadata")

    model_config = {
        "json_schema_extra": {
            "example": {
                "path": "sites/hq/readonly",
                "username": "admin",
                "password": "admin123",
                "username_key": "username",
                "password_key": "password",
                "metadata": {"description": "HQ site readonly credentials"},
            }
        }
    }


class VaultCredentialReadRequest(BaseModel):
    """Request model for reading Vault credentials (metadata only, no password)."""

    path: str = Field(..., description="Credential path in Vault")
    show_password: bool = Field(
        False, description="Whether to show password in response (default: False)"
    )


class VaultCredentialDeleteRequest(BaseModel):
    """Request model for deleting Vault credentials."""

    path: str = Field(..., description="Credential path in Vault")


class VaultCredentialListRequest(BaseModel):
    """Request model for listing Vault credential paths."""

    path_prefix: Optional[str] = Field(None, description="Path prefix to filter results")
    recursive: bool = Field(False, description="Whether to list recursively")


class VaultTestConnectionRequest(BaseModel):
    """Request model for testing Vault connection."""

    pass


class VaultCredentialMetadataRequest(BaseModel):
    """Request model for reading Vault credential metadata."""

    path: str = Field(..., description="Credential path in Vault")

    model_config = {
        "json_schema_extra": {
            "example": {
                "path": "sites/hq/readonly",
            }
        }
    }


class VaultCredentialBatchReadRequest(BaseModel):
    """Request model for batch reading Vault credentials."""

    paths: list[str] = Field(..., description="List of credential paths to read", min_length=1, max_length=100)
    show_password: bool = Field(
        False, description="Whether to show password in response (default: False)"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "paths": ["sites/hq/readonly", "sites/branch1/admin", "devices/core/backup"],
                "show_password": False,
            }
        }
    }
