import logging
import os
from pathlib import Path
from typing import Optional

from pydantic import (
    BaseModel,
    ConfigDict,
    DirectoryPath,
    Field,
    FilePath,
    ValidationError,
    model_validator,
)
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
    external_url: Optional[str] = None  # e.g., http://netpulse.example.com:9000
    api_key: str = Field(..., description="API key")
    api_key_name: str = "X-API-KEY"
    gunicorn_worker: int = Field(default_factory=lambda: 2 * os.cpu_count() + 1)  # type: ignore


class JobConfig(BaseModel):
    ttl: int = 1800
    timeout: int = 300
    result_ttl: int = 300


class WorkerConfig(BaseModel):
    scheduler: str = "least_load"
    ttl: int = 300
    pinned_per_node: int = 32


class CredentialConfig(BaseModel):
    enabled: bool = False
    name: str | None = None

    model_config = ConfigDict(extra="allow")


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


class PluginConfig(BaseModel):
    driver: DirectoryPath = Path("netpulse/plugins/drivers/")
    webhook: DirectoryPath = Path("netpulse/plugins/webhooks/")
    template: DirectoryPath = Path("netpulse/plugins/templates/")
    scheduler: DirectoryPath = Path("netpulse/plugins/schedulers/")
    credential: DirectoryPath = Path("netpulse/plugins/credentials/")


class LogConfig(BaseModel):
    config: FilePath = Path("config/log-config.yaml")
    level: str = "INFO"


class StorageConfig(BaseModel):
    staging: Path = Path("/app/storage/staging")


class AppConfig(BaseSettings):
    # Must be provided fields
    server: ServerConfig
    worker: WorkerConfig
    redis: RedisConfig
    plugin: PluginConfig
    storage: StorageConfig = StorageConfig()

    # With default values
    job: JobConfig = JobConfig()
    log: LogConfig = LogConfig()
    credential: CredentialConfig = CredentialConfig()

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


def initialize_config() -> AppConfig:
    try:
        return AppConfig()  # type: ignore
    except ValidationError as e:
        log.error(f"Error in reading config: {e}")
        raise e
