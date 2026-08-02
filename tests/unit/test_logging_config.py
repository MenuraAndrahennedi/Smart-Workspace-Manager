import logging

import pytest

from backend.utils.logging_config import LOG_FILENAME, configure_logging


@pytest.fixture(autouse=True)
def restore_root_logging():
    root_logger = logging.getLogger()
    original_handlers = root_logger.handlers[:]
    original_level = root_logger.level
    yield

    for handler in root_logger.handlers:
        if handler not in original_handlers:
            handler.close()
    root_logger.handlers = original_handlers
    root_logger.setLevel(original_level)


def test_configure_logging_writes_console_and_rotating_file(
    tmp_path,
    capsys,
):
    log_path = configure_logging("INFO", tmp_path)
    logger = logging.getLogger("backend.test")

    logger.debug("hidden message")
    logger.info("saved message")
    for handler in logging.getLogger().handlers:
        handler.flush()

    assert log_path == tmp_path / LOG_FILENAME
    assert "saved message" in log_path.read_text(encoding="utf-8")
    assert "hidden message" not in log_path.read_text(encoding="utf-8")
    assert "saved message" in capsys.readouterr().err


def test_configure_logging_is_idempotent(tmp_path):
    configure_logging("INFO", tmp_path)
    configure_logging("DEBUG", tmp_path)

    root_logger = logging.getLogger()
    assert root_logger.level == logging.DEBUG
    assert len(root_logger.handlers) == 2


def test_configure_logging_rejects_unknown_level(tmp_path):
    with pytest.raises(ValueError, match="Unsupported log level"):
        configure_logging("verbose", tmp_path)
