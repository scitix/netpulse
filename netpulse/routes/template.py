import logging
from typing import Optional

from fastapi import APIRouter, HTTPException

from ..models.request import TemplateParseRequest, TemplateRenderRequest
from ..models.response import BaseResponse
from ..plugins import parsers, renderers

log = logging.getLogger(__name__)

router = APIRouter(prefix="/template", tags=["template"])


# Render
@router.post("/render", response_model=BaseResponse)
@router.post("/render/{name}", response_model=BaseResponse)
def render_template(req: TemplateRenderRequest, name: Optional[str] = None):
    if name:
        req.name = name

    if not req.name:
        raise ValueError("Renderer name is required")

    if not req.template:
        raise HTTPException(status_code=400, detail="Template source is required")

    try:
        robj = renderers[req.name].from_rendering_request(req)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Renderer {req.name} not found")

    data = robj.render(req.context)
    return BaseResponse(code=200, message="success", data=data)


# Parse
@router.post("/parse", response_model=BaseResponse)
@router.post("/parse/{name}", response_model=BaseResponse)
def parse_template(req: TemplateParseRequest, name: Optional[str] = None):
    if name:
        req.name = name

    if not req.name:
        raise ValueError("Parser name is required")

    try:
        pobj = parsers[req.name].from_parsing_request(req)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Parser {req.name} not found")

    data = pobj.parse(req.context)
    return BaseResponse(code=200, message="success", data=data)
