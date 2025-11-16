import logging
import os
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, DirectoryPath, Field, FilePath, ValidationError, model_validator
from pydantic_settings import (
    BaseSettings,
    SettingsConfigDict,
    YamlConfigSettingsSource,
)

log = logging.getLogger(__name__)
CONFIG_PATH = "config/config.yaml"


class ServerConfig(BaseModel):
    host: str = "0.0.0.0"
    port: int = 9000
    api_key: str = Field(..., description="API key")
    api_key_name: str = "X-API-KEY"
    gunicorn_worker: int = Field(default_factory=lambda: 2 * os.cpu_count() + 1)


class JobConfig(BaseModel):
    ttl: int = 1800
    timeout: int = 300
    result_ttl: int = 300


class WorkerConfig(BaseModel):
    scheduler: str = "least_load"
    ttl: int = 300
    pinned_per_node: int = 32


class RedisConfig(BaseModel):
    class RedisTLSConfig(BaseModel):
        enabled: bool = False
        ca: Optional[Path] = None
        cert: Optional[Path] = None
        key: Optional[Path] = None
        # NOTE: Don't use FilePath. It will check for existence even if enabled is False

        @model_validator(mode="after")
        def _check_paths(self):
            if self.enabled:
                for name in ("ca", "cert", "key"):
                    value: Optional[Path] = getattr(self, name)
                    if value is None or not value.is_file():
                        raise ValueError(f"{name} must be an existing file when TLS is enabled")
            return self

    class RedisKeyConfig(BaseModel):
        host_to_node_map: str = "netpulse:host_to_node_map"
        node_info_map: str = "netpulse:node_info_map"

    class RedisSentinelConfig(BaseModel):
        enabled: bool = False
        host: str = "redis-sentinel"
        port: int = 26379
        master_name: str = "mymaster"
        password: Optional[str] = None

    host: str = "localhost"
    port: int = 6379
    password: Optional[str] = None
    timeout: int = 30
    keepalive: int = 30
    tls: RedisTLSConfig = RedisTLSConfig()
    sentinel: RedisSentinelConfig = RedisSentinelConfig()
    key: RedisKeyConfig = RedisKeyConfig()


class VaultConfig(BaseSettings):

    """Vault configuration."""

    url: str = Field(..., description="Vault server URL")
    token: str = Field(..., description="Vault access token, supports env var ${VAULT_TOKEN}")
    mount_point: str = Field("secret", description="KV store mount point")
    timeout: int = Field(30, description="Connection timeout in seconds")

    model_config = SettingsConfigDict(
        env_prefix="NETPULSE__CREDENTIAL__VAULT__",
        env_nested_delimiter="__",
    )


class CredentialConfig(BaseSettings):
    """Credential plugin configuration."""

    vault: Optional[VaultConfig] = None

    model_config = SettingsConfigDict(
        env_prefix="NETPULSE__CREDENTIAL__",
        env_nested_delimiter="__",
    )


class PluginConfig(BaseModel):
    driver: DirectoryPath = Path("netpulse/plugins/drivers/")
    webhook: DirectoryPath = Path("netpulse/plugins/webhooks/")
    template: DirectoryPath = Path("netpulse/plugins/templates/")
    scheduler: DirectoryPath = Path("netpulse/plugins/schedulers/")
    credential: DirectoryPath = Path("netpulse/plugins/credentials/")


class LogConfig(BaseModel):
    config: FilePath = Path("config/log-config.yaml")
    level: str = "INFO"


class AppConfig(BaseSettings):
    server: ServerConfig
    worker: WorkerConfig
    redis: RedisConfig
    plugin: PluginConfig
    credential: Optional[CredentialConfig] = None
    # With default values
    job: JobConfig = JobConfig()
    log: LogConfig = LogConfig()

    model_config = SettingsConfigDict(
        env_prefix="NETPULSE_",
        env_nested_delimiter="__",
        yaml_file=os.getenv("NETPULSE_CONFIG_FILE", CONFIG_PATH),
    )

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls,
        init_settings,
        env_settings,
        dotenv_settings,
        file_secret_settings,
    ):
        """Read settings: env -> dotenv -> yaml -> default"""
        return (
            env_settings,
            dotenv_settings,
            YamlConfigSettingsSource(settings_cls),
            init_settings,
        )

    @staticmethod
    def get_host_queue_name(host: str) -> str:
        return f"HostQ_{host}"

    @staticmethod
    def get_node_queue_name(node: str) -> str:
        return f"NodeQ_{node}"

    @staticmethod
    def get_fifo_queue_name() -> str:
        return "FifoQ"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Auto-create CredentialConfig from environment if vault env vars are present
        if self.credential is None:
            # Check if vault environment variables are set
            vault_url = os.getenv("NETPULSE__CREDENTIAL__VAULT__URL")
            vault_token = os.getenv("NETPULSE__CREDENTIAL__VAULT__TOKEN") or os.getenv("VAULT_TOKEN")
            if vault_url and vault_token:
                try:
                    vault_config = VaultConfig(
                        url=vault_url,
                        token=vault_token,
                        mount_point=os.getenv("NETPULSE__CREDENTIAL__VAULT__MOUNT_POINT", "secret"),
                        timeout=int(os.getenv("NETPULSE__CREDENTIAL__VAULT__TIMEOUT", "30")),
                    )
                    self.credential = CredentialConfig(vault=vault_config)
                except Exception as e:
                    log.warning(f"Failed to create Vault config from environment: {e}")
                    # If Vault config creation fails, leave credential as None
                    pass


def initialize_config() -> AppConfig:
    try:
        config = AppConfig()
        # Auto-create CredentialConfig from environment if vault env vars are present
        if config.credential is None:
            # Check if vault environment variables are set
            vault_url = os.getenv("NETPULSE__CREDENTIAL__VAULT__URL")
            vault_token = os.getenv("NETPULSE__CREDENTIAL__VAULT__TOKEN") or os.getenv("VAULT_TOKEN")
            if vault_url and vault_token:
                try:
                    vault_config = VaultConfig(
                        url=vault_url,
                        token=vault_token,
                        mount_point=os.getenv("NETPULSE__CREDENTIAL__VAULT__MOUNT_POINT", "secret"),
                        timeout=int(os.getenv("NETPULSE__CREDENTIAL__VAULT__TIMEOUT", "30")),
                    )
                    config.credential = CredentialConfig(vault=vault_config)
                    log.info("Vault configuration loaded from environment variables")
                except Exception as e:
                    log.warning(f"Failed to create Vault config from environment: {e}")
                    import traceback
                    log.debug(traceback.format_exc())
        return config
    except ValidationError as e:
        log.error(f"Error in reading config: {e}")
        raise e
