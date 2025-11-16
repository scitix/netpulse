import logging
from typing import Dict, Type

from ..models.common import DriverConnectionArgs
from ..plugins import credentials
from ..plugins.credentials.base import BaseCredentialProvider

log = logging.getLogger(__name__)


class CredentialResolver:
    """Credential resolver service for fetching credentials from providers."""

    def __init__(self):
        self._provider_instances: Dict[str, BaseCredentialProvider] = {}
        self._credential_cache: Dict[str, Dict[str, str]] = {}
        self._validate_config()

    def _validate_config(self):
        """Validate Vault configuration on startup (if configured)."""
        from ..utils import g_config

        if g_config.credential and hasattr(g_config.credential, "vault"):
            try:
                vault_config = g_config.credential.vault
                from ..plugins.credentials.vault.provider import VaultCredentialProvider

                test_provider = VaultCredentialProvider(
                    vault_url=vault_config.url,
                    token=vault_config.token,
                    mount_point=vault_config.mount_point,
                    timeout=vault_config.timeout,
                )
                if test_provider.validate_connection():
                    log.info("Vault connection validated successfully")
                else:
                    log.warning(
                        "Vault connection validation failed, credential plugin may not work"
                    )
            except Exception as e:
                log.warning(f"Failed to validate Vault configuration: {e}")

    def _get_provider_instance(self, provider_name: str) -> BaseCredentialProvider:
        """Get credential provider instance (singleton pattern)."""
        if provider_name not in self._provider_instances:
            provider_class = credentials.get(provider_name)
            if not provider_class:
                raise ValueError(f"Unknown credential provider: {provider_name}")

            instance = self._create_provider_instance(provider_name, provider_class)
            self._provider_instances[provider_name] = instance

        return self._provider_instances[provider_name]

    def _create_provider_instance(
        self, provider_name: str, provider_class: Type[BaseCredentialProvider]
    ) -> BaseCredentialProvider:
        """Create credential provider instance."""
        from ..utils import g_config

        if provider_name != "vault":
            raise ValueError(f"Unsupported credential provider: {provider_name}")

        if not g_config.credential or not hasattr(g_config.credential, "vault"):
            raise ValueError(
                "Vault configuration not found. Please configure credential.vault in config."
            )

        vault_config = g_config.credential.vault
        return provider_class(
            vault_url=vault_config.url,
            token=vault_config.token,
            mount_point=vault_config.mount_point,
            timeout=vault_config.timeout,
        )

    def resolve_credentials(self, connection_args: DriverConnectionArgs) -> DriverConnectionArgs:
        """Resolve credential reference and inject credentials into connection args."""
        if connection_args.credential_ref is None:
            return connection_args

        reference = connection_args.credential_ref
        cache_key = f"{reference.provider}:{reference.path}"

        if cache_key in self._credential_cache:
            log.debug(f"Using cached credentials for {cache_key}")
            creds = self._credential_cache[cache_key]
        else:
            provider = self._get_provider_instance(reference.provider)
            try:
                creds = provider.get_credentials(reference)
                self._credential_cache[cache_key] = creds
                log.debug(f"Cached credentials for {cache_key}")
            except Exception as e:
                log.error(
                    f"Failed to get credentials from {reference.provider}:{reference.path}: {e}"
                )
                raise

        update_dict = {"credential_ref": None}

        if reference.username_key in creds:
            update_dict["username"] = creds[reference.username_key]
        if reference.password_key in creds:
            update_dict["password"] = creds[reference.password_key]

        return connection_args.model_copy(update=update_dict)


g_credential_resolver = CredentialResolver()
