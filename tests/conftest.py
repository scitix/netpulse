import os
from pathlib import Path

# Default to unit test configuration and fakeredis for all tests unless overridden.
BASE_DIR = Path(__file__).parent
TEST_CONFIG = BASE_DIR / "data" / "config.test.yaml"

os.environ.setdefault("NETPULSE_CONFIG_FILE", str(TEST_CONFIG))
os.environ.setdefault("NETPULSE_SERVER__API_KEY", "TEST_API_KEY")
os.environ.setdefault("NETPULSE_REDIS__PASSWORD", "test")
os.environ.setdefault("NETPULSE_FAKE_REDIS", "1")


def pytest_configure(config):
    config.addinivalue_line("markers", "api: API-level tests without external deps")
    config.addinivalue_line("markers", "e2e: end-to-end tests that require ContainerLab")


def pytest_addoption(parser):
    parser.addoption(
        "--e2e",
        action="store_true",
        default=False,
        help="Force-enable end-to-end tests when lab services are reachable.",
    )
    parser.addoption(
        "--no-e2e",
        action="store_true",
        default=False,
        help="Disable end-to-end tests even if lab services are reachable.",
    )
