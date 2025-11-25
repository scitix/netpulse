from netpulse import utils
from netpulse.services import rediz


def test_test_config_loaded(app_config, fake_redis_conn):
    """Ensure test config, API key, and fakeredis are wired for unit tests."""
    assert utils.g_config.server.api_key == "TEST_API_KEY"
    assert utils.g_config.redis.tls.enabled is False
    assert rediz.g_rdb.conn is fake_redis_conn
    # fakeredis should respond to ping without a real Redis server
    assert fake_redis_conn.ping() is True


def test_config_loads_from_yaml_and_env_override(tmp_path, runtime_loader):
    """
    Config should read from YAML, then allow NETPULSE_ env overrides.
    """
    cfg_file = tmp_path / "config.yaml"
    cfg_file.write_text(
        """
    server:
      host: 1.2.3.4
      port: 9001
      api_key: YAML_KEY
    worker:
      scheduler: greedy
      ttl: 120
      pinned_per_node: 8
    redis:
      host: yaml-redis
      port: 6380
      password: yaml-pass
      tls:
        enabled: false
    plugin:
      driver: netpulse/plugins/drivers
      webhook: netpulse/plugins/webhooks
      template: netpulse/plugins/templates
      scheduler: netpulse/plugins/schedulers
    """
    )

    # Provide dummy TLS paths so validation passes when enabling TLS
    ca_path = tmp_path / "ca.crt"
    cert_path = tmp_path / "redis.crt"
    key_path = tmp_path / "redis.key"
    for p in (ca_path, cert_path, key_path):
        p.write_text("dummy")

    runtime = runtime_loader(
        {
            "NETPULSE_CONFIG_FILE": str(cfg_file),
            "NETPULSE_SERVER__API_KEY": "ENV_KEY",
            "NETPULSE_REDIS__TLS__ENABLED": "1",
            "NETPULSE_REDIS__TLS__CA": str(ca_path),
            "NETPULSE_REDIS__TLS__CERT": str(cert_path),
            "NETPULSE_REDIS__TLS__KEY": str(key_path),
        }
    )
    config = runtime.config

    assert config.server.host == "1.2.3.4"
    assert config.server.port == 9001
    # env override should win over YAML
    assert config.server.api_key == "ENV_KEY"
    # nested env override should flip TLS enabled
    assert config.redis.tls.enabled is True
    assert config.redis.host == "yaml-redis"
    assert config.redis.port == 6380
    assert config.redis.tls.ca == ca_path
    assert config.redis.tls.cert == cert_path
    assert config.redis.tls.key == key_path
