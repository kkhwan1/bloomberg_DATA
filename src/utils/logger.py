"""
Advanced logging utility for Bloomberg Data Crawler.

Provides multi-destination logging with:
- Daily rotating file logs (YYYYMMDD.log)
- Colorized console output
- Size-based rotation with backup retention
- Module-specific logger instances with caching
- Specialized loggers for cost tracking, API calls, and parsing
"""

import logging
import sys
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Dict, Optional

try:
    import colorlog
    HAS_COLORLOG = True
except ImportError:
    HAS_COLORLOG = False

from src.config import LoggingConfig


# Global logger cache to prevent duplicate logger creation
_LOGGER_CACHE: Dict[str, logging.Logger] = {}


class LoggerConfig:
    """
    Centralized logger configuration manager.

    Manages log directories, file naming conventions, and formatting rules.
    """

    def __init__(self):
        """Initialize logger configuration from application settings."""
        self.log_dir = LoggingConfig.LOG_DIR
        self.log_level = getattr(logging, LoggingConfig.LOG_LEVEL.upper(), logging.INFO)
        self.max_bytes = LoggingConfig.MAX_LOG_SIZE
        self.backup_count = LoggingConfig.BACKUP_COUNT

        # File format (detailed)
        self.file_format = LoggingConfig.LOG_FORMAT
        self.date_format = LoggingConfig.DATE_FORMAT

        # Console format (colorized and simplified)
        if HAS_COLORLOG:
            self.console_format = (
                "%(log_color)s%(levelname)-8s%(reset)s "
                "%(cyan)s%(name)s%(reset)s - %(message)s"
            )
        else:
            self.console_format = "%(levelname)-8s %(name)s - %(message)s"

        # Ensure log directory exists
        LoggingConfig.ensure_log_directory()

    def get_daily_log_filename(self, logger_name: str) -> str:
        """
        Generate daily log filename with YYYYMMDD prefix.

        Args:
            logger_name: Name of the logger

        Returns:
            Formatted log filename (e.g., '20260107_bloomberg_crawler.log')
        """
        date_prefix = datetime.now().strftime("%Y%m%d")
        base_name = logger_name.replace(".", "_").lower()
        return f"{date_prefix}_{base_name}.log"

    def get_log_file_path(self, logger_name: str) -> Path:
        """
        Get full path to log file for given logger.

        Args:
            logger_name: Name of the logger

        Returns:
            Complete path to log file
        """
        filename = self.get_daily_log_filename(logger_name)
        return self.log_dir / filename


def setup_logger(name: str, level: Optional[int] = None) -> logging.Logger:
    """
    Create and configure a logger instance with file and console handlers.

    Features:
    - Daily rotating file logs with date prefix
    - Size-based rotation (10MB default) with 5 backups
    - Colorized console output (if colorlog available)
    - Detailed file logs, simplified console logs

    Args:
        name: Logger name (typically __name__ of calling module)
        level: Optional custom log level (defaults to config setting)

    Returns:
        Configured logger instance

    Example:
        >>> logger = setup_logger(__name__)
        >>> logger.info("Application started")
    """
    # Check cache first
    if name in _LOGGER_CACHE:
        return _LOGGER_CACHE[name]

    config = LoggerConfig()
    logger = logging.getLogger(name)

    # Set log level
    logger.setLevel(level or config.log_level)

    # Prevent duplicate handlers on repeated calls
    if logger.handlers:
        return logger

    # File handler with rotation
    log_file_path = config.get_log_file_path(name)
    file_handler = RotatingFileHandler(
        filename=log_file_path,
        maxBytes=config.max_bytes,
        backupCount=config.backup_count,
        encoding="utf-8"
    )
    file_handler.setLevel(logging.DEBUG)  # Capture all levels in file
    file_formatter = logging.Formatter(
        fmt=config.file_format,
        datefmt=config.date_format
    )
    file_handler.setFormatter(file_formatter)

    # Console handler with color support
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(config.log_level)

    if HAS_COLORLOG:
        # Colorized console output
        console_formatter = colorlog.ColoredFormatter(
            fmt=config.console_format,
            datefmt=config.date_format,
            log_colors={
                'DEBUG': 'white',
                'INFO': 'green',
                'WARNING': 'yellow',
                'ERROR': 'red',
                'CRITICAL': 'bold_red',
            }
        )
    else:
        # Fallback to standard formatter
        console_formatter = logging.Formatter(
            fmt=config.console_format,
            datefmt=config.date_format
        )

    console_handler.setFormatter(console_formatter)

    # Attach handlers
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    # Cache the logger
    _LOGGER_CACHE[name] = logger

    return logger


def get_logger(name: str) -> logging.Logger:
    """
    Retrieve cached logger instance or create new one.

    This is the recommended way to get logger instances throughout the application.
    Ensures consistent logging configuration across all modules.

    Args:
        name: Logger name (typically __name__ of calling module)

    Returns:
        Cached or newly created logger instance

    Example:
        >>> from src.utils.logger import get_logger
        >>> logger = get_logger(__name__)
        >>> logger.info("Processing data")
    """
    if name in _LOGGER_CACHE:
        return _LOGGER_CACHE[name]
    return setup_logger(name)


# Specialized logger instances for common use cases

def get_cost_logger() -> logging.Logger:
    """
    Get specialized logger for cost tracking and budget monitoring.

    Returns:
        Logger instance configured for cost-related operations

    Example:
        >>> cost_logger = get_cost_logger()
        >>> cost_logger.info(f"Request cost: ${cost:.4f}, Total: ${total:.2f}")
    """
    return get_logger("bloomberg.cost")


def get_api_logger() -> logging.Logger:
    """
    Get specialized logger for API call tracking and debugging.

    Returns:
        Logger instance configured for API operations

    Example:
        >>> api_logger = get_api_logger()
        >>> api_logger.debug(f"GET {url} - Status: {status_code}")
    """
    return get_logger("bloomberg.api")


def get_parser_logger() -> logging.Logger:
    """
    Get specialized logger for HTML parsing and data extraction.

    Returns:
        Logger instance configured for parsing operations

    Example:
        >>> parser_logger = get_parser_logger()
        >>> parser_logger.warning(f"Missing field: {field_name}")
    """
    return get_logger("bloomberg.parser")


# Convenience aliases for backward compatibility
cost_logger = get_cost_logger()
api_logger = get_api_logger()
parser_logger = get_parser_logger()


# Module-level setup logging
_module_logger = get_logger(__name__)
_module_logger.debug(
    f"Logger utility initialized - colorlog {'enabled' if HAS_COLORLOG else 'disabled'}"
)
