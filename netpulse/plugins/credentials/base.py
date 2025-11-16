from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Dict

if TYPE_CHECKING:
    from ...models.common import CredentialReference


class BaseCredentialProvider(ABC):
    """Base class for credential providers."""

    credential_name: str

    @abstractmethod
    def get_credentials(self, reference: "CredentialReference") -> Dict[str, str]:
        """
        Get credentials from provider.

        Args:
            reference: Credential reference containing provider and path info

        Returns:
            Dictionary containing username and password

        Raises:
            CredentialError: When credential retrieval fails
        """
        pass

    @abstractmethod
    def validate_connection(self) -> bool:
        """
        Validate connection to credential store.

        Returns:
            True if connection is valid, False otherwise
        """
        pass
