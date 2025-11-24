import types
from typing import Any

import pytest

from netpulse.plugins.templates import TemplateSource
from netpulse.plugins.templates.jinja2 import Jinja2Renderer
from netpulse.plugins.templates.jinja2.model import Jinja2RenderRequest
from netpulse.plugins.templates.textfsm import TextFSMTemplateParser
from netpulse.plugins.templates.textfsm.model import TextFSMParseRequest
from netpulse.plugins.templates.ttp import TTPTemplateParser
from netpulse.plugins.templates.ttp.model import TTPParseRequest


def test_jinja2_renderer_renders_context():
    """Jinja2 renderer should render placeholders with provided context."""
    renderer = Jinja2Renderer.from_rendering_request(
        Jinja2RenderRequest(template="hello {{ name }}")
    )
    assert renderer.render({"name": "world"}) == "hello world"


def test_textfsm_parser_parses_custom_template():
    """TextFSM parser should extract values using inline template."""
    template = """Value HOST (\\S+)
Value UPTIME (.+)

Start
  ^Host: ${HOST}, Uptime: ${UPTIME} -> Record
"""
    parser = TextFSMTemplateParser.from_parsing_request(TextFSMParseRequest(template=template))
    result = parser.parse("Host: R1, Uptime: 5d")
    assert result == [{"HOST": "R1", "UPTIME": "5d"}]


def test_ttp_parser_parses_inline_template():
    """TTP parser should return structured data for inline template."""
    template = """
<group name="interfaces">
interface {{ interface }} description {{ desc }}
</group>
    """
    parser = TTPTemplateParser.from_parsing_request(TTPParseRequest(template=template))
    result = parser.parse("interface Gi0/1 description Uplink")
    assert isinstance(result, dict)
    interfaces = result["_root_template_"][0]["interfaces"]
    assert interfaces["interface"] == "Gi0/1"
    assert interfaces["desc"] == "Uplink"


def test_template_source_string():
    """TemplateSource should return raw string when given plain content."""
    src = TemplateSource("interface Gi0/1")
    assert src.load() == "interface Gi0/1"


def test_template_source_file(tmp_path):
    """TemplateSource should load content from file:// URI."""
    tpl = tmp_path / "tpl.txt"
    tpl.write_text("hostname router")

    src = TemplateSource(f"file://{tpl}")
    assert src.load() == "hostname router"


def test_template_source_http(monkeypatch: pytest.MonkeyPatch):
    """TemplateSource should fetch HTTP content via requests.get."""
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
    """TemplateSource should load bytes from FTP URL using urllib."""

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
