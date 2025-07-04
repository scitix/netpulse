import logging

from fastapi import HTTPException, Request, Security
from fastapi.responses import JSONResponse
from fastapi.security.api_key import APIKeyCookie, APIKeyHeader, APIKeyQuery
from pydantic import ValidationError
from starlette import status

from ..utils import g_config

log = logging.getLogger(__name__)

api_key_query = APIKeyQuery(name=g_config.server.api_key_name, auto_error=False)
api_key_header = APIKeyHeader(name=g_config.server.api_key_name, auto_error=False)
api_key_cookie = APIKeyCookie(name=g_config.server.api_key_name, auto_error=False)


def verify_api_key(
    query_key: str = Security(api_key_query),
    header_key: str = Security(api_key_header),
    cookie_key: str = Security(api_key_cookie),
):
    """Check for a valid API key from multiple sources."""
    if query_key == g_config.server.api_key:
        return query_key
    if header_key == g_config.server.api_key:
        return header_key
    if cookie_key == g_config.server.api_key:
        return cookie_key

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Invalid or missing API key.",
    )


def http_exception_handler(request: Request, exc: HTTPException):
    """
    HTTP exception handler
    """
    return JSONResponse(
        status_code=exc.status_code,
        content={"code": -1, "message": exc.detail},
    )


def validation_exception_handler(request: Request, exc: ValidationError):
    """
    Validation error handler
    """
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "code": -1,
            "message": "Validation Error",
            "data": exc.errors(),
        },
    )


def value_error_handler(request: Request, exc: ValueError):
    """
    Value error handler
    """
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "code": -1,
            "message": "Value Error",
            "data": str(exc),
        },
    )


def general_exception_handler(request: Request, exc: Exception):
    """
    Generic exception handler
    """
    log.exception("Internal Server Error", exc_info=exc)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "code": -1,
            "message": "Internal Server Error",
            "data": str(exc),
        },
    )
