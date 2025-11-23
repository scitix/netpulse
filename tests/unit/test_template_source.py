import types
from typing import Any

import pytest

from netpulse.plugins.templates import TemplateSource


def test_template_source_string():
    src = TemplateSource("interface Gi0/1")
    assert src.load() == "interface Gi0/1"


def test_template_source_file(tmp_path):
    tpl = tmp_path / "tpl.txt"
    tpl.write_text("hostname router")

    src = TemplateSource(f"file://{tpl}")
    assert src.load() == "hostname router"


def test_template_source_http(monkeypatch: pytest.MonkeyPatch):
    calls: dict[str, Any] = {}

    class DummyResponse:
        def __init__(self, text: str):
            self.text = text

        def raise_for_status(self) -> None:
            calls["raised"] = True

    def fake_get(url: str) -> "DummyResponse":
        calls["url"] = url
        return DummyResponse(text="from http")

    monkeypatch.setattr("netpulse.plugins.templates.requests.get", fake_get)

    src = TemplateSource("http://example.com/template")
    assert src.load() == "from http"
    assert calls["url"] == "http://example.com/template"
    assert calls["raised"] is True


def test_template_source_ftp(monkeypatch: pytest.MonkeyPatch):
    class DummyFTP(types.SimpleNamespace):
        def __enter__(self) -> "DummyFTP":
            return self

        def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
            return False

    def fake_urlopen(url: str) -> DummyFTP:
        return DummyFTP(read=lambda: b"from ftp")

    monkeypatch.setattr("netpulse.plugins.templates.urllib.request.urlopen", fake_urlopen)

    src = TemplateSource("ftp://example.com/template")
    assert src.load() == "from ftp"
