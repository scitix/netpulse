from pydantic import BaseModel, Field

from ....models.request import TemplateRenderRequest


class Jinja2Args(BaseModel):
    """From Jinja2 environment.py"""

    block_start_string: str | None = None
    block_end_string: str | None = None
    variable_start_string: str | None = None
    variable_end_string: str | None = None
    comment_start_string: str | None = None
    comment_end_string: str | None = None
    line_statement_prefix: str | None = None
    line_comment_prefix: str | None = None
    trim_blocks: bool | None = None
    lstrip_blocks: bool | None = None
    newline_sequence: str | None = None
    keep_trailing_newline: bool | None = None


class Jinja2RenderRequest(TemplateRenderRequest):
    name: str = "jinja2"

    args: Jinja2Args | None = Field(
        default=None,
        title="Jinja2 Template class arguments",
        description="Template class __init__ arguments",
    )
