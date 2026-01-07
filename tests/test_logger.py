"""
Unit tests for logger utility.

Tests logging configuration, file rotation, console output,
and specialized logger instances.
"""

import logging
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import pytest

from src.utils.logger import (
    LoggerConfig,
    get_api_logger,
    get_cost_logger,
    get_logger,
    get_parser_logger,
    setup_logger,
)


class TestLoggerConfig:
    """Test LoggerConfig class."""

    def test_initialization(self):
        """Test LoggerConfig initializes with correct defaults."""
        config = LoggerConfig()

        assert config.log_dir.exists()
        assert config.log_level == logging.INFO
        assert config.max_bytes == 10 * 1024 * 1024  # 10MB
        assert config.backup_count == 5

    def test_daily_log_filename_format(self):
        """Test daily log filename generation with date prefix."""
        config = LoggerConfig()
        logger_name = "test.module"

        filename = config.get_daily_log_filename(logger_name)

        # Should contain YYYYMMDD prefix
        date_prefix = datetime.now().strftime("%Y%m%d")
        assert filename.startswith(date_prefix)
        assert "test_module" in filename
        assert filename.endswith(".log")

    def test_log_file_path_construction(self):
        """Test complete log file path construction."""
        config = LoggerConfig()
        logger_name = "bloomberg.api"

        log_path = config.get_log_file_path(logger_name)

        assert isinstance(log_path, Path)
        assert log_path.parent == config.log_dir
        assert log_path.suffix == ".log"


class TestSetupLogger:
    """Test setup_logger function."""

    def test_logger_creation(self):
        """Test basic logger creation."""
        logger_name = "test.logger"
        logger = setup_logger(logger_name)

        assert logger.name == logger_name
        assert len(logger.handlers) == 2  # File + Console

    def test_logger_level_configuration(self):
        """Test logger respects custom log level."""
        logger = setup_logger("test.debug", level=logging.DEBUG)
        assert logger.level == logging.DEBUG

        logger = setup_logger("test.warning", level=logging.WARNING)
        assert logger.level == logging.WARNING

    def test_file_handler_configuration(self):
        """Test file handler is configured correctly."""
        logger = setup_logger("test.file")

        # Find file handler
        file_handlers = [
            h for h in logger.handlers
            if isinstance(h, logging.handlers.RotatingFileHandler)
        ]

        assert len(file_handlers) == 1
        file_handler = file_handlers[0]

        assert file_handler.maxBytes == 10 * 1024 * 1024
        assert file_handler.backupCount == 5
        assert file_handler.level == logging.DEBUG

    def test_console_handler_configuration(self):
        """Test console handler is configured correctly."""
        logger = setup_logger("test.console")

        # Find stream handler
        stream_handlers = [
            h for h in logger.handlers
            if isinstance(h, logging.StreamHandler)
            and not isinstance(h, logging.handlers.RotatingFileHandler)
        ]

        assert len(stream_handlers) == 1

    def test_no_duplicate_handlers(self):
        """Test that calling setup_logger multiple times doesn't add duplicate handlers."""
        logger_name = "test.duplicates"

        logger1 = setup_logger(logger_name)
        handler_count1 = len(logger1.handlers)

        logger2 = setup_logger(logger_name)
        handler_count2 = len(logger2.handlers)

        assert handler_count1 == handler_count2 == 2

    def test_logger_writes_to_file(self, tmp_path):
        """Test that logger actually writes to log file."""
        with patch("src.utils.logger.LoggingConfig") as mock_config:
            mock_config.LOG_DIR = tmp_path
            mock_config.LOG_LEVEL = "INFO"
            mock_config.LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            mock_config.DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
            mock_config.MAX_LOG_SIZE = 1024 * 1024
            mock_config.BACKUP_COUNT = 3
            mock_config.ensure_log_directory = lambda: None

            logger = setup_logger("test.write")
            test_message = "Test log message"

            logger.info(test_message)

            # Find the log file
            log_files = list(tmp_path.glob("*.log"))
            assert len(log_files) > 0

            # Verify message was written
            log_content = log_files[0].read_text(encoding="utf-8")
            assert test_message in log_content


