import logging
import logging.config
import re
from typing import Any, Optional, Union

import yaml
from colorlog import ColoredFormatter


class ScrubFilter(logging.Filter):
    def __init__(self):
        super().__init__()
        # Replace sensitive information (ignoring case)
        self.pattern = re.compile(
            r'(?i)("(?:password|token|key|secret|community)"\s*:\s*["\'])(.*?)(["\'])'
        )

    def filter(self, record):
        record.msg = self.scrub(record.msg)
        if isinstance(record.args, dict):
            for k in record.args:
                record.args[k] = self.scrub(record.args[k])
        else:
            record.args = tuple(self.scrub(arg) for arg in record.args)
        return True

    def scrub(self, message: Union[str, Any]) -> str:
        if not isinstance(message, str):
            return message
        try:
            return self.pattern.sub(r"\1******\3", message)
        except Exception as e:
            logging.debug(f"Scrubbing error: {e!s}", exc_info=True)
            return message


def setup_logging(log_config_filename: str, overrided_level: Optional[str] = None):
    try:
        from yaml import CSafeLoader as SafeLoader
    except ImportError:
        from yaml import SafeLoader

    with open(log_config_filename) as f:
        log_config_dict = yaml.load(f, Loader=SafeLoader)

    if overrided_level:
        for handler in log_config_dict["handlers"].values():
            handler["level"] = overrided_level
        for logger in log_config_dict["loggers"].values():
            logger["level"] = overrided_level
        log_config_dict["root"]["level"] = overrided_level

    logging.config.dictConfig(log_config_dict)

    def colorize(handler: logging.Handler):
        # Only apply color to console output
        if isinstance(handler, logging.StreamHandler) and handler.stream.isatty():
            formatter = handler.formatter
            handler.setFormatter(
                ColoredFormatter(
                    fmt=formatter._fmt,
                    datefmt=formatter.datefmt,
                    log_colors={
                        "DEBUG": "cyan",
                        "INFO": "green",
                        "WARNING": "yellow",
                        "ERROR": "red",
                        "CRITICAL": "bold_red",
                    },
                )
            )

    root_logger = logging.getLogger()
    scrub_filter = ScrubFilter()
    for handler in root_logger.handlers:
        handler.addFilter(scrub_filter)
        colorize(handler)

    logging.getLogger(__name__).info(f"Logger configured with {log_config_filename}")
