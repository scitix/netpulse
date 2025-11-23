from netpulse import utils
from netpulse.services import rediz


def test_test_config_loaded(app_config, fake_redis_conn):
    assert utils.g_config.server.api_key == "TEST_API_KEY"
    assert utils.g_config.redis.tls.enabled is False
    assert rediz.g_rdb.conn is fake_redis_conn
    # fakeredis should respond to ping without a real Redis server
    assert fake_redis_conn.ping() is True
