class CredentialError(Exception):
    """Base exception for credential-related errors."""

    pass


class CredentialProviderNotFound(CredentialError):
    """Credential provider not found."""

    pass


class CredentialNotFound(CredentialError):
    """Credential not found in Vault."""

    pass


class CredentialAccessDenied(CredentialError):
    """Access denied to credential."""

    pass


class VaultConnectionError(CredentialError):
    """Vault connection failed."""

    pass


class CredentialValidationError(CredentialError):
    """Credential validation failed (missing required fields)."""

    pass
