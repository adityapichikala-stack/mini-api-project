import sys

from loguru import logger

from config import settings

_configured = False


def configure_logging() -> None:
    global _configured
    if _configured:
        return

    logger.remove()
    logger.add(
        sys.stdout,
        level=settings.log_level,
        format="{level} | {message}",
    )
    _configured = True
