from typing import Optional

from pydantic import BaseModel, Field

from ....models.request import TemplateRenderRequest


class Jinja2Args(BaseModel):
    """From Jinja2 environment.py"""

    block_start_string: Optional[str] = None
    block_end_string: Optional[str] = None
    variable_start_string: Optional[str] = None
    variable_end_string: Optional[str] = None
    comment_start_string: Optional[str] = None
    comment_end_string: Optional[str] = None
    line_statement_prefix: Optional[str] = None
    line_comment_prefix: Optional[str] = None
    trim_blocks: Optional[bool] = None
    lstrip_blocks: Optional[bool] = None
    newline_sequence: Optional[str] = None
    keep_trailing_newline: Optional[bool] = None


class Jinja2RenderRequest(TemplateRenderRequest):
    name: str = "jinja2"

    args: Optional[Jinja2Args] = Field(
        None,
        title="Jinja2 Template class arguments",
        description="Template class __init__ arguments",
    )
