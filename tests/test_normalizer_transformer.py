"""
Tests for normalizer transformer module.

Test multi-source data transformation and normalization logic.
"""

from datetime import datetime

import pytest

from src.normalizer.schemas import AssetClass, DataSource
from src.normalizer.transformer import DataTransformer
from src.utils.exceptions import DataNormalizationError


class TestDataTransformer:
    """Test DataTransformer class."""

    def test_from_bloomberg_basic(self):
        """Test transforming basic Bloomberg data."""
        bloomberg_data = {
            "symbol": "AAPL:US",
            "name": "Apple Inc.",
            "last_price": 175.50,
            "timestamp": "2024-01-15T16:00:00Z",
            "change": 2.50,
            "pct_change": 1.45,
            "volume": 52000000,
        }

        quote = DataTransformer.from_bloomberg(bloomberg_data, AssetClass.STOCKS)

        assert quote.symbol == "AAPL:US"
        assert quote.name == "Apple Inc."
        assert quote.price == 175.50
        assert quote.source == DataSource.BLOOMBERG
        assert quote.asset_class == AssetClass.STOCKS
        assert quote.change == 2.50
        assert quote.change_percent == 1.45
        assert quote.volume == 52000000

    def test_from_bloomberg_full_data(self):
        """Test transforming comprehensive Bloomberg data."""
        bloomberg_data = {
            "symbol": "AAPL:US",
            "security_name": "Apple Inc.",
            "last_price": 175.50,
            "timestamp": "2024-01-15T16:00:00Z",
            "change": 2.50,
            "pct_change": 1.45,
            "volume": 52000000,
            "market_cap": 2750000000000,
            "open_price": 173.00,
            "day_high": 176.00,
            "day_low": 172.50,
            "previous_close": 173.00,
            "pe_ratio": 28.5,
            "eps": 6.15,
            "dividend_yield": 0.52,
            "beta": 1.25,
            "week_52_high": 198.23,
            "week_52_low": 164.08,
            "currency": "USD",
            "exchange": "NASDAQ",
            "sector": "Technology",
            "industry": "Consumer Electronics",
            "market_status": "open",
        }

        quote = DataTransformer.from_bloomberg(bloomberg_data, AssetClass.STOCKS)

        assert quote.price == 175.50
        assert quote.market_cap == 2750000000000
        assert quote.open_price == 173.00
        assert quote.day_high == 176.00
        assert quote.day_low == 172.50
        assert quote.pe_ratio == 28.5
        assert quote.currency == "USD"
        assert quote.exchange == "NASDAQ"
        assert quote.sector == "Technology"

    def test_from_bloomberg_missing_symbol(self):
        """Test Bloomberg transformation fails without symbol."""
        bloomberg_data = {
            "name": "Test",
            "last_price": 100.0,
            "timestamp": "2024-01-15T16:00:00Z",
        }

        with pytest.raises(DataNormalizationError, match="Missing required field: symbol"):
            DataTransformer.from_bloomberg(bloomberg_data, AssetClass.STOCKS)

    def test_from_bloomberg_invalid_price(self):
        """Test Bloomberg transformation fails with invalid price."""
        bloomberg_data = {
            "symbol": "TEST",
            "name": "Test",
            "last_price": -10.0,
            "timestamp": "2024-01-15T16:00:00Z",
        }

        with pytest.raises(DataNormalizationError, match="Invalid or missing price"):
            DataTransformer.from_bloomberg(bloomberg_data, AssetClass.STOCKS)

    def test_from_yfinance_basic(self):
        """Test transforming basic yfinance data."""
        yfinance_data = {
            "symbol": "AAPL",
            "longName": "Apple Inc.",
            "currentPrice": 175.50,
            "regularMarketTime": 1705338000,  # Unix timestamp
            "regularMarketChange": 2.50,
            "regularMarketChangePercent": 0.0145,  # yfinance uses decimal
            "regularMarketVolume": 52000000,
        }

        quote = DataTransformer.from_yfinance(yfinance_data, AssetClass.STOCKS)

        assert quote.symbol == "AAPL"
        assert quote.name == "Apple Inc."
        assert quote.price == 175.50
        assert quote.source == DataSource.YFINANCE
        assert quote.change == 2.50
        # Should convert decimal to percentage (with floating point tolerance)
        assert abs(quote.change_percent - 1.45) < 0.01
        assert quote.volume == 52000000

    def test_from_yfinance_full_data(self):
        """Test transforming comprehensive yfinance data."""
        yfinance_data = {
            "symbol": "AAPL",
            "longName": "Apple Inc.",
            "currentPrice": 175.50,
            "regularMarketTime": 1705338000,
            "regularMarketChange": 2.50,
            "regularMarketChangePercent": 0.0145,
            "regularMarketVolume": 52000000,
            "marketCap": 2750000000000,
            "regularMarketOpen": 173.00,
            "regularMarketDayHigh": 176.00,
            "regularMarketDayLow": 172.50,
            "regularMarketPreviousClose": 173.00,
            "trailingPE": 28.5,
            "trailingEps": 6.15,
            "dividendYield": 0.0052,  # yfinance uses decimal
            "beta": 1.25,
            "fiftyTwoWeekHigh": 198.23,
            "fiftyTwoWeekLow": 164.08,
            "currency": "USD",
            "exchange": "NMS",
            "sector": "Technology",
            "industry": "Consumer Electronics",
        }

        quote = DataTransformer.from_yfinance(yfinance_data, AssetClass.STOCKS)

        assert quote.price == 175.50
        assert quote.market_cap == 2750000000000
        assert quote.pe_ratio == 28.5
        # Should convert decimal to percentage
        assert quote.dividend_yield == 0.52
        assert quote.currency == "USD"

    def test_from_yfinance_historical_data(self):
        """Test transforming yfinance historical data format."""
        yfinance_data = {
            "symbol": "AAPL",
            "longName": "Apple Inc.",
            "Close": 175.50,  # Historical data uses 'Close' instead of 'currentPrice'
            "Date": "2024-01-15",
            "open": 173.00,  # Use lowercase for historical data
            "high": 176.00,
            "low": 172.50,
            "volume": 52000000,
        }

        quote = DataTransformer.from_yfinance(yfinance_data, AssetClass.STOCKS)

        assert quote.price == 175.50
        assert quote.open_price == 173.00
        assert quote.day_high == 176.00

    def test_from_finnhub_basic(self):
        """Test transforming basic Finnhub data."""
        finnhub_data = {
            "c": 175.50,  # current price
            "d": 2.50,  # change
            "dp": 1.45,  # percent change
            "h": 176.00,  # high
            "l": 172.50,  # low
            "o": 173.00,  # open
            "pc": 173.00,  # previous close
            "t": 1705338000,  # Unix timestamp
        }

        quote = DataTransformer.from_finnhub(
            finnhub_data, AssetClass.STOCKS, symbol="AAPL", name="Apple Inc."
        )

        assert quote.symbol == "AAPL"
        assert quote.name == "Apple Inc."
        assert quote.price == 175.50
        assert quote.source == DataSource.FINNHUB
        assert quote.change == 2.50
        assert quote.change_percent == 1.45
        assert quote.day_high == 176.00

    def test_from_finnhub_missing_symbol(self):
        """Test Finnhub transformation requires symbol parameter."""
        finnhub_data = {
            "c": 175.50,
            "t": 1705338000,
        }

        with pytest.raises(DataNormalizationError, match="Symbol is required"):
            DataTransformer.from_finnhub(finnhub_data, AssetClass.STOCKS, symbol="")

    def test_normalize_timestamp_datetime(self):
        """Test normalizing datetime object."""
        dt = datetime(2024, 1, 15, 16, 0, 0)
        result = DataTransformer.normalize_timestamp(dt)

        assert isinstance(result, datetime)
        assert result.year == 2024
        assert result.month == 1
        assert result.day == 15

    def test_normalize_timestamp_unix_seconds(self):
        """Test normalizing Unix timestamp in seconds."""
        unix_timestamp = 1705338000
        result = DataTransformer.normalize_timestamp(unix_timestamp)

        assert isinstance(result, datetime)
        assert result.year == 2024

    def test_normalize_timestamp_unix_milliseconds(self):
        """Test normalizing Unix timestamp in milliseconds."""
        unix_timestamp_ms = 1705338000000
        result = DataTransformer.normalize_timestamp(unix_timestamp_ms)

        assert isinstance(result, datetime)
        assert result.year == 2024

    def test_normalize_timestamp_iso_string(self):
        """Test normalizing ISO format string."""
        iso_string = "2024-01-15T16:00:00Z"
        result = DataTransformer.normalize_timestamp(iso_string)

        assert isinstance(result, datetime)
        assert result.year == 2024
        assert result.month == 1
        assert result.day == 15

    def test_normalize_timestamp_none(self):
        """Test normalizing None returns current time."""
        result = DataTransformer.normalize_timestamp(None)

        assert isinstance(result, datetime)
        # Should be recent (within last minute)
        age_seconds = (datetime.utcnow() - result).total_seconds()
        assert age_seconds < 60

    def test_normalize_number_int(self):
        """Test normalizing integer."""
        assert DataTransformer.normalize_number(100) == 100.0

    def test_normalize_number_float(self):
        """Test normalizing float."""
        assert DataTransformer.normalize_number(175.50) == 175.50

    def test_normalize_number_string(self):
        """Test normalizing numeric string."""
        assert DataTransformer.normalize_number("175.50") == 175.50

    def test_normalize_number_string_with_commas(self):
        """Test normalizing string with thousand separators."""
        assert DataTransformer.normalize_number("1,750,500.00") == 1750500.0

    def test_normalize_number_string_with_currency(self):
        """Test normalizing string with currency symbols."""
        assert DataTransformer.normalize_number("$175.50") == 175.50
        assert DataTransformer.normalize_number("€175.50") == 175.50
        assert DataTransformer.normalize_number("£175.50") == 175.50

    def test_normalize_number_string_with_percent(self):
        """Test normalizing string with percent sign."""
        assert DataTransformer.normalize_number("1.45%") == 1.45

    def test_normalize_number_with_suffix_k(self):
        """Test normalizing number with 'K' suffix."""
        assert DataTransformer.normalize_number("52K") == 52000

    def test_normalize_number_with_suffix_m(self):
        """Test normalizing number with 'M' suffix."""
        assert DataTransformer.normalize_number("2.75M") == 2750000

    def test_normalize_number_with_suffix_b(self):
        """Test normalizing number with 'B' suffix."""
        assert DataTransformer.normalize_number("2.75B") == 2750000000

    def test_normalize_number_none(self):
        """Test normalizing None returns None."""
        assert DataTransformer.normalize_number(None) is None

    def test_normalize_number_na_string(self):
        """Test normalizing 'N/A' returns None."""
        assert DataTransformer.normalize_number("N/A") is None
        assert DataTransformer.normalize_number("n/a") is None
        assert DataTransformer.normalize_number("NA") is None

    def test_normalize_number_invalid_string(self):
        """Test normalizing invalid string returns None."""
        assert DataTransformer.normalize_number("invalid") is None

    def test_infer_asset_class_stocks(self):
        """Test inferring stocks asset class."""
        # Standard stock symbols
        assert DataTransformer.infer_asset_class("AAPL") == AssetClass.STOCKS
        assert DataTransformer.infer_asset_class("AAPL:US") == AssetClass.STOCKS
        assert DataTransformer.infer_asset_class("MSFT") == AssetClass.STOCKS

    def test_infer_asset_class_forex(self):
        """Test inferring forex asset class."""
        # Forex pairs
        assert DataTransformer.infer_asset_class("EUR/USD") == AssetClass.FOREX
        assert DataTransformer.infer_asset_class("EURUSD") == AssetClass.FOREX
        assert DataTransformer.infer_asset_class("GBP/JPY") == AssetClass.FOREX

    def test_infer_asset_class_crypto(self):
        """Test inferring crypto asset class."""
        # Cryptocurrency
        assert DataTransformer.infer_asset_class("BTC-USD") == AssetClass.CRYPTO
        assert DataTransformer.infer_asset_class("BTCUSD") == AssetClass.CRYPTO
        assert DataTransformer.infer_asset_class("ETH-USD") == AssetClass.CRYPTO

    def test_infer_asset_class_indices(self):
        """Test inferring indices asset class."""
        # Market indices
        assert DataTransformer.infer_asset_class("^GSPC") == AssetClass.INDICES
        assert DataTransformer.infer_asset_class("^DJI") == AssetClass.INDICES

    def test_infer_asset_class_from_data(self):
        """Test inferring asset class from data hints."""
        data = {"quoteType": "ETF"}
        assert DataTransformer.infer_asset_class("SPY", data) == AssetClass.ETF

        data = {"quoteType": "CRYPTOCURRENCY"}
        assert DataTransformer.infer_asset_class("TEST", data) == AssetClass.CRYPTO

        data = {"quoteType": "FUTURE"}
        assert DataTransformer.infer_asset_class("ESZ23", data) == AssetClass.FUTURES


