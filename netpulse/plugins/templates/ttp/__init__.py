import logging

from ttp.ttp import ttp as TTPParser
from ttp_templates import parse_output

from .. import BaseTemplateParser, TemplateSource
from .model import TTPParseRequest, TTPTemplateArgs

log = logging.getLogger(__name__)


class TTPTemplateParser(BaseTemplateParser):
    template_name = "ttp"

    @classmethod
    def from_parsing_request(cls, req: TTPParseRequest) -> "TTPTemplateParser":
        if not isinstance(req, TTPParseRequest):
            req = TTPParseRequest.model_validate(req.model_dump())
        return cls(
            source=req.template,
            use_ttp=req.use_ttp_template,
            ttp_args=req.ttp_template_args,
        )

    def __init__(self, source: str, use_ttp: bool = False, ttp_args: TTPTemplateArgs = None):
        self.use_ttp = use_ttp
        self.ttp_args = ttp_args

        if not use_ttp:
            try:
                s = TemplateSource(source)
                s = s.load()
            except Exception as e:
                log.error(f"Error in loading template from {source}: {e}")
                raise e

            if s is None or len(s) == 0:
                log.error(f"Error in building template from {source}: Empty template")
                raise ValueError("Empty template")

            self.template = s

    def _ttp_template_parse(self, context: str) -> dict:
        return parse_output(
            data=context,
            platform=self.ttp_args.platform,
            command=self.ttp_args.command,
            structure="dictionary",
        )

    def _parse(self, context: str) -> dict:
        try:
            parser = TTPParser(data=context, template=self.template)
            parser.parse()
        except Exception as e:
            log.error(f"Error in parsing template: {e}")
            raise e

        return parser.result(structure="dictionary")

    def parse(self, context: str) -> dict:
        try:
            return self._ttp_template_parse(context) if self.use_ttp else self._parse(context)
        except Exception as e:
            log.error(f"Error in parsing template: {e}")
            raise e


__all__ = ["TTPTemplateParser"]
