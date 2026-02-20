import json
import logging
import time
from typing import Any, ClassVar, Optional

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    HttpUrl,
    ValidationError,
    field_validator,
    model_validator,
)

from netpulse.services.rediz import g_rdb

try:
    import hvac  # type: ignore
except ImportError:  # pragma: no cover - handled in factory
    hvac = None  # type: ignore

from ....models import DriverConnectionArgs
from ....models.common import CredentialRef
from .. import BaseCredentialProvider

log = logging.getLogger(__name__)


DEFAULT_FIELD_MAPPING: dict[str, str] = {
    "username": "username",
    "password": "password",
}
OPTIONAL_FIELD_MAPPING: dict[str, str] = {
    "pkey": "pkey",
}



class VaultKvConfig(BaseModel):
    """Global Vault configuration loaded from config.yaml."""

    addr: HttpUrl | None = Field(default=None, description="Vault address, e.g., http://vault:8200")
    token: str | None = Field(default=None, description="Token for Vault authentication")
    role_id: str | None = Field(default=None, description="AppRole role_id")
    secret_id: str | None = Field(default=None, description="AppRole secret_id")
    namespace: str | None = Field(default=None, description="Default Vault namespace")
    verify: bool | str = Field(
        default=True, description="TLS verification flag or CA bundle path (VAULT_CACERT)"
    )
    allowed_paths: list[str] = Field(
        default_factory=list,
        description="Allowed path prefixes (mount/path). Empty list disables restriction.",
    )
    cache_ttl: int = Field(
        default=30, ge=0, le=3600, description="Secret cache TTL in seconds (0 disables cache)"
    )

    model_config = ConfigDict(extra="forbid")

    @field_validator("allowed_paths", mode="before")
    @classmethod
    def _normalize_allowed_paths(cls, value):
        if value is None:
            return []
        if isinstance(value, str):
            value = value.split(",")
        return [v.strip().strip("/") for v in value if v and str(v).strip()]

    @model_validator(mode="after")
    def _validate_core(self):
        if not self.addr:
            raise ValueError("Vault address 'addr' must be configured (or set via VAULT_ADDR)")

        if not self.token and not (self.role_id and self.secret_id):
            raise ValueError("Vault auth requires token or AppRole (role_id + secret_id)")

        return self


class VaultCredentialSettings(BaseModel):
    """Per-request credential reference."""

    ref: str = Field(..., description="Secret path inside the mount")
    mount: str = Field(default="kv", description="Vault KV v2 mount point")
    version: int | None = Field(default=None, ge=1, description="Secret version (KV v2)")
    namespace: str | None = Field(default=None, description="Namespace override for this request")
    field_mapping: dict[str, str] = Field(
        default_factory=dict,
        description="Mapping from connection_arg name -> secret field name",
    )

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def _ensure_mapping(self):
        if not self.field_mapping:
            self.field_mapping = DEFAULT_FIELD_MAPPING.copy()
        return self

    @field_validator("field_mapping")
    @classmethod
    def _validate_mapping(cls, value):
        for dest, src in value.items():
            if not isinstance(dest, str) or not dest:
                raise ValueError("field_mapping keys must be non-empty strings")
            if not isinstance(src, str) or not src:
                raise ValueError("field_mapping values must be non-empty strings")
        return value