class TestDataTransformerEdgeCases:
    """Test edge cases and error handling."""

    def test_extract_field_multiple_names(self):
        """Test field extraction tries multiple field names."""
        data = {"alternate_name": "Test Value"}

        # Should find value using alternate field name
        result = DataTransformer._extract_field(data, ["primary_name", "alternate_name"])
        assert result == "Test Value"

    def test_extract_field_missing(self):
        """Test field extraction returns None when not found."""
        data = {"other_field": "value"}

        result = DataTransformer._extract_field(data, ["missing_field"])
        assert result is None

    def test_extract_numeric_with_conversion(self):
        """Test numeric extraction with type conversion."""
        data = {"value": "123.45"}

        result = DataTransformer._extract_numeric(data, ["value"])
        assert result == 123.45

    def test_parse_market_status_variations(self):
        """Test parsing various market status strings."""
        assert (
            DataTransformer._parse_market_status("OPEN").value
            == "open"
        )
        assert (
            DataTransformer._parse_market_status("closed").value
            == "closed"
        )
        assert (
            DataTransformer._parse_market_status("After-Hours").value
            == "post_market"
        )
        assert (
            DataTransformer._parse_market_status("Pre-Market").value
            == "pre_market"
        )
        assert (
            DataTransformer._parse_market_status("halted").value
            == "halted"
        )
        assert (
            DataTransformer._parse_market_status("unknown_status").value
            == "unknown"
        )

    def test_bloomberg_fallback_name_to_symbol(self):
        """Test Bloomberg uses symbol as name fallback."""
        bloomberg_data = {
            "symbol": "TEST:US",
            "last_price": 100.0,
            "timestamp": "2024-01-15T16:00:00Z",
        }

        quote = DataTransformer.from_bloomberg(bloomberg_data, AssetClass.STOCKS)
        assert quote.name == "TEST:US"

    def test_yfinance_fallback_name_to_symbol(self):
        """Test yfinance uses symbol as name fallback."""
        yfinance_data = {
            "symbol": "TEST",
            "currentPrice": 100.0,
            "regularMarketTime": 1705338000,
        }

        quote = DataTransformer.from_yfinance(yfinance_data, AssetClass.STOCKS)
        assert quote.name == "TEST"

    def test_finnhub_default_name(self):
        """Test Finnhub defaults name to symbol if not provided."""
        finnhub_data = {
            "c": 100.0,
            "t": 1705338000,
        }

        quote = DataTransformer.from_finnhub(
            finnhub_data, AssetClass.STOCKS, symbol="TEST"
        )
        assert quote.name == "TEST"
