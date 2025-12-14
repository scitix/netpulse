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
