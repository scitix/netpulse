import logging

from jinja2 import Template

from .. import BaseTemplateRenderer, TemplateSource
from .model import Jinja2Args, Jinja2RenderRequest

log = logging.getLogger(__name__)


class Jinja2Renderer(BaseTemplateRenderer):
    template_name = "jinja2"

    @classmethod
    def from_rendering_request(cls, req: Jinja2RenderRequest):
        if not isinstance(req, Jinja2RenderRequest):
            # Python don't have implicit type conversion
            req = Jinja2RenderRequest.model_validate(req.model_dump())
        return cls(source=req.template, options=req.args)

    def __init__(self, source: str, options: Jinja2Args = None):
        options: dict = options.model_dump() if options else {}

        try:
            source: TemplateSource = TemplateSource(source)
            options["source"] = source.load()
        except Exception as e:
            log.error(f"Error in loading template from {source}: {e}")
            raise e

        self.template = Template(**options)

    def render(self, context: dict | None) -> str:
        """
        Render a template string with context
        """
        if context is None:
            context = {}

        try:
            rendered = self.template.render(**context)
        except Exception as e:
            log.error(f"Error in rendering template: {e}")
            raise e

        return rendered


__all__ = ["Jinja2Renderer"]
