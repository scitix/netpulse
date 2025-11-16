import logging
from typing import Any, Dict, List, Optional

import hvac
from hvac.exceptions import Forbidden, InvalidPath, VaultDown, VaultError

from ..plugins.credentials.exceptions import (
    CredentialAccessDenied,
    CredentialError,
    CredentialNotFound,
    VaultConnectionError,
)
from ..utils import g_config

log = logging.getLogger(__name__)


class VaultManager:
    """Vault credential management service."""

    def __init__(self):
        self._client: Optional[hvac.Client] = None
        self._mount_point: str = "secret"

    def _get_client(self) -> hvac.Client:
        """Get or create Vault client."""
        if self._client is None:
            if not g_config.credential or not hasattr(g_config.credential, "vault"):
                raise ValueError(
                    "Vault configuration not found. Please configure credential.vault in config."
                )

            vault_config = g_config.credential.vault
            self._client = hvac.Client(
                url=vault_config.url, token=vault_config.token, timeout=vault_config.timeout
            )
            self._mount_point = vault_config.mount_point

        return self._client

    def test_connection(self) -> Dict[str, Any]:
        """Test Vault connection."""
        try:
            client = self._get_client()
            if not client.is_authenticated():
                return {"success": False, "error": "Vault authentication failed"}

            try:
                client.secrets.kv.v2.read_secret_version(
                    path=".test", mount_point=self._mount_point
                )
            except InvalidPath:
                pass
            except Forbidden:
                return {
                    "success": False,
                    "error": "Vault connection OK but insufficient permissions",
                }

            return {
                "success": True,
                "url": g_config.credential.vault.url,
                "mount_point": self._mount_point,
            }
        except VaultDown:
            return {"success": False, "error": "Vault server is down or unreachable"}
        except Exception as e:
            log.error(f"Vault connection test failed: {e}")
            return {"success": False, "error": str(e)}

    def create_credential(
        self,
        path: str,
        username: str,
        password: str,
        username_key: str = "username",
        password_key: str = "password",
        metadata: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Create or update credential in Vault."""
        try:
            client = self._get_client()

            data = {username_key: username, password_key: password}
            if metadata:
                data.update(metadata)

            client.secrets.kv.v2.create_or_update_secret(
                path=path, secret=data, mount_point=self._mount_point
            )

            return {
                "success": True,
                "path": path,
                "message": "Credential created/updated successfully",
            }
        except Forbidden:
            raise CredentialAccessDenied(f"Access denied to path '{path}'")
        except VaultDown:
            raise VaultConnectionError("Vault server is down or unreachable")
        except VaultError as e:
            log.error(f"Vault error when creating credential at '{path}': {e}")
            raise CredentialError(f"Failed to create credential in Vault: {e}")
        except Exception as e:
            log.error(f"Error creating credential at '{path}': {e}")
            raise CredentialError(f"Unexpected error: {e}")

    def read_credential(self, path: str, show_password: bool = False) -> Dict[str, Any]:
        """Read credential from Vault."""
        try:
            client = self._get_client()
            response = client.secrets.kv.v2.read_secret_version(
                path=path, mount_point=self._mount_point
            )

            data = response["data"]["data"]
            metadata = response.get("data", {}).get("metadata", {})

            username_key = next(
                (k for k in ["username", "user", "login", "account"] if k in data), "username"
            )
            password_key = next(
                (k for k in ["password", "pass", "passwd", "pwd"] if k in data), "password"
            )

            result = {
                "path": path,
                "username": data.get(username_key),
                "username_key": username_key,
            }

            if show_password:
                result["password"] = data.get(password_key)
                result["password_key"] = password_key
            else:
                result["password"] = "***hidden***"
                result["password_key"] = password_key

            if metadata:
                if show_password:
                    result["metadata"] = metadata
                else:
                    result["metadata"] = {
                        k: v for k, v in metadata.items() if "password" not in k.lower()
                    }

            return result
        except InvalidPath:
            raise CredentialNotFound(f"Path '{path}' not found in Vault")
        except Forbidden:
            raise CredentialAccessDenied(f"Access denied to path '{path}'")
        except VaultDown:
            raise VaultConnectionError("Vault server is down or unreachable")
        except VaultError as e:
            log.error(f"Vault error when reading credential from '{path}': {e}")
            raise CredentialError(f"Failed to read credential from Vault: {e}")
        except Exception as e:
            log.error(f"Error reading credential from '{path}': {e}")
            raise CredentialError(f"Unexpected error: {e}")

    def delete_credential(self, path: str) -> Dict[str, Any]:
        """Delete credential from Vault."""
        try:
            client = self._get_client()
            client.secrets.kv.v2.delete_metadata_and_all_versions(
                path=path, mount_point=self._mount_point
            )

            return {"success": True, "path": path, "message": "Credential deleted successfully"}
        except InvalidPath:
            raise CredentialNotFound(f"Path '{path}' not found in Vault")
        except Forbidden:
            raise CredentialAccessDenied(f"Access denied to path '{path}'")
        except VaultDown:
            raise VaultConnectionError("Vault server is down or unreachable")
        except VaultError as e:
            log.error(f"Vault error when deleting credential at '{path}': {e}")
            raise CredentialError(f"Failed to delete credential from Vault: {e}")
        except Exception as e:
            log.error(f"Error deleting credential at '{path}': {e}")
            raise CredentialError(f"Unexpected error: {e}")

    def list_credentials(
        self, path_prefix: Optional[str] = None, recursive: bool = False
    ) -> List[str]:
        """List credential paths in Vault."""
        try:
            client = self._get_client()

            list_path = path_prefix or ""

            def _list_recursive(current_path: str) -> List[str]:
                """Recursively list paths."""
                result = []
                try:
                    response = client.secrets.kv.v2.list_secrets(
                        path=current_path, mount_point=self._mount_point
                    )
                    keys = response.get("data", {}).get("keys", [])

                    for key in keys:
                        if current_path:
                            full_path = f"{current_path}/{key.rstrip('/')}"
                        else:
                            full_path = key.rstrip("/")

                        if key.endswith("/"):
                            # It's a directory, recurse
                            result.extend(_list_recursive(full_path))
                        else:
                            # It's a file/secret
                            result.append(full_path)

                except InvalidPath:
                    # Path doesn't exist, return empty list
                    pass

                return result

            try:
                response = client.secrets.kv.v2.list_secrets(
                    path=list_path, mount_point=self._mount_point
                )
                keys = response.get("data", {}).get("keys", [])

                if not recursive:
                    # Return only direct children
                    result = []
                    for key in keys:
                        if list_path:
                            full_path = f"{list_path}/{key.rstrip('/')}"
                        else:
                            full_path = key.rstrip("/")
                        result.append(full_path)
                    return result
                else:
                    # Recursively list all paths
                    return _list_recursive(list_path)

            except InvalidPath:
                # Path doesn't exist
                return []
        except Forbidden:
            raise CredentialAccessDenied(f"Access denied to path '{path_prefix or ''}'")
        except VaultDown:
            raise VaultConnectionError("Vault server is down or unreachable")
        except VaultError as e:
            log.error(f"Vault error when listing credentials: {e}")
            raise CredentialError(f"Failed to list credentials from Vault: {e}")
        except Exception as e:
            log.error(f"Error listing credentials: {e}")
            raise CredentialError(f"Unexpected error: {e}")

    def get_metadata(self, path: str) -> Dict[str, Any]:
        """Get credential metadata from Vault."""
        try:
            client = self._get_client()
            mount_path = f"{self._mount_point}/metadata/{path}"
            response = client.read(path=mount_path)
            if response is None:
                raise CredentialNotFound(f"Path '{path}' not found in Vault")

            metadata = response.get("data", {})
            versions = metadata.get("versions", {})

            current_version = metadata.get("current_version")
            oldest_version = metadata.get("oldest_version")

            result = {
                "path": path,
                "current_version": current_version,
                "oldest_version": oldest_version,
                "created_time": metadata.get("created_time"),
                "updated_time": metadata.get("updated_time"),
                "versions": {},
            }

            if versions:
                for version_num, version_info in versions.items():
                    result["versions"][version_num] = {
                        "created_time": version_info.get("created_time"),
                        "deletion_time": version_info.get("deletion_time"),
                        "destroyed": version_info.get("destroyed", False),
                    }

            try:
                secret_response = client.secrets.kv.v2.read_secret_version(
                    path=path, mount_point=self._mount_point
                )
                secret_data = secret_response.get("data", {}).get("data", {})
                custom_metadata = {
                    k: v
                    for k, v in secret_data.items()
                    if k not in ["username", "user", "login", "account", "password", "pass", "passwd", "pwd"]
                }
                if custom_metadata:
                    result["custom_metadata"] = custom_metadata
            except Exception:
                pass

            return result
        except InvalidPath:
            raise CredentialNotFound(f"Path '{path}' not found in Vault")
        except Forbidden:
            raise CredentialAccessDenied(f"Access denied to path '{path}'")
        except VaultDown:
            raise VaultConnectionError("Vault server is down or unreachable")
        except VaultError as e:
            log.error(f"Vault error when reading metadata from '{path}': {e}")
            raise CredentialError(f"Failed to read metadata from Vault: {e}")
        except Exception as e:
            log.error(f"Error reading metadata from '{path}': {e}")
            raise CredentialError(f"Unexpected error: {e}")

    def batch_read_credentials(
        self, paths: List[str], show_password: bool = False
    ) -> Dict[str, Any]:
        """Batch read credentials from Vault."""
        results = {}
        errors = {}

        for path in paths:
            try:
                credential = self.read_credential(path=path, show_password=show_password)
                results[path] = credential
            except CredentialNotFound as e:
                errors[path] = {"error": "not_found", "message": str(e)}
            except CredentialAccessDenied as e:
                errors[path] = {"error": "access_denied", "message": str(e)}
            except Exception as e:
                log.error(f"Error reading credential from '{path}': {e}")
                errors[path] = {"error": "unknown", "message": str(e)}

        return {
            "success": len(errors) == 0,
            "results": results,
            "errors": errors,
            "total": len(paths),
            "succeeded": len(results),
            "failed": len(errors),
        }


g_vault_manager = VaultManager()
