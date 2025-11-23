from netpulse.plugins.templates.jinja2 import Jinja2Renderer
from netpulse.plugins.templates.jinja2.model import Jinja2RenderRequest
from netpulse.plugins.templates.textfsm import TextFSMTemplateParser
from netpulse.plugins.templates.textfsm.model import TextFSMParseRequest
from netpulse.plugins.templates.ttp import TTPTemplateParser
from netpulse.plugins.templates.ttp.model import TTPParseRequest


def test_jinja2_renderer_renders_context():
    renderer = Jinja2Renderer.from_rendering_request(
        Jinja2RenderRequest(template="hello {{ name }}")
    )
    assert renderer.render({"name": "world"}) == "hello world"


def test_textfsm_parser_parses_custom_template():
    template = """Value HOST (\\S+)
Value UPTIME (.+)

Start
  ^Host: ${HOST}, Uptime: ${UPTIME} -> Record
"""
    parser = TextFSMTemplateParser.from_parsing_request(TextFSMParseRequest(template=template))
    result = parser.parse("Host: R1, Uptime: 5d")
    assert result == [{"HOST": "R1", "UPTIME": "5d"}]


def test_ttp_parser_parses_inline_template():
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
