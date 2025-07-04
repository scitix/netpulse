import logging

from netpulse.utils import g_config, logger

log = logging.getLogger(__name__)

bind = f"{g_config.server.host}:{g_config.server.port}"
timeout = 3 * 60
keepalive = 24 * 60 * 60

workers = g_config.server.gunicorn_worker
worker_class = "uvicorn.workers.UvicornWorker"

accesslog = "-"
errorlog = "-"

# Gunicorn logger is seperated from application logger.
loglevel = "info"


def post_worker_init(worker):
    # NOTE: Logger must be configured after worker forked.
    logger.setup_logging(g_config.log.config, g_config.log.level)
