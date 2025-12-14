from typing import Any

from pydantic import BaseModel

from ...models import DriverConnectionArgs
from ...models.common import CredentialRef


class BaseCredentialProvider:
    """Abstract base class for credential providers."""

    credential_name: str = "base"

    @classmethod
    def from_credential_ref(
        cls, ref: CredentialRef, plugin_cfg: BaseModel | None
    ) -> "BaseCredentialProvider":
        """
        Instantiate provider from a credential reference and raw plugin config.
        """
        raise NotImplementedError

    def resolve(self, req: Any, conn_args: DriverConnectionArgs) -> DriverConnectionArgs:
        """
        Return a new DriverConnectionArgs with secrets populated.
        Implementations MUST NOT log secret values.
        """
        raise NotImplementedError


__all__ = ["BaseCredentialProvider"]
