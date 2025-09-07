"""Central logging setup (Phase 1).
Creates a logs/ directory and configures a rotating file + console handler.
"""
import logging
import os
from logging.handlers import RotatingFileHandler

LOG_DIR = os.path.join(os.path.dirname(__file__), '..', 'logs')
LOG_PATH = os.path.abspath(os.path.join(LOG_DIR, 'flight_system.log'))

DEFAULT_FORMAT = '%(asctime)s %(levelname)s %(name)s :: %(message)s'

_initialized = False

def init_logging(level: str = 'INFO') -> None:
    global _initialized
    if _initialized:
        return
    os.makedirs(LOG_DIR, exist_ok=True)
    logger = logging.getLogger()
    logger.setLevel(level)
    # Clear existing handlers to avoid duplication
    logger.handlers.clear()

    formatter = logging.Formatter(DEFAULT_FORMAT)

    ch = logging.StreamHandler()
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    fh = RotatingFileHandler(LOG_PATH, maxBytes=2_000_000, backupCount=3, encoding='utf-8')
    fh.setFormatter(formatter)
    logger.addHandler(fh)

    _initialized = True

__all__ = ["init_logging", "LOG_PATH"]
