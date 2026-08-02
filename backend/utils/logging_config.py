import logging
import logging.config
import time
from pathlib import Path

from backend.config import settings
from backend.utils.file_utils import ensure_directory

LOG_FILENAME = "smart_workspace.log"
LOG_FORMAT = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
MAX_LOG_BYTES = 5 * 1024 * 1024
LOG_BACKUP_COUNT = 3


class UTCFormatter(logging.Formatter):
    converter = time.gmtime


def _resolve_log_level(level: str | int | None) -> int:
    if level is None:
        level = settings.LOG_LEVEL
    if isinstance(level, int):
        return level

    resolved_level = logging.getLevelName(level.upper())
    if not isinstance(resolved_level, int):
        raise ValueError(f"Unsupported log level: {level}")
    return resolved_level


def configure_logging(
    level: str | int | None = None,
    log_directory: str | Path | None = None,
) -> Path:
    resolved_level = _resolve_log_level(level)
    if log_directory is None:
        log_directory = settings.DATA_ROOT / "logs"
    log_directory = ensure_directory(log_directory)
    log_path = log_directory / LOG_FILENAME

    logging.config.dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "standard": {
                    "()": UTCFormatter,
                    "format": LOG_FORMAT,
                    "datefmt": "%Y-%m-%d %H:%M:%S",
                },
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "level": resolved_level,
                    "formatter": "standard",
                    "stream": "ext://sys.stderr",
                },
                "file": {
                    "class": "logging.handlers.RotatingFileHandler",
                    "level": resolved_level,
                    "formatter": "standard",
                    "filename": str(log_path),
                    "maxBytes": MAX_LOG_BYTES,
                    "backupCount": LOG_BACKUP_COUNT,
                    "encoding": "utf-8",
                },
            },
            "root": {
                "level": resolved_level,
                "handlers": ["console", "file"],
            },
            "loggers": {
                "matplotlib": {"level": "WARNING"},
                "PIL": {"level": "WARNING"},
                "sqlalchemy.engine": {"level": "WARNING"},
            },
        }
    )
    return log_path
