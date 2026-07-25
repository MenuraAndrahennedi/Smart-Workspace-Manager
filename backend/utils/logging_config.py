# How all application logs appear

import logging
from backend.config.settings import LOG_LEVEL


def configure_logging() -> None:
    level = getattr(logging, LOG_LEVEL)

    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # logger = logging.getLogger(__name__)

    # logger.debug("Detailed developer information")
    # logger.info("Application started successfully")
    # logger.warning("Storage is nearly full")
    # logger.error("Failed to save the file")
    # logger.critical("Application cannot continue")




