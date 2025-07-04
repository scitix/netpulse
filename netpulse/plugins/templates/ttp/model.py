from typing import Optional

from pydantic import BaseModel, Field

from ....models.request import TemplateParseRequest


class TTPTemplateArgs(BaseModel):
    """
    From ttp_templates parse_output.py
    """

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


class TTPParseRequest(TemplateParseRequest):
    name: str = "ttp"

    template: Optional[str] = Field(
        None,
        title="Template source",
        description="URI of the template source. Default: plain text. \
            Ignored if `use_ttp_template` is set.",
    )

    use_ttp_template: Optional[bool] = Field(
        False,
        title="Use templates from ttp_templates",
        description="Use templates from ttp_templates",
    )

    ttp_template_args: Optional[TTPTemplateArgs] = Field(
        None,
        title="TTP templates `parse_output` arguments",
        description="TTP templates `parse_output` arguments (see ttp_template)",
    )
