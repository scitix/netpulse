import io
import logging

from ntc_templates import parse
from textfsm import TextFSM

from .. import BaseTemplateParser, TemplateSource
from .model import (
    TextFSMNtcArgs,
    TextFSMParseRequest,
)

log = logging.getLogger(__name__)


class TextFSMTemplateParser(BaseTemplateParser):
    template_name = "textfsm"

    @classmethod
    def from_parsing_request(cls, req: TextFSMParseRequest) -> "TextFSMTemplateParser":
        if not isinstance(req, TextFSMParseRequest):
            req = TextFSMParseRequest.model_validate(req.model_dump())
        return cls(
            source=req.template,
            use_ntc=req.use_ntc_template,
            ntc_args=req.ntc_template_args,
        )

    def __init__(self, source: str, use_ntc: bool = False, ntc_args: TextFSMNtcArgs = None):
        self.use_ntc = use_ntc
        self.ntc_args = ntc_args
        self.template: TextFSM = None

        if not self.use_ntc:
            try:
                s = TemplateSource(source)
                s = s.load()
            except Exception as e:
                log.error(f"Error in loading template from {source}: {e}")
                raise e

            try:
                template_stream = io.StringIO(s)
                self.template = TextFSM(template_stream)
            except Exception as e:
                log.error(f"Error in building template from {source}: {e}")
                raise e

    def _ntc_parse(self, context: str) -> list[dict]:
        return parse.parse_output(
            platform=self.ntc_args.platform, command=self.ntc_args.command, data=context
        )

    def _template_parse(self, context: str) -> list[dict]:
        if self.template is None:
            raise ValueError("Template not loaded")

        return self.template.ParseTextToDicts(context)

    def parse(self, context: str) -> list[dict]:
        try:
            return self._ntc_parse(context) if self.use_ntc else self._template_parse(context)
        except Exception as e:
            log.error(f"Error in parsing context: {e}")
            raise e


__all__ = ["TextFSMTemplateParser"]
