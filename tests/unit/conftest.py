import importlib
from typing import Iterator

import pytest


@pytest.fixture(scope="session")
def app_config():
    """
    Load NetPulse modules with the test configuration and fakeredis.
    """
    from netpulse import utils
    from netpulse.services import manager, rediz

    importlib.reload(utils)
    importlib.reload(rediz)
    importlib.reload(manager)
    return utils.g_config


@pytest.fixture()
def fake_redis_conn(app_config) -> Iterator:
    from netpulse.services import rediz

    conn = rediz.g_rdb.conn
    conn.flushall()
    try:
        yield conn
    finally:
        conn.flushall()
