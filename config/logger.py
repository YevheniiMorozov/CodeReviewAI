import logging

from config.main_config import LOG_LEVEL


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    logging.basicConfig(level=LOG_LEVEL)
    return logger