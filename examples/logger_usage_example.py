"""
Logger Usage Examples for Bloomberg Data Crawler.

Demonstrates various logging patterns and best practices.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.utils.logger import (
    get_api_logger,
    get_cost_logger,
    get_logger,
    get_parser_logger,
)


def example_basic_logging():
    """Basic logging example."""
    print("\n=== Basic Logging Example ===")

    logger = get_logger(__name__)

    logger.debug("Debug: Variable value = 123")
    logger.info("Info: Application started successfully")
    logger.warning("Warning: Approaching rate limit")
    logger.error("Error: Failed to parse response")
    logger.critical("Critical: Database connection lost")


def example_cost_tracking():
    """Cost logger example for budget monitoring."""
    print("\n=== Cost Tracking Example ===")

    cost_logger = get_cost_logger()

    # Track individual request costs
    request_cost = 0.0015
    total_cost = 2.45
    budget = 5.50

    cost_logger.info(f"Request cost: ${request_cost:.4f}")
    cost_logger.info(f"Total spent: ${total_cost:.2f} / ${budget:.2f}")

    # Warning when approaching budget limit
    if total_cost / budget > 0.8:
        cost_logger.warning(
            f"Budget alert: {(total_cost/budget)*100:.1f}% of budget used"
        )


def example_api_logging():
    """API logger example for HTTP call tracking."""
    print("\n=== API Logging Example ===")

    api_logger = get_api_logger()

    # Log API requests
    url = "https://www.bloomberg.com/quote/AAPL:US"
    status_code = 200
    response_time = 0.456

    api_logger.debug(f"GET {url}")
    api_logger.info(
        f"Response: {status_code} - {response_time:.3f}s"
    )

    # Log errors
    if status_code >= 400:
        api_logger.error(
            f"API error: {status_code} from {url}"
        )


def example_parser_logging():
    """Parser logger example for data extraction."""
    print("\n=== Parser Logging Example ===")

    parser_logger = get_parser_logger()

    symbol = "AAPL:US"

    parser_logger.debug(f"Parsing page for {symbol}")
    parser_logger.info(f"Extracted price: $150.25")

    # Log missing data
    missing_field = "52_week_high"
    parser_logger.warning(
        f"Missing field '{missing_field}' for {symbol}"
    )


def example_structured_logging():
    """Structured logging with context."""
    print("\n=== Structured Logging Example ===")

    logger = get_logger("bloomberg.orchestrator")

    # Context-rich logging
    context = {
        "symbol": "AAPL:US",
        "source": "bloomberg",
        "cache_hit": False,
        "duration_ms": 456,
    }

    logger.info(
        "Data fetch completed",
        extra=context
    )

    # Multi-line logging for complex data
    logger.debug(
        "Request details:\n"
        f"  Symbol: {context['symbol']}\n"
        f"  Source: {context['source']}\n"
        f"  Cached: {context['cache_hit']}\n"
        f"  Duration: {context['duration_ms']}ms"
    )


def example_exception_logging():
    """Exception logging example."""
    print("\n=== Exception Logging Example ===")

    logger = get_logger(__name__)

    try:
        # Simulate an error
        result = 1 / 0
    except ZeroDivisionError as e:
        logger.error(
            f"Division error occurred: {e}",
            exc_info=True  # Include full traceback
        )


def example_module_specific_logger():
    """Module-specific logger example."""
    print("\n=== Module-Specific Logger Example ===")

    # Each module gets its own logger
    cache_logger = get_logger("bloomberg.storage.cache")
    db_logger = get_logger("bloomberg.storage.database")
    client_logger = get_logger("bloomberg.clients.bright_data")

    cache_logger.info("Cache hit for AAPL:US")
    db_logger.info("Inserted 5 records into database")
    client_logger.debug("Proxy connection established")


def example_performance_logging():
    """Performance logging example."""
    print("\n=== Performance Logging Example ===")

    logger = get_logger("bloomberg.performance")

    import time

    start_time = time.time()

    # Simulate work
    time.sleep(0.1)

    elapsed = time.time() - start_time

    logger.info(
        f"Operation completed in {elapsed*1000:.2f}ms"
    )

    if elapsed > 1.0:
        logger.warning(
            f"Slow operation detected: {elapsed:.2f}s"
        )


def main():
    """Run all logging examples."""
    print("=" * 60)
    print("Bloomberg Data Crawler - Logger Examples")
    print("=" * 60)

    example_basic_logging()
    example_cost_tracking()
    example_api_logging()
    example_parser_logging()
    example_structured_logging()
    example_exception_logging()
    example_module_specific_logger()
    example_performance_logging()

    print("\n" + "=" * 60)
    print("Check logs/ directory for detailed file logs")
    print("Daily log files are named: YYYYMMDD_logger_name.log")
    print("=" * 60)


if __name__ == "__main__":
    main()
