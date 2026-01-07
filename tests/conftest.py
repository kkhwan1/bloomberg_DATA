"""
Pytest configuration and shared fixtures for Bloomberg Data Crawler tests.

Provides:
    - Test data fixtures
    - Mock clients and responses
    - Temporary directories
    - Common test utilities
"""

import json
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Dict
from unittest.mock import MagicMock, Mock

import pytest

from src.normalizer.schemas import AssetClass, MarketQuote
from src.orchestrator.cache_manager import CacheManager
from src.orchestrator.cost_tracker import CostTracker


# ========== Directory and Path Fixtures ==========


@pytest.fixture
def fixtures_dir() -> Path:
    """
    Get path to test fixtures directory.

    Returns:
        Path to tests/fixtures directory
    """
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def temp_cache_dir():
    """
    Create temporary directory for cache database.

    Yields:
        Path to temporary directory

    Cleanup:
        Removes directory and all contents after test
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


@pytest.fixture
def temp_log_dir():
    """
    Create temporary directory for log files.

    Yields:
        Path to temporary directory
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


# ========== Bloomberg HTML Fixtures ==========


@pytest.fixture
def sample_bloomberg_html(fixtures_dir: Path) -> str:
    """
    Load sample Bloomberg HTML for testing.

    Args:
        fixtures_dir: Path to fixtures directory

    Returns:
        HTML content as string
    """
    html_file = fixtures_dir / "sample_bloomberg.html"

    if html_file.exists():
        return html_file.read_text(encoding="utf-8")

    # Return minimal valid HTML if fixture doesn't exist
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>AAPL:US - Bloomberg</title>
        <script type="application/ld+json">
        {
            "@context": "https://schema.org",
            "@type": "Corporation",
            "name": "Apple Inc.",
            "tickerSymbol": "AAPL",
            "price": 185.50,
            "priceCurrency": "USD"
        }
        </script>
    </head>
    <body>
        <h1>Apple Inc.</h1>
        <span class="price">185.50</span>
    </body>
    </html>
    """


@pytest.fixture
def sample_bloomberg_json_ld() -> Dict:
    """
    Sample Bloomberg JSON-LD structured data.

    Returns:
        Dictionary with JSON-LD data
    """
    return {
        "@context": "https://schema.org",
        "@type": "Corporation",
        "name": "Apple Inc.",
        "tickerSymbol": "AAPL",
        "price": 185.50,
        "priceChange": 2.35,
        "priceChangePercent": 1.28,
        "priceCurrency": "USD",
        "volume": 45678900,
        "marketCap": 2850000000000
    }


@pytest.fixture
def sample_bloomberg_next_data() -> Dict:
    """
    Sample Bloomberg __NEXT_DATA__ structure.

    Returns:
        Dictionary with Next.js data
    """
    return {
        "props": {
            "pageProps": {
                "quote": {
                    "ticker": "AAPL",
                    "name": "Apple Inc.",
                    "lastPrice": 185.50,
                    "change": 2.35,
                    "changePercent": 1.28,
                    "currency": "USD",
                    "volume": 45678900,
                    "marketCap": 2850000000000,
                    "high": 187.20,
                    "low": 183.10,
                    "open": 184.00,
                    "previousClose": 183.15,
                    "yearHigh": 199.62,
                    "yearLow": 124.17
                }
            }
        }
    }


# ========== Cost Tracker Fixtures ==========


@pytest.fixture
def mock_cost_tracker():
    """
    Mock CostTracker for testing without affecting real budget.

    Returns:
        Mock CostTracker instance
    """
    tracker = Mock(spec=CostTracker)
    tracker.budget_limit = 100.0
    tracker.cost_per_request = 0.0015
    tracker.total_requests = 0
    tracker.total_cost = 0.0
    tracker.successful_requests = 0
    tracker.failed_requests = 0

    def can_make_request():
        return tracker.total_cost + tracker.cost_per_request <= tracker.budget_limit

    def record_request(asset_class: str, symbol: str, success: bool = True):
        tracker.total_requests += 1
        tracker.total_cost += tracker.cost_per_request

        if success:
            tracker.successful_requests += 1
        else:
            tracker.failed_requests += 1

        usage_ratio = tracker.total_cost / tracker.budget_limit
        alert_level = 'ok'
        if usage_ratio >= 0.95:
            alert_level = 'danger'
        elif usage_ratio >= 0.80:
            alert_level = 'critical'
        elif usage_ratio >= 0.50:
            alert_level = 'warning'

        return {
            'request_count': tracker.total_requests,
            'total_cost': tracker.total_cost,
            'budget_remaining': tracker.budget_limit - tracker.total_cost,
            'budget_used_pct': usage_ratio * 100,
            'alert_level': alert_level,
            'success': success,
            'asset_class': asset_class,
            'symbol': symbol,
            'timestamp': datetime.now().isoformat()
        }

    def get_statistics():
        usage_ratio = tracker.total_cost / tracker.budget_limit
        return {
            'total_requests': tracker.total_requests,
            'total_cost': tracker.total_cost,
            'budget_remaining': tracker.budget_limit - tracker.total_cost,
            'budget_used_pct': usage_ratio * 100,
            'successful_requests': tracker.successful_requests,
            'failed_requests': tracker.failed_requests
        }

    tracker.can_make_request = can_make_request
    tracker.record_request = record_request
    tracker.get_statistics = get_statistics

    return tracker


@pytest.fixture
def clean_cost_tracker(temp_log_dir):
    """
    Provide clean CostTracker instance for testing.

    Args:
        temp_log_dir: Temporary directory for storage

    Yields:
        Fresh CostTracker instance
    """
    # Reset singleton
    CostTracker._instance = None

    # Mock storage path to use temp directory
    from unittest.mock import patch

    storage_path = temp_log_dir / "cost_tracking.json"

    with patch('src.config.LoggingConfig.LOG_DIR', temp_log_dir):
        tracker = CostTracker()
        tracker.storage_path = storage_path

        # Reset to clean state
        try:
            tracker.reset(confirm=True)
        except:
            pass

        yield tracker

        # Cleanup
        if storage_path.exists():
            storage_path.unlink()


# ========== Cache Manager Fixtures ==========


@pytest.fixture
def clean_cache_manager(temp_cache_dir):
    """
    Provide clean CacheManager instance for testing.

    Args:
        temp_cache_dir: Temporary directory for database

    Yields:
        Fresh CacheManager instance
    """
    db_path = temp_cache_dir / "test_cache.db"
    cache = CacheManager(db_path=db_path, ttl_seconds=900)

    yield cache

    # Cleanup
    cache.close()
    if db_path.exists():
        db_path.unlink()


# ========== Mock API Response Fixtures ==========


@pytest.fixture
def mock_yfinance_response() -> Dict:
    """
    Mock yfinance API response data.

    Returns:
        Dictionary with yfinance-style quote data
    """
    return {
        'symbol': 'AAPL',
        'shortName': 'Apple Inc.',
        'regularMarketPrice': 185.50,
        'regularMarketChange': 2.35,
        'regularMarketChangePercent': 1.28,
        'regularMarketVolume': 45678900,
        'marketCap': 2850000000000,
        'regularMarketDayHigh': 187.20,
        'regularMarketDayLow': 183.10,
        'regularMarketOpen': 184.00,
        'regularMarketPreviousClose': 183.15,
        'fiftyTwoWeekHigh': 199.62,
        'fiftyTwoWeekLow': 124.17,
        'currency': 'USD'
    }


@pytest.fixture
def mock_bright_data_html() -> str:
    """
    Mock Bright Data HTML response.

    Returns:
        HTML string with Bloomberg quote data
    """
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <script id="__NEXT_DATA__" type="application/json">
        {
            "props": {
                "pageProps": {
                    "quote": {
                        "ticker": "AAPL",
                        "name": "Apple Inc.",
                        "lastPrice": 185.50,
                        "change": 2.35,
                        "changePercent": 1.28,
                        "currency": "USD",
                        "volume": 45678900,
                        "marketCap": 2850000000000
                    }
                }
            }
        }
        </script>
    </head>
    <body>
        <h1>Apple Inc.</h1>
    </body>
    </html>
    """