class VaultKvCredentialProvider(BaseCredentialProvider):
    credential_name: str = "vault_kv"

    _cache: ClassVar[
        dict[tuple[Optional[str], str, str, Optional[int]], tuple[float, dict[str, Any]]]
    ] = {}
    L1_CACHE_TTL: ClassVar[int] = 10  # Hardware local cache for 10 seconds

    def __init__(self, cfg: VaultCredentialSettings, client_cfg: VaultKvConfig):
        self.cfg = cfg
        self.client_cfg = client_cfg
        self.namespace = self.cfg.namespace or self.client_cfg.namespace

        self._assert_allowed_path()
        self._client = self._build_client()

    @classmethod
    def from_credential_ref(cls, ref: CredentialRef, plugin_cfg) -> "VaultKvCredentialProvider":
        if hvac is None:
            raise ImportError(
                "hvac is required for vault_kv credential provider. "
                "Install with `pip install hvac`."
            )

        try:
            cfg = VaultCredentialSettings.model_validate(
                ref.model_dump(exclude={"name"}, exclude_none=True)
            )
        except ValidationError as exc:  # pragma: no cover - validated in runtime
            raise ValueError(f"Invalid vault_kv credential reference: {exc}") from exc

        client_cfg = cls._load_client_config(plugin_cfg)
        return cls(cfg=cfg, client_cfg=client_cfg)

    @staticmethod
    def _load_client_config(plugin_cfg) -> VaultKvConfig:
        """
        Validate config.yaml credential section.
        """
        dumped: dict[str, Any] = {}
        if plugin_cfg is not None:
            dumped = plugin_cfg.model_dump(exclude={"enabled", "name"}, exclude_none=True)

        # Load token from environment variable if not in config
        import os

        if "token" not in dumped and (token := os.getenv("NETPULSE_VAULT_TOKEN")):
            dumped["token"] = token
        if "role_id" not in dumped and (role_id := os.getenv("NETPULSE_VAULT_ROLE_ID")):
            dumped["role_id"] = role_id
        if "secret_id" not in dumped and (secret_id := os.getenv("NETPULSE_VAULT_SECRET_ID")):
            dumped["secret_id"] = secret_id

        return VaultKvConfig.model_validate(dumped)

    def resolve(self, req: Any, conn_args: DriverConnectionArgs) -> DriverConnectionArgs:
        secret = self._read_secret()
        updates = self._extract_updates(secret)
        return conn_args.model_copy(update=updates, deep=True)

    def _build_client(self):
        client = hvac.Client(  # type: ignore
            url=str(self.client_cfg.addr),
            token=self.client_cfg.token,
            namespace=self.namespace,
            verify=self.client_cfg.verify,
        )

        if not client.is_authenticated():
            if self.client_cfg.role_id and self.client_cfg.secret_id:
                client.auth.approle.login(
                    role_id=self.client_cfg.role_id,
                    secret_id=self.client_cfg.secret_id,
                )

        if not client.is_authenticated():
            raise ValueError("Vault authentication failed (token or AppRole not accepted)")

        return client

    def _read_secret(self) -> dict[str, Any]:
        params = (self.namespace, self.cfg.mount, self.cfg.ref, self.cfg.version)
        cache_ttl = self.client_cfg.cache_ttl

        # 1. L1 Cache Check (Memory - Very Fast)
        if cache_ttl > 0:
            cached_l1 = self._cache.get(params)
            if cached_l1 and cached_l1[0] > time.time():
                return cached_l1[1]

        # 2. L2 Cache Check (Redis - Distributed)
        ns = self.namespace or "default"
        ver = self.cfg.version or "latest"
        redis_key = f"netpulse:cache:vault:{ns}:{self.cfg.mount}:{self.cfg.ref}:{ver}"

        if cache_ttl > 0:
            try:
                cached_l2 = g_rdb.conn.get(redis_key)
                if cached_l2:
                    data = json.loads(cached_l2)
                    # Sync to L1
                    self._cache[params] = (time.time() + self.L1_CACHE_TTL, data)
                    return data
            except Exception as e:
                log.warning(f"Vault L2 Cache access failed, falling back to direct fetch: {e}")

        # 3. Direct Fetch from Vault
        try:
            response = self._client.secrets.kv.v2.read_secret_version(
                mount_point=self.cfg.mount,
                path=self.cfg.ref,
                version=self.cfg.version,
            )
        except Exception as exc:
            log.error(
                "Failed to read secret from Vault (mount=%s, path=%s, version=%s): %s",
                self.cfg.mount,
                self.cfg.ref,
                self.cfg.version,
                exc,
            )
            raise

        data = response.get("data", {}).get("data", {})
        if not isinstance(data, dict) or not data:
            raise ValueError("Secret payload is empty or invalid")

        # 4. Populate Caches
        if cache_ttl > 0:
            # Populate L1
            self._cache[params] = (time.time() + self.L1_CACHE_TTL, data)
            # Populate L2 (Redis)
            try:
                g_rdb.conn.setex(redis_key, cache_ttl, json.dumps(data))
            except Exception as e:
                log.warning(f"Failed to populate Vault L2 Cache (Redis): {e}")

        return data

    def _extract_updates(self, secret: dict[str, Any]) -> dict[str, Any]:
        updates: dict[str, Any] = {}
        missing: list[str] = []

        # Check mandatory/explicit mapping
        for dest, source in self.cfg.field_mapping.items():
            if source in secret and secret.get(source) is not None:
                updates[dest] = secret.get(source)
            else:
                missing.append(source)

        if missing:
            raise ValueError(f"Missing required secret fields: {', '.join(missing)}")

        # Check optional default mapping (only if not explicitly overridden)
        # Actually, if the user didn't provide any mapping, we also try optional ones
        # but don't fail if they are missing.
        # Check if we are using default mapping
        if self.cfg.field_mapping == DEFAULT_FIELD_MAPPING:
            for dest, source in OPTIONAL_FIELD_MAPPING.items():
                if source in secret and secret.get(source) is not None:
                    updates[dest] = secret.get(source)

        return updates

    def _assert_allowed_path(self) -> None:
        if not self.client_cfg.allowed_paths:
            return

        full_path = f"{self.cfg.mount.strip('/')}/{self.cfg.ref.strip('/')}"
        for prefix in self.client_cfg.allowed_paths:
            if full_path.startswith(prefix):
                return

        raise ValueError(f"Access to Vault path '{full_path}' is not allowed by policy")


__all__ = ["VaultKvCredentialProvider"]
