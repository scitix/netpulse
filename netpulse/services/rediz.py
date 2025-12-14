import logging
import os

from redis.sentinel import Sentinel

from redis import Redis

from ..utils import g_config
from ..utils.config import RedisConfig

log = logging.getLogger(__name__)


def _fake_redis_enabled() -> bool:
    """
    Treat NETPULSE_FAKE_REDIS as a boolean flag; values like "1/true/yes/on"
    enable fakeredis, anything else is considered disabled.
    """
    value = os.getenv("NETPULSE_FAKE_REDIS", "").strip().lower()
    return value in {"1", "true", "yes", "on"}


class Rediz:
    def __init__(self, config: RedisConfig):
        self.config = config

        # Use fakeredis for tests when requested
        if _fake_redis_enabled():
            try:
                import fakeredis
            except ImportError as e:
                raise ImportError(
                    "NETPULSE_FAKE_REDIS is set but fakeredis is not installed. "
                    "Install fakeredis or unset NETPULSE_FAKE_REDIS."
                ) from e

            log.info("[USING FAKEREDIS MODE]")
            self.conn = fakeredis.FakeRedis()
            return

        # Using Sentinel for connection
        if config.sentinel.enabled:
            log.info("[USING REDIS SENTINEL MODE]")
            log.info(f"Sentinel server: {config.sentinel.host}:{config.sentinel.port}")
            log.info(f"Sentinel Master name: '{config.sentinel.master_name}'")
            log.info(f"TLS encryption: {'Enabled' if config.tls.enabled else 'Disabled'}")

            sentinel = Sentinel(
                [(config.sentinel.host, config.sentinel.port)],
                socket_timeout=config.timeout,
                password=config.sentinel.password,
                sentinel_kwargs={
                    "password": config.sentinel.password,
                    "socket_timeout": config.timeout,
                },
            )

            # Try to discover master node information from Sentinel
            try:
                master_info = sentinel.discover_master(config.sentinel.master_name)
                log.info(f"Discovered Redis master node: {master_info[0]}:{master_info[1]}")
            except Exception as e:
                log.error(f"Unable to discover master node from Sentinel: {e!s}")

            # Try to discover all slave nodes
            try:
                slave_nodes = sentinel.discover_slaves(config.sentinel.master_name)
                log.info(f"Discovered {len(slave_nodes)} Redis slave nodes:")
                for i, slave in enumerate(slave_nodes, 1):
                    log.info(f"  Slave #{i}: {slave[0]}:{slave[1]}")
            except Exception as e:
                log.error(f"Unable to discover slave nodes from Sentinel: {e!s}")

            # Connect to master node
            if config.tls.enabled:
                log.info("Connecting to Redis master node with TLS encryption")
                master = sentinel.master_for(
                    config.sentinel.master_name,
                    socket_timeout=config.timeout,
                    password=config.password,
                    ssl=True,
                    ssl_cert_reqs="required",
                    ssl_ca_certs=config.tls.ca,
                    ssl_certfile=config.tls.cert,
                    ssl_keyfile=config.tls.key,
                    socket_keepalive=config.keepalive,
                    retry_on_timeout=True,
                    retry_on_error=[ConnectionError],
                )
            else:
                log.info("Connecting to Redis master node without encryption")
                master = sentinel.master_for(
                    config.sentinel.master_name,
                    socket_timeout=config.timeout,
                    password=config.password,
                    socket_keepalive=config.keepalive,
                    retry_on_timeout=True,
                    retry_on_error=[ConnectionError],
                )

            self.conn = master

            # Verify connection success
            try:
                ping_result = self.conn.ping()
                log.info(
                    f"Redis master node connection test: "
                    f"{'Successful' if ping_result else 'Failed'}"
                )
            except Exception as e:
                log.error(f"Redis master node connection failed: {e!s}")

        # Using direct connection mode
        else:
            log.info("[USING DIRECT REDIS CONNECTION MODE]")
            log.info(f"Redis server: {config.host}:{config.port}")
            log.info(f"TLS encryption: {'Enabled' if config.tls.enabled else 'Disabled'}")
            log.info(
                f"Timeout setting: {config.timeout}s, "
                f"Keep alive: {'Yes' if config.keepalive else 'No'}"
            )

            if config.tls.enabled:
                log.info("Connecting to Redis with TLS encryption")
                self.conn = Redis(
                    host=config.host,
                    port=config.port,
                    password=config.password,
                    ssl=True,
                    ssl_cert_reqs="required",
                    ssl_ca_certs=config.tls.ca,
                    ssl_certfile=config.tls.cert,
                    ssl_keyfile=config.tls.key,
                    socket_connect_timeout=config.timeout,
                    socket_keepalive=config.keepalive,
                    retry_on_timeout=True,
                    retry_on_error=[ConnectionError],
                )
            else:
                log.info("Connecting to Redis without encryption")
                self.conn = Redis(
                    host=config.host,
                    port=config.port,
                    password=config.password,
                    socket_connect_timeout=config.timeout,
                    socket_keepalive=config.keepalive,
                    retry_on_timeout=True,
                    retry_on_error=[ConnectionError],
                )

            # Verify connection success
            try:
                ping_result = self.conn.ping()
                log.info(f"Redis connection test: {'Successful' if ping_result else 'Failed'}")
            except Exception as e:
                log.error(f"Redis connection failed: {e!s}")


g_rdb = Rediz(g_config.redis)
