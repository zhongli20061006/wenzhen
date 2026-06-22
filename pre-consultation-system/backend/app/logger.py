import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from datetime import datetime

LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs")
os.makedirs(LOG_DIR, exist_ok=True)


def _formatter():
    return logging.Formatter(
        "[%(asctime)s] %(levelname)-8s %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def _handler(filename, level, max_bytes=10 * 1024 * 1024, backup_count=5):
    h = RotatingFileHandler(
        os.path.join(LOG_DIR, filename),
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
    )
    h.setLevel(level)
    h.setFormatter(_formatter())
    return h


def setup_logger(name: str = "app") -> logging.Logger:
    logger = logging.getLogger(name)

    if logger.handlers:
        return logger

    logger.setLevel(logging.DEBUG)

    logger.addHandler(_handler("app.log", logging.INFO))
    logger.addHandler(_handler("app_debug.log", logging.DEBUG))
    logger.addHandler(_handler("app_error.log", logging.ERROR))

    console = logging.StreamHandler(sys.stdout)
    console.setLevel(logging.DEBUG)
    console.setFormatter(_formatter())
    logger.addHandler(console)

    return logger


logger = setup_logger()
