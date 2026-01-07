"""
Tests for YFinance Client

Tests the YFinanceClient wrapper including quote fetching, historical data,
bulk operations, error handling, and data normalization.
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock
import pandas as pd

from src.clients.yfinance_client import YFinanceClient
from src.utils.exceptions import APIError


class TestYFinanceClient:
    """Test suite for YFinanceClient."""

    @pytest.fixture
    def client(self):
        """Create a YFinanceClient instance for testing."""
        return YFinanceClient(timeout=10)

    @pytest.fixture
    def mock_ticker_info(self):
        """Mock yfinance Ticker info data."""
        return {
            'regularMarketPrice': 150.25,
            'longName': 'Apple Inc.',
            'shortName': 'Apple',
            'previousClose': 148.50,
            'volume': 52000000,
            'regularMarketVolume': 52000000,
            'marketCap': 2400000000000,
            'dayHigh': 152.00,
            'regularMarketDayHigh': 152.00,
            'dayLow': 148.50,
            'regularMarketDayLow': 148.50,
            'fiftyTwoWeekHigh': 180.00,
            'fiftyTwoWeekLow': 130.00,
        }

    @pytest.fixture
    def mock_fast_info(self):
        """Mock yfinance fast_info data."""
        mock_fast = MagicMock()
        mock_fast.last_price = 150.25
        mock_fast.previous_close = 148.50
        mock_fast.last_volume = 52000000
        mock_fast.market_cap = 2400000000000
        mock_fast.day_high = 152.00
        mock_fast.day_low = 148.50
        mock_fast.year_high = 180.00
        mock_fast.year_low = 130.00
        return mock_fast

    def test_fetch_quote_success(self, client, mock_ticker_info):
        """Test successful quote fetching."""
        with patch('yfinance.Ticker') as mock_ticker_class:
            mock_ticker = Mock()
            mock_ticker.info = mock_ticker_info
            mock_ticker_class.return_value = mock_ticker

            quote = client.fetch_quote("AAPL")

            assert quote is not None
            assert quote['symbol'] == 'AAPL'
            assert quote['name'] == 'Apple Inc.'
            assert quote['price'] == 150.25
            assert quote['change'] == pytest.approx(1.75, 0.01)
            assert quote['change_percent'] == pytest.approx(1.18, 0.01)
            assert quote['volume'] == 52000000
            assert quote['market_cap'] == 2400000000000
            assert quote['day_high'] == 152.00
            assert quote['day_low'] == 148.50
            assert quote['year_high'] == 180.00
            assert quote['year_low'] == 130.00
            assert quote['source'] == 'yfinance'
            assert 'timestamp' in quote

    def test_fetch_quote_with_fast_info_fallback(self, client, mock_fast_info):
        """Test quote fetching with fast_info fallback when full info unavailable."""
        with patch('yfinance.Ticker') as mock_ticker_class:
            mock_ticker = Mock()
            mock_ticker.info = {}  # Empty info triggers fallback
            mock_ticker.fast_info = mock_fast_info
            mock_ticker_class.return_value = mock_ticker

            quote = client.fetch_quote("AAPL")

            assert quote is not None
            assert quote['symbol'] == 'AAPL'
            assert quote['price'] == 150.25
            assert quote['source'] == 'yfinance'

    def test_fetch_quote_no_data(self, client):
        """Test quote fetching when no data is available."""
        with patch('yfinance.Ticker') as mock_ticker_class:
            mock_ticker = Mock()
            mock_ticker.info = {}
            mock_ticker.fast_info = Mock(side_effect=Exception("No fast info"))
            mock_ticker_class.return_value = mock_ticker

            quote = client.fetch_quote("INVALID")
            assert quote is None

    def test_fetch_quote_api_error(self, client):
        """Test quote fetching when API raises an exception."""
        with patch('yfinance.Ticker') as mock_ticker_class:
            mock_ticker_class.side_effect = Exception("Network error")

            with pytest.raises(APIError) as exc_info:
                client.fetch_quote("AAPL")

            assert "Failed to fetch quote for AAPL" in str(exc_info.value)
            assert exc_info.value.endpoint == "yfinance.Ticker(AAPL)"

    def test_fetch_history_success(self, client):
        """Test successful historical data fetching."""
        # Create sample historical data
        dates = pd.date_range('2024-01-01', periods=5, freq='D', tz='UTC')
        mock_history = pd.DataFrame({
            'Open': [148.0, 149.0, 150.0, 151.0, 152.0],
            'High': [149.0, 150.0, 151.0, 152.0, 153.0],
            'Low': [147.0, 148.0, 149.0, 150.0, 151.0],
            'Close': [148.5, 149.5, 150.5, 151.5, 152.5],
            'Volume': [50000000, 51000000, 52000000, 53000000, 54000000],
        }, index=dates)

        with patch('yfinance.Ticker') as mock_ticker_class:
            mock_ticker = Mock()
            mock_ticker.history.return_value = mock_history
            mock_ticker_class.return_value = mock_ticker

            history = client.fetch_history("AAPL", period="5d", interval="1d")

            assert history is not None
            assert len(history) == 5
            assert 'Symbol' in history.columns
            assert all(history['Symbol'] == 'AAPL')
            assert history.index.tz is not None  # Timezone-aware
            mock_ticker.history.assert_called_once_with(
                period="5d",
                interval="1d",
                timeout=10
            )

    def test_fetch_history_timezone_conversion(self, client):
        """Test that historical data is properly converted to UTC."""
        # Create data with non-UTC timezone
        dates = pd.date_range('2024-01-01', periods=3, freq='D', tz='America/New_York')
        mock_history = pd.DataFrame({
            'Open': [148.0, 149.0, 150.0],
            'Close': [148.5, 149.5, 150.5],
            'Volume': [50000000, 51000000, 52000000],
        }, index=dates)

        with patch('yfinance.Ticker') as mock_ticker_class:
            mock_ticker = Mock()
            mock_ticker.history.return_value = mock_history
            mock_ticker_class.return_value = mock_ticker

            history = client.fetch_history("AAPL")

            # Check that timezone is UTC (handles both datetime.timezone.utc and pytz.UTC)
            assert str(history.index.tz) == 'UTC' or history.index.tz.tzname(None) == 'UTC'

    def test_fetch_history_empty(self, client):
        """Test historical data fetching when no data is available."""
        with patch('yfinance.Ticker') as mock_ticker_class:
            mock_ticker = Mock()
            mock_ticker.history.return_value = pd.DataFrame()
            mock_ticker_class.return_value = mock_ticker

            history = client.fetch_history("INVALID")
            assert history is None

    def test_fetch_history_api_error(self, client):
        """Test historical data fetching when API raises an exception."""
        with patch('yfinance.Ticker') as mock_ticker_class:
            mock_ticker = Mock()
            mock_ticker.history.side_effect = Exception("Network error")
            mock_ticker_class.return_value = mock_ticker

            with pytest.raises(APIError) as exc_info:
                client.fetch_history("AAPL")

            assert "Failed to fetch history for AAPL" in str(exc_info.value)

    def test_fetch_multiple_success(self, client, mock_ticker_info):
        """Test fetching multiple symbols successfully."""
        with patch('yfinance.Ticker') as mock_ticker_class:
            mock_ticker = Mock()
            mock_ticker.info = mock_ticker_info
            mock_ticker_class.return_value = mock_ticker

            symbols = ["AAPL", "MSFT", "GOOGL"]
            results = client.fetch_multiple(symbols)

            assert len(results) == 3
            assert all(symbol in results for symbol in symbols)
            assert all(results[symbol] is not None for symbol in symbols)
            assert all(results[symbol]['source'] == 'yfinance' for symbol in symbols)

    def test_fetch_multiple_with_failures(self, client, mock_ticker_info):
        """Test fetching multiple symbols with some failures."""
        def ticker_side_effect(symbol, session=None):
            mock_ticker = Mock()
            if symbol == "INVALID":
                mock_ticker.info = {}
                mock_ticker.fast_info = Mock(side_effect=Exception("No data"))
            else:
                mock_ticker.info = mock_ticker_info
            return mock_ticker

        with patch('yfinance.Ticker', side_effect=ticker_side_effect):
            symbols = ["AAPL", "INVALID", "MSFT"]
            results = client.fetch_multiple(symbols)

            assert len(results) == 3
            assert results["AAPL"] is not None
            assert results["INVALID"] is None
            assert results["MSFT"] is not None

    def test_normalize_quote_alternative_fields(self, client):
        """Test quote normalization with alternative field names."""
        info = {
            'currentPrice': 150.25,  # Alternative to regularMarketPrice
            'shortName': 'Apple',
            'previousClose': 148.50,
        }

        normalized = client._normalize_quote("AAPL", info)

        assert normalized['price'] == 150.25
        assert normalized['name'] == 'Apple'
        assert normalized['symbol'] == 'AAPL'

    def test_normalize_quote_missing_fields(self, client):
        """Test quote normalization with missing optional fields."""
        info = {
            'regularMarketPrice': 150.25,
            'previousClose': 148.50,
        }

        normalized = client._normalize_quote("AAPL", info)

        assert normalized['price'] == 150.25
        assert normalized['name'] == 'AAPL'  # Falls back to symbol
        assert normalized['volume'] == 0
        assert normalized['market_cap'] == 0
        assert normalized['day_high'] == 0.0
        assert normalized['day_low'] == 0.0
        assert normalized['year_high'] == 0.0
        assert normalized['year_low'] == 0.0

    def test_context_manager(self, client):
        """Test client as context manager with session management."""
        with patch('requests.Session') as mock_session_class:
            mock_session = Mock()
            mock_session_class.return_value = mock_session

            with client as ctx_client:
                assert ctx_client.session is not None

            mock_session.close.assert_called_once()
            assert client.session is None

    def test_forex_symbol(self, client):
        """Test fetching forex pairs (e.g., EURUSD=X)."""
        with patch('yfinance.Ticker') as mock_ticker_class:
            mock_ticker = Mock()
            mock_ticker.info = {
                'regularMarketPrice': 1.0850,
                'shortName': 'EUR/USD',
                'previousClose': 1.0820,
                'volume': 0,
                'marketCap': 0,
            }
            mock_ticker_class.return_value = mock_ticker

            quote = client.fetch_quote("EURUSD=X")

            assert quote is not None
            assert quote['symbol'] == 'EURUSD=X'
            assert 'EUR/USD' in quote['name']

    def test_commodity_symbol(self, client):
        """Test fetching commodity futures (e.g., GC=F for Gold)."""
        with patch('yfinance.Ticker') as mock_ticker_class:
            mock_ticker = Mock()
            mock_ticker.info = {
                'regularMarketPrice': 2050.50,
                'shortName': 'Gold Futures',
                'previousClose': 2040.00,
                'volume': 100000,
                'marketCap': 0,
            }
            mock_ticker_class.return_value = mock_ticker

            quote = client.fetch_quote("GC=F")

            assert quote is not None
            assert quote['symbol'] == 'GC=F'
            assert 'Gold' in quote['name']

    def test_timestamp_format(self, client, mock_ticker_info):
        """Test that timestamp is in ISO 8601 format with timezone."""
        with patch('yfinance.Ticker') as mock_ticker_class:
            mock_ticker = Mock()
            mock_ticker.info = mock_ticker_info
            mock_ticker_class.return_value = mock_ticker

            quote = client.fetch_quote("AAPL")

            # Verify ISO 8601 format
            timestamp = quote['timestamp']
            assert 'T' in timestamp
            assert timestamp.endswith('Z') or '+' in timestamp or timestamp.endswith('+00:00')

            # Verify parseable
            parsed = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            assert parsed is not None
