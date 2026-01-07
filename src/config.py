"""
Configuration management for Bloomberg Data Crawler.

Environment-based configuration using python-dotenv for secure credential handling.
"""

import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class BrightDataConfig:
    """Bright Data proxy configuration."""

    API_TOKEN: str = os.getenv("BRIGHT_DATA_TOKEN", "")
    ZONE: str = os.getenv("BRIGHT_DATA_ZONE", "bloomberg")
    HOST: str = os.getenv("BRIGHT_DATA_HOST", "brd.superproxy.io")
    PORT: int = int(os.getenv("BRIGHT_DATA_PORT", "33335"))

    @classmethod
    def get_proxy_url(cls) -> str:
        """Construct complete proxy URL."""
        if not cls.API_TOKEN:
            raise ValueError("BRIGHT_DATA_TOKEN not set in environment")
        return f"http://brd-customer-{cls.API_TOKEN}:@{cls.HOST}:{cls.PORT}"

    @classmethod
    def is_configured(cls) -> bool:
        """Check if Bright Data credentials are configured."""
        return bool(cls.API_TOKEN)


class CostConfig:
    """Budget and cost management configuration."""

    # Total budget in USD
    TOTAL_BUDGET: float = float(os.getenv("TOTAL_BUDGET", "5.50"))

    # Cost per Bloomberg request (in USD)
    COST_PER_REQUEST: float = float(os.getenv("COST_PER_REQUEST", "0.0015"))

    # Safety margin (percentage of budget to reserve)
    SAFETY_MARGIN: float = float(os.getenv("SAFETY_MARGIN", "0.10"))

    # Alert threshold (percentage of budget used to trigger warning)
    ALERT_THRESHOLD: float = float(os.getenv("ALERT_THRESHOLD", "0.80"))

    @classmethod
    def get_max_requests(cls) -> int:
        """Calculate maximum allowed requests based on budget."""
        usable_budget = cls.TOTAL_BUDGET * (1 - cls.SAFETY_MARGIN)
        return int(usable_budget / cls.COST_PER_REQUEST)

    @classmethod
    def get_alert_request_count(cls) -> int:
        """Get request count that triggers alert."""
        return int(cls.get_max_requests() * cls.ALERT_THRESHOLD)


class CacheConfig:
    """Cache and database configuration."""

    # Cache time-to-live in seconds (15 minutes default)
    TTL_SECONDS: int = int(os.getenv("CACHE_TTL_SECONDS", "900"))

    # Base directory for data storage
    DATA_DIR: Path = Path(os.getenv("DATA_DIR", "data"))

    # SQLite database path
    DB_PATH: Path = DATA_DIR / "bloomberg_cache.db"

    # Cache directory for raw responses
    CACHE_DIR: Path = Path(os.getenv("CACHE_DIR", "cache"))

    @classmethod
    def ensure_directories(cls) -> None:
        """Create necessary directories if they don't exist."""
        cls.DATA_DIR.mkdir(parents=True, exist_ok=True)
        cls.CACHE_DIR.mkdir(parents=True, exist_ok=True)


class SchedulerConfig:
    """Scheduling and update interval configuration."""

    # Update interval in seconds (15 minutes default)
    UPDATE_INTERVAL_SECONDS: int = int(os.getenv("UPDATE_INTERVAL_SECONDS", "900"))

    # Enable automatic updates
    AUTO_UPDATE_ENABLED: bool = os.getenv("AUTO_UPDATE_ENABLED", "true").lower() == "true"

    # Maximum retry attempts for failed requests
    MAX_RETRIES: int = int(os.getenv("MAX_RETRIES", "3"))

    # Delay between retries in seconds
    RETRY_DELAY_SECONDS: int = int(os.getenv("RETRY_DELAY_SECONDS", "5"))


class LoggingConfig:
    """Logging configuration."""

    # Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    # Log directory
    LOG_DIR: Path = Path(os.getenv("LOG_DIR", "logs"))

    # Log file name
    LOG_FILE: str = os.getenv("LOG_FILE", "bloomberg_crawler.log")

    # Log format
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    # Date format
    DATE_FORMAT: str = "%Y-%m-%d %H:%M:%S"

    # Maximum log file size in bytes (10MB default)
    MAX_LOG_SIZE: int = int(os.getenv("MAX_LOG_SIZE", str(10 * 1024 * 1024)))

    # Number of backup log files to keep
    BACKUP_COUNT: int = int(os.getenv("BACKUP_COUNT", "5"))

    @classmethod
    def ensure_log_directory(cls) -> None:
        """Create log directory if it doesn't exist."""
        cls.LOG_DIR.mkdir(parents=True, exist_ok=True)

    @classmethod
    def get_log_file_path(cls) -> Path:
        """Get full path to log file."""
        return cls.LOG_DIR / cls.LOG_FILE


class APIConfig:
    """External API configuration."""

    # Finnhub API key for fallback data
    FINNHUB_API_KEY: Optional[str] = os.getenv("FINNHUB_API_KEY")

    # Alpha Vantage API key for alternative data source
    ALPHA_VANTAGE_API_KEY: Optional[str] = os.getenv("ALPHA_VANTAGE_API_KEY")

    # API request timeout in seconds
    REQUEST_TIMEOUT: int = int(os.getenv("REQUEST_TIMEOUT", "30"))

    @classmethod
    def has_finnhub(cls) -> bool:
        """Check if Finnhub API is configured."""
        return bool(cls.FINNHUB_API_KEY)

    @classmethod
    def has_alpha_vantage(cls) -> bool:
        """Check if Alpha Vantage API is configured."""
        return bool(cls.ALPHA_VANTAGE_API_KEY)


class AppConfig:
    """Main application configuration aggregating all config classes."""

    bright_data = BrightDataConfig
    cost = CostConfig
    cache = CacheConfig
    scheduler = SchedulerConfig
    logging = LoggingConfig
    api = APIConfig

    # Application metadata
    APP_NAME: str = "Bloomberg Data Crawler"
    VERSION: str = "1.0.0"

    # Bloomberg target symbols
    DEFAULT_SYMBOLS: list[str] = [
        "AAPL:US",
        "MSFT:US",
        "GOOGL:US",
        "AMZN:US",
        "TSLA:US"
    ]

    @classmethod
    def initialize(cls) -> None:
        """Initialize all configuration settings and create necessary directories."""
        CacheConfig.ensure_directories()
        LoggingConfig.ensure_log_directory()

    @classmethod
    def validate(cls) -> tuple[bool, list[str]]:
        """
        Validate configuration settings.

        Returns:
            Tuple of (is_valid, error_messages)
        """
        errors = []

        # Validate Bright Data configuration
        if not BrightDataConfig.is_configured():
            errors.append("BRIGHT_DATA_TOKEN is not configured")

        # Validate budget settings
        if CostConfig.TOTAL_BUDGET <= 0:
            errors.append("TOTAL_BUDGET must be greater than 0")

        if CostConfig.COST_PER_REQUEST <= 0:
            errors.append("COST_PER_REQUEST must be greater than 0")

        # Validate cache TTL
        if CacheConfig.TTL_SECONDS < 60:
            errors.append("CACHE_TTL_SECONDS should be at least 60 seconds")

        # Validate scheduler settings
        if SchedulerConfig.UPDATE_INTERVAL_SECONDS < 60:
            errors.append("UPDATE_INTERVAL_SECONDS should be at least 60 seconds")

        return (len(errors) == 0, errors)


# Initialize configuration on module import
AppConfig.initialize()
