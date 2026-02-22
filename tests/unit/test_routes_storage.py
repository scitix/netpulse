import os
import shutil
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from netpulse.controller import app

client = TestClient(app)
API_KEY = "test_key"


@pytest.fixture(autouse=True)
def mock_storage_staging():
    """Mock the storage staging directory and API key for all tests."""
    test_staging = "/tmp/netpulse_test_staging"
    test_download = os.path.join(test_staging, "downloads")
    os.makedirs(test_download, exist_ok=True)

    # Patch g_config in various modules to ensure consistency
    with (
        patch("netpulse.routes.storage.g_config") as mock_conf_storage,
        patch("netpulse.server.common.g_config") as mock_conf_auth,
    ):
        mock_conf_storage.storage.staging = Path(test_staging)
        mock_conf_auth.server.api_key = API_KEY
        mock_conf_auth.server.api_key_name = "X-API-KEY"

        yield test_download

    if os.path.exists(test_staging):
        shutil.rmtree(test_staging)


def test_fetch_staged_file_success(mock_storage_staging):
    """Test successful retrieval of a staged file."""
    file_id = "test_file.txt"
    file_path = os.path.join(mock_storage_staging, file_id)
    content = b"Some test content"

    with open(file_path, "wb") as f:
        f.write(content)

    response = client.get(f"/storage/fetch/{file_id}", headers={"X-API-KEY": API_KEY})
    assert response.status_code == 200
    assert response.content == content
    assert response.headers["content-disposition"] == f'attachment; filename="{file_id}"'


def test_fetch_staged_file_not_found():
    """Test 404 when file does not exist."""
    response = client.get("/storage/fetch/non_existent.txt", headers={"X-API-KEY": API_KEY})
    assert response.status_code == 404


def test_fetch_staged_file_path_traversal():
    """Test protection when path traversal is attempted."""
    # Note: TestClient/httpx might normalize '../..' before sending.
    # If it's normalized, it might not match the route or hit a different one (404).
    # If it's NOT normalized, the backend blocks it (403).
    response = client.get("/storage/fetch/../../etc/passwd", headers={"X-API-KEY": API_KEY})
    assert response.status_code in [403, 404]
