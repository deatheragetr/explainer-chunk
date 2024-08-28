import logging
import sys
from typing import Optional


def setup_logging(
    log_level: str = "INFO", log_to_file: bool = False, log_file: Optional[str] = None
):
    # Create logger
    logger = logging.getLogger("app")
    logger.setLevel(getattr(logging, log_level))

    # Create formatter
    log_format = "%(levelname)s - %(asctime)s - %(name)s - %(message)s"
    formatter = logging.Formatter(log_format)

    # Create and add stdout handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # Optionally create and add file handler
    # May Not Need
    if log_to_file and log_file:
        from logging.handlers import RotatingFileHandler

        file_handler = RotatingFileHandler(log_file, maxBytes=10240, backupCount=5)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    # Prevent the logger from propagating messages to the root logger
    logger.propagate = False

    return logger


# Call after main.py/FastAPI app is created
def get_logger():
    return logging.getLogger("app")