@pytest.fixture
def mock_market_quote() -> MarketQuote:
    """
    Sample MarketQuote object for testing.

    Returns:
        MarketQuote instance with test data
    """
    return MarketQuote(
        symbol="AAPL:US",
        name="Apple Inc.",
        asset_class=AssetClass.STOCKS,
        price=185.50,
        change=2.35,
        change_percent=1.28,
        volume=45678900,
        market_cap=2850000000000.0,
        currency="USD",
        day_high=187.20,
        day_low=183.10,
        open_price=184.00,
        previous_close=183.15,
        year_high=199.62,
        year_low=124.17,
        source="yfinance",
        timestamp=datetime.now()
    )


# ========== Mock Client Fixtures ==========


@pytest.fixture
def mock_yfinance_client():
    """
    Mock YFinanceClient for testing.

    Returns:
        Mock client instance
    """
    client = MagicMock()

    client.fetch_quote.return_value = {
        'symbol': 'AAPL',
        'shortName': 'Apple Inc.',
        'regularMarketPrice': 185.50,
        'regularMarketChange': 2.35,
        'regularMarketChangePercent': 1.28,
        'regularMarketVolume': 45678900,
        'marketCap': 2850000000000,
        'currency': 'USD'
    }

    return client


@pytest.fixture
def mock_bright_data_client():
    """
    Mock BrightDataClient for testing.

    Returns:
        Mock async client instance
    """
    client = MagicMock()

    async def mock_fetch(url: str) -> str:
        return """
        <html>
        <head>
            <script type="application/ld+json">
            {
                "@type": "Corporation",
                "name": "Apple Inc.",
                "tickerSymbol": "AAPL",
                "price": 185.50,
                "priceCurrency": "USD"
            }
            </script>
        </head>
        </html>
        """

    client.fetch = mock_fetch

    return client


# ========== Utility Fixtures ==========


@pytest.fixture
def sample_symbols() -> list:
    """
    Sample trading symbols for batch testing.

    Returns:
        List of ticker symbols
    """
    return [
        "AAPL:US",
        "MSFT:US",
        "GOOGL:US",
        "AMZN:US",
        "TSLA:US"
    ]


@pytest.fixture
def sample_asset_classes() -> Dict[str, AssetClass]:
    """
    Sample asset class mappings.

    Returns:
        Dictionary mapping symbols to asset classes
    """
    return {
        "AAPL:US": AssetClass.STOCKS,
        "SPX:IND": AssetClass.INDICES,
        "EUR/USD": AssetClass.FOREX,
        "GC=F": AssetClass.COMMODITIES,
        "US10Y:GOV": AssetClass.BONDS
    }
