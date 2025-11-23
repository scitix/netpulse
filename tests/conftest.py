import importlib
import os
from pathlib import Path
from typing import Iterator

import pytest

# Ensure the app loads test settings and uses fakeredis before importing NetPulse
BASE_DIR = Path(__file__).parent
TEST_CONFIG = BASE_DIR / "data" / "config.test.yaml"

os.environ.setdefault("NETPULSE_CONFIG_FILE", str(TEST_CONFIG))
os.environ.setdefault("NETPULSE_SERVER__API_KEY", "TEST_API_KEY")
os.environ.setdefault("NETPULSE_REDIS__PASSWORD", "test")
os.environ.setdefault("NETPULSE_FAKE_REDIS", "1")


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
