import logging
import logging.config
import re
from pathlib import Path
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

    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = self.scrub(record.msg)
        if isinstance(record.args, dict):
            record.args = {k: self.scrub(v) for k, v in record.args.items()}
        elif record.args:
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


def setup_logging(log_config_filename: Path, overridden_level: Optional[str] = None):
    try:
        from yaml import CSafeLoader as SafeLoader
    except ImportError:
        from yaml import SafeLoader

    with open(log_config_filename) as f:
        log_config_dict = yaml.load(f, Loader=SafeLoader)

    if overridden_level:
        for handler in log_config_dict["handlers"].values():
            handler["level"] = overridden_level
        for logger in log_config_dict["loggers"].values():
            logger["level"] = overridden_level
        log_config_dict["root"]["level"] = overridden_level

    logging.config.dictConfig(log_config_dict)

    def colorize(handler: logging.Handler):
        # Only apply color to console output
        if isinstance(handler, logging.StreamHandler) and handler.stream.isatty():
            formatter = handler.formatter
            if formatter is not None:
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
            else:
                raise ValueError("Handler has no formatter to colorize")

    root_logger = logging.getLogger()
    scrub_filter = ScrubFilter()
    for handler in root_logger.handlers:
        handler.addFilter(filter=scrub_filter)
        colorize(handler)

    logging.getLogger(__name__).info(f"Logger configured with {log_config_filename}")
