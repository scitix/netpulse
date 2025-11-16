import logging
from typing import Dict

import hvac
from hvac.exceptions import Forbidden, InvalidPath, VaultDown, VaultError

from netpulse.models.common import CredentialReference
from ..base import BaseCredentialProvider
from ..exceptions import (
    CredentialAccessDenied,
    CredentialError,
    CredentialNotFound,
    CredentialValidationError,
    VaultConnectionError,
)

log = logging.getLogger(__name__)


class VaultCredentialProvider(BaseCredentialProvider):
    """Vault credential provider implementation."""

    credential_name = "vault"

    def __init__(self, vault_url: str, token: str, mount_point: str = "secret", timeout: int = 30):
        """Initialize Vault credential provider."""
        self.vault_url = vault_url
        self.token = token
        self.mount_point = mount_point
        self.timeout = timeout
        self.client = hvac.Client(url=vault_url, token=token, timeout=timeout)

    def get_credentials(self, reference: CredentialReference) -> Dict[str, str]:
        """Get credentials from Vault."""
        try:
            response = self.client.secrets.kv.v2.read_secret_version(
                path=reference.path, mount_point=self.mount_point
            )

            data = response["data"]["data"]
            username = data.get(reference.username_key)
            password = data.get(reference.password_key)

            if not username or not password:
                missing = []
                if not username:
                    missing.append(reference.username_key)
                if not password:
                    missing.append(reference.password_key)
                raise CredentialValidationError(
                    f"Missing required fields {missing} in Vault path '{reference.path}'"
                )

            return {
                reference.username_key: username,
                reference.password_key: password,
            }
        except InvalidPath:
            raise CredentialNotFound(f"Path '{reference.path}' not found in Vault")
        except Forbidden:
            raise CredentialAccessDenied(f"Access denied to path '{reference.path}'")
        except VaultDown:
            raise VaultConnectionError("Vault server is down or unreachable")
        except CredentialValidationError:
            raise
        except VaultError as e:
            log.error(f"Vault error when getting credentials from '{reference.path}': {e}")
            raise CredentialError(f"Failed to get credentials from Vault: {e}")
        except Exception as e:
            log.error(f"Error getting credentials from '{reference.path}': {e}")
            raise CredentialError(f"Unexpected error: {e}")

    def validate_connection(self) -> bool:
        """Validate Vault connection."""
        try:
            return self.client.is_authenticated()
        except Exception as e:
            log.error(f"Vault connection validation failed: {e}")
            return False