class TestGetLogger:
    """Test get_logger function."""

    def test_get_logger_returns_cached_instance(self):
        """Test that get_logger returns cached logger instances."""
        logger_name = "test.cached"

        logger1 = get_logger(logger_name)
        logger2 = get_logger(logger_name)

        assert logger1 is logger2

    def test_get_logger_creates_new_if_not_cached(self):
        """Test that get_logger creates new logger if not in cache."""
        unique_name = f"test.unique.{datetime.now().timestamp()}"
        logger = get_logger(unique_name)

        assert logger.name == unique_name
        assert len(logger.handlers) > 0


class TestSpecializedLoggers:
    """Test specialized logger instances."""

    def test_cost_logger_creation(self):
        """Test cost logger is created with correct name."""
        cost_logger = get_cost_logger()

        assert cost_logger.name == "bloomberg.cost"
        assert len(cost_logger.handlers) > 0

    def test_api_logger_creation(self):
        """Test API logger is created with correct name."""
        api_logger = get_api_logger()

        assert api_logger.name == "bloomberg.api"
        assert len(api_logger.handlers) > 0

    def test_parser_logger_creation(self):
        """Test parser logger is created with correct name."""
        parser_logger = get_parser_logger()

        assert parser_logger.name == "bloomberg.parser"
        assert len(parser_logger.handlers) > 0

    def test_specialized_loggers_are_cached(self):
        """Test that specialized loggers return same instance on multiple calls."""
        cost1 = get_cost_logger()
        cost2 = get_cost_logger()
        assert cost1 is cost2

        api1 = get_api_logger()
        api2 = get_api_logger()
        assert api1 is api2

        parser1 = get_parser_logger()
        parser2 = get_parser_logger()
        assert parser1 is parser2


class TestLoggingOutput:
    """Test actual logging output and formatting."""

    def test_log_levels(self, caplog):
        """Test different log levels are captured correctly."""
        logger = get_logger("test.levels")

        # Set logger to DEBUG level to capture all messages
        logger.setLevel(logging.DEBUG)

        with caplog.at_level(logging.DEBUG):
            logger.debug("Debug message")
            logger.info("Info message")
            logger.warning("Warning message")
            logger.error("Error message")
            logger.critical("Critical message")

        # Check that all messages were captured
        assert "Debug message" in caplog.text
        assert "Info message" in caplog.text
        assert "Warning message" in caplog.text
        assert "Error message" in caplog.text
        assert "Critical message" in caplog.text

    def test_log_message_with_context(self, caplog):
        """Test logging with contextual information."""
        logger = get_logger("test.context")

        with caplog.at_level(logging.INFO):
            logger.info("Processing symbol: %s", "AAPL:US")
            logger.warning("High cost detected: $%.2f", 5.75)

        assert "AAPL:US" in caplog.text
        assert "5.75" in caplog.text


class TestFileRotation:
    """Test log file rotation behavior."""

    def test_rotation_creates_backup_files(self, tmp_path):
        """Test that rotation creates numbered backup files."""
        with patch("src.utils.logger.LoggingConfig") as mock_config:
            mock_config.LOG_DIR = tmp_path
            mock_config.LOG_LEVEL = "INFO"
            mock_config.LOG_FORMAT = "%(message)s"
            mock_config.DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
            mock_config.MAX_LOG_SIZE = 100  # Very small size to trigger rotation
            mock_config.BACKUP_COUNT = 3
            mock_config.ensure_log_directory = lambda: None

            logger = setup_logger("test.rotation")

            # Write enough data to trigger rotation
            for i in range(20):
                logger.info("A" * 50)  # 50 characters per message

            # Check for backup files
            log_files = list(tmp_path.glob("*.log*"))
            assert len(log_files) > 1  # Original + at least one backup


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_logger_with_dots_in_name(self):
        """Test logger names with multiple dot separators."""
        logger = get_logger("app.module.submodule.component")

        assert logger.name == "app.module.submodule.component"

    def test_logger_with_special_characters(self):
        """Test logger handles special characters in name."""
        logger = get_logger("test-logger_123")

        assert logger.name == "test-logger_123"

    def test_concurrent_logger_creation(self):
        """Test that concurrent logger creation is safe."""
        logger_name = "test.concurrent"

        loggers = [get_logger(logger_name) for _ in range(10)]

        # All should be the same instance
        assert all(logger is loggers[0] for logger in loggers)
