import pytest
from fastapi import HTTPException

from netpulse.server.common import verify_api_key


def test_verify_api_key_accepts_query_header_cookie(monkeypatch, app_config):
    api_key = app_config.server.api_key
    assert verify_api_key(query_key=api_key, header_key=None, cookie_key=None) == api_key
    assert verify_api_key(query_key=None, header_key=api_key, cookie_key=None) == api_key
    assert verify_api_key(query_key=None, header_key=None, cookie_key=api_key) == api_key


def test_verify_api_key_rejects_invalid(monkeypatch, app_config):
    with pytest.raises(HTTPException):
        verify_api_key(query_key="bad", header_key=None, cookie_key=None)
