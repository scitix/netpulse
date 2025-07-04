from typing import Optional

from pydantic import BaseModel, Field

from ....models.request import TemplateParseRequest


class TextFSMNtcArgs(BaseModel):
    """From ntc_templates parse.py"""

    platform: str = Field(
        ...,
        title="Platform",
        description="The platform of the device (same as netmiko's `device type`)",
    )

    command: str = Field(
        ...,
        title="Command",
        description="The command to parse",
    )


class TextFSMParseRequest(TemplateParseRequest):
    name: str = "textfsm"

    template: Optional[str] = Field(
        None,
        title="Template source",
        description="URI of the template source. Default: plain text. \
            Ignored if `use_ntc_template` is set.",
    )

    use_ntc_template: Optional[bool] = Field(
        False,
        title="Use NTC templates",
        description="Use NTC templates for parsing",
    )

    ntc_template_args: Optional[TextFSMNtcArgs] = Field(
        None,
        title="NTC templates arguments",
        description="NTC templates arguments (see ntc_template)",
    )
