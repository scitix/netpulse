import logging

from fastapi import Depends, FastAPI, HTTPException
from pydantic import ValidationError

from . import __version__
from .routes import device, manage, template
from .server import (
    general_exception_handler,
    http_exception_handler,
    validation_exception_handler,
    value_error_handler,
    verify_api_key,
)
from .utils import g_config
from .utils.logger import setup_logging

log = logging.getLogger(__name__)

log.info("Starting NetPulse Controller...")
app = FastAPI(
    title="NetPulse Controller",
    description="NetPulse Controller API",
    version=__version__,
    contact={"name": "NetPulse"},
)

# Static files
# app.mount("/static", StaticFiles(directory="netpulse/static"), name="static")

# Routes
app.include_router(device, dependencies=[Depends(verify_api_key)])  # Unified device operation
app.include_router(template, dependencies=[Depends(verify_api_key)])
app.include_router(manage, dependencies=[Depends(verify_api_key)])

# Exception handlers
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(ValidationError, validation_exception_handler)
app.add_exception_handler(ValueError, value_error_handler)
app.add_exception_handler(Exception, general_exception_handler)


def main():
    """
    This should never be used in production, for testing purpose only.
    """
    import uvicorn

    setup_logging(g_config.log.config, g_config.log.level)
    log.warning("Uvicorn is for testing purpose only.")
    log.warning("Use gunicorn.conf.py for production.")

    log.info("Starting NetPulse Controller with Uvicorn...")
    uvicorn.run(app, host=g_config.server.host, port=g_config.server.port)


if __name__ == "__main__":
    main()
