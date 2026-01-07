"""
Tests for normalizer schemas module.

Test Pydantic models for data validation, serialization, and business logic.
"""

import json
from datetime import datetime, timedelta

import pytest

from src.normalizer.schemas import (
    AssetClass,
    DataSource,
    MarketQuote,
    MarketStatus,
    QuoteCollection,
)


class TestMarketQuote:
    """Test MarketQuote model."""

    def test_create_valid_quote(self):
        """Test creating a valid quote with required fields."""
        quote = MarketQuote(
            symbol="AAPL:US",
            name="Apple Inc.",
            price=175.50,
            timestamp=datetime.utcnow(),
            source=DataSource.BLOOMBERG,
            asset_class=AssetClass.STOCKS,
        )

        assert quote.symbol == "AAPL:US"
        assert quote.name == "Apple Inc."
        assert quote.price == 175.50
        assert quote.source == DataSource.BLOOMBERG
        assert quote.asset_class == AssetClass.STOCKS

    def test_symbol_normalization(self):
        """Test that symbol is normalized to uppercase."""
        quote = MarketQuote(
            symbol="aapl:us",
            name="Apple Inc.",
            price=175.50,
            timestamp=datetime.utcnow(),
            source=DataSource.YFINANCE,
            asset_class=AssetClass.STOCKS,
        )

        assert quote.symbol == "AAPL:US"

    def test_empty_symbol_validation(self):
        """Test that empty symbol raises validation error."""
        with pytest.raises(ValueError, match="Symbol cannot be empty"):
            MarketQuote(
                symbol="",
                name="Test",
                price=100.0,
                timestamp=datetime.utcnow(),
                source=DataSource.BLOOMBERG,
                asset_class=AssetClass.STOCKS,
            )

    def test_negative_price_validation(self):
        """Test that negative price raises validation error."""
        with pytest.raises(ValueError):
            MarketQuote(
                symbol="TEST",
                name="Test",
                price=-10.0,
                timestamp=datetime.utcnow(),
                source=DataSource.BLOOMBERG,
                asset_class=AssetClass.STOCKS,
            )

    def test_price_range_validation(self):
        """Test day high/low validation logic."""
        with pytest.raises(ValueError, match="day_low cannot exceed day_high"):
            MarketQuote(
                symbol="TEST",
                name="Test",
                price=100.0,
                timestamp=datetime.utcnow(),
                source=DataSource.BLOOMBERG,
                asset_class=AssetClass.STOCKS,
                day_high=90.0,
                day_low=110.0,
            )

    def test_52_week_range_validation(self):
        """Test 52-week high/low validation."""
        with pytest.raises(ValueError, match="week_52_low cannot exceed week_52_high"):
            MarketQuote(
                symbol="TEST",
                name="Test",
                price=100.0,
                timestamp=datetime.utcnow(),
                source=DataSource.BLOOMBERG,
                asset_class=AssetClass.STOCKS,
                week_52_high=80.0,
                week_52_low=120.0,
            )

    def test_auto_calculate_change_percent(self):
        """Test automatic calculation of change_percent."""
        quote = MarketQuote(
            symbol="TEST",
            name="Test",
            price=105.0,
            timestamp=datetime.utcnow(),
            source=DataSource.BLOOMBERG,
            asset_class=AssetClass.STOCKS,
            change=5.0,
            previous_close=100.0,
        )

        assert quote.change_percent == 5.0

    def test_auto_calculate_spread(self):
        """Test automatic calculation of bid-ask spread."""
        quote = MarketQuote(
            symbol="EUR/USD",
            name="Euro US Dollar",
            price=1.1050,
            timestamp=datetime.utcnow(),
            source=DataSource.BLOOMBERG,
            asset_class=AssetClass.FOREX,
            bid=1.1048,
            ask=1.1052,
        )

        assert quote.spread == 0.0004

    def test_is_valid_basic(self):
        """Test is_valid method with valid quote."""
        quote = MarketQuote(
            symbol="AAPL:US",
            name="Apple Inc.",
            price=175.50,
            timestamp=datetime.utcnow(),
            source=DataSource.BLOOMBERG,
            asset_class=AssetClass.STOCKS,
        )

        assert quote.is_valid() is True

    def test_is_valid_stale_data(self):
        """Test is_valid rejects stale data."""
        old_timestamp = datetime.utcnow() - timedelta(hours=2)
        quote = MarketQuote(
            symbol="AAPL:US",
            name="Apple Inc.",
            price=175.50,
            timestamp=old_timestamp,
            source=DataSource.BLOOMBERG,
            asset_class=AssetClass.STOCKS,
            data_freshness_seconds=7200,  # 2 hours
        )

        assert quote.is_valid() is False

    def test_is_valid_low_confidence(self):
        """Test is_valid rejects low confidence data."""
        quote = MarketQuote(
            symbol="AAPL:US",
            name="Apple Inc.",
            price=175.50,
            timestamp=datetime.utcnow(),
            source=DataSource.CACHE,
            asset_class=AssetClass.STOCKS,
            confidence_score=0.3,
        )

        assert quote.is_valid() is False

    def test_to_csv_row(self):
        """Test CSV serialization."""
        quote = MarketQuote(
            symbol="AAPL:US",
            name="Apple Inc.",
            price=175.50,
            timestamp=datetime(2024, 1, 15, 16, 0, 0),
            source=DataSource.BLOOMBERG,
            asset_class=AssetClass.STOCKS,
            change=2.50,
            change_percent=1.45,
            volume=52000000,
        )

        csv_row = quote.to_csv_row()

        assert csv_row["symbol"] == "AAPL:US"
        assert csv_row["price"] == 175.50
        assert csv_row["source"] == "bloomberg"
        assert csv_row["asset_class"] == "stocks"
        assert csv_row["volume"] == 52000000

    def test_to_json(self):
        """Test JSON serialization."""
        quote = MarketQuote(
            symbol="AAPL:US",
            name="Apple Inc.",
            price=175.50,
            timestamp=datetime(2024, 1, 15, 16, 0, 0),
            source=DataSource.BLOOMBERG,
            asset_class=AssetClass.STOCKS,
        )

        json_str = quote.to_json()
        parsed = json.loads(json_str)

        assert parsed["symbol"] == "AAPL:US"
        assert parsed["price"] == 175.50
        assert parsed["source"] == "bloomberg"

    def test_to_dict(self):
        """Test dictionary conversion."""
        quote = MarketQuote(
            symbol="AAPL:US",
            name="Apple Inc.",
            price=175.50,
            timestamp=datetime(2024, 1, 15, 16, 0, 0),
            source=DataSource.BLOOMBERG,
            asset_class=AssetClass.STOCKS,
        )

        quote_dict = quote.to_dict()

        assert isinstance(quote_dict, dict)
        assert quote_dict["symbol"] == "AAPL:US"
        assert quote_dict["price"] == 175.50

    def test_from_dict(self):
        """Test creating quote from dictionary."""
        data = {
            "symbol": "AAPL:US",
            "name": "Apple Inc.",
            "price": 175.50,
            "timestamp": datetime(2024, 1, 15, 16, 0, 0),
            "source": DataSource.BLOOMBERG,
            "asset_class": AssetClass.STOCKS,
        }

        quote = MarketQuote.from_dict(data)

        assert quote.symbol == "AAPL:US"
        assert quote.price == 175.50

    def test_calculate_data_age(self):
        """Test data age calculation."""
        # Create quote with timestamp 5 minutes ago
        old_time = datetime.utcnow() - timedelta(minutes=5)
        quote = MarketQuote(
            symbol="AAPL:US",
            name="Apple Inc.",
            price=175.50,
            timestamp=old_time,
            source=DataSource.BLOOMBERG,
            asset_class=AssetClass.STOCKS,
        )

        age = quote.calculate_data_age()

        # Should be approximately 300 seconds (5 minutes)
        assert 290 <= age <= 310

    def test_is_fresh(self):
        """Test freshness check."""
        # Fresh data (1 minute old)
        fresh_time = datetime.utcnow() - timedelta(minutes=1)
        fresh_quote = MarketQuote(
            symbol="AAPL:US",
            name="Apple Inc.",
            price=175.50,
            timestamp=fresh_time,
            source=DataSource.BLOOMBERG,
            asset_class=AssetClass.STOCKS,
        )

        assert fresh_quote.is_fresh(max_age_seconds=900) is True

        # Stale data (20 minutes old)
        stale_time = datetime.utcnow() - timedelta(minutes=20)
        stale_quote = MarketQuote(
            symbol="AAPL:US",
            name="Apple Inc.",
            price=175.50,
            timestamp=stale_time,
            source=DataSource.BLOOMBERG,
            asset_class=AssetClass.STOCKS,
        )

        assert stale_quote.is_fresh(max_age_seconds=900) is False

    def test_get_display_name(self):
        """Test display name formatting."""
        quote = MarketQuote(
            symbol="AAPL:US",
            name="Apple Inc.",
            price=175.50,
            timestamp=datetime.utcnow(),
            source=DataSource.BLOOMBERG,
            asset_class=AssetClass.STOCKS,
        )

        assert quote.get_display_name() == "Apple Inc. (AAPL:US)"

    def test_str_representation(self):
        """Test string representation."""
        quote = MarketQuote(
            symbol="AAPL:US",
            name="Apple Inc.",
            price=175.50,
            timestamp=datetime(2024, 1, 15, 16, 0, 0),
            source=DataSource.BLOOMBERG,
            asset_class=AssetClass.STOCKS,
            change_percent=1.45,
        )

        str_repr = str(quote)

        assert "AAPL:US" in str_repr
        assert "$175.50" in str_repr
        assert "+1.45%" in str_repr


class TestQuoteCollection:
    """Test QuoteCollection model."""

    def test_create_empty_collection(self):
        """Test creating empty collection."""
        collection = QuoteCollection()

        assert len(collection.quotes) == 0
        assert collection.total_count == 0
        assert collection.valid_count == 0

    def test_add_quote(self):
        """Test adding quote to collection."""
        collection = QuoteCollection()

        quote = MarketQuote(
            symbol="AAPL:US",
            name="Apple Inc.",
            price=175.50,
            timestamp=datetime.utcnow(),
            source=DataSource.BLOOMBERG,
            asset_class=AssetClass.STOCKS,
        )

        collection.add_quote(quote)

        assert collection.total_count == 1
        assert collection.valid_count == 1

    def test_get_valid_quotes(self):
        """Test filtering valid quotes."""
        collection = QuoteCollection()

        # Add valid quote
        valid_quote = MarketQuote(
            symbol="AAPL:US",
            name="Apple Inc.",
            price=175.50,
            timestamp=datetime.utcnow(),
            source=DataSource.BLOOMBERG,
            asset_class=AssetClass.STOCKS,
        )
        collection.add_quote(valid_quote)

        # Add invalid quote (low confidence)
        invalid_quote = MarketQuote(
            symbol="TEST",
            name="Test",
            price=100.0,
            timestamp=datetime.utcnow(),
            source=DataSource.CACHE,
            asset_class=AssetClass.STOCKS,
            confidence_score=0.3,
        )
        collection.add_quote(invalid_quote)

        valid_quotes = collection.get_valid_quotes()

        assert len(valid_quotes) == 1
        assert valid_quotes[0].symbol == "AAPL:US"

    def test_get_by_symbol(self):
        """Test retrieving quote by symbol."""
        collection = QuoteCollection()

        quote1 = MarketQuote(
            symbol="AAPL:US",
            name="Apple Inc.",
            price=175.50,
            timestamp=datetime.utcnow(),
            source=DataSource.BLOOMBERG,
            asset_class=AssetClass.STOCKS,
        )

        quote2 = MarketQuote(
            symbol="MSFT:US",
            name="Microsoft Corp.",
            price=380.25,
            timestamp=datetime.utcnow(),
            source=DataSource.BLOOMBERG,
            asset_class=AssetClass.STOCKS,
        )

        collection.add_quote(quote1)
        collection.add_quote(quote2)

        found_quote = collection.get_by_symbol("MSFT:US")

        assert found_quote is not None
        assert found_quote.symbol == "MSFT:US"

    def test_get_by_symbol_case_insensitive(self):
        """Test symbol lookup is case-insensitive."""
        collection = QuoteCollection()

        quote = MarketQuote(
            symbol="AAPL:US",
            name="Apple Inc.",
            price=175.50,
            timestamp=datetime.utcnow(),
            source=DataSource.BLOOMBERG,
            asset_class=AssetClass.STOCKS,
        )
        collection.add_quote(quote)

        found_quote = collection.get_by_symbol("aapl:us")

        assert found_quote is not None
        assert found_quote.symbol == "AAPL:US"

    def test_to_dataframe(self):
        """Test conversion to pandas DataFrame."""
        collection = QuoteCollection()

        quote1 = MarketQuote(
            symbol="AAPL:US",
            name="Apple Inc.",
            price=175.50,
            timestamp=datetime.utcnow(),
            source=DataSource.BLOOMBERG,
            asset_class=AssetClass.STOCKS,
        )

        quote2 = MarketQuote(
            symbol="MSFT:US",
            name="Microsoft Corp.",
            price=380.25,
            timestamp=datetime.utcnow(),
            source=DataSource.BLOOMBERG,
            asset_class=AssetClass.STOCKS,
        )

        collection.add_quote(quote1)
        collection.add_quote(quote2)

        df = collection.to_dataframe()

        assert len(df) == 2
        assert "symbol" in df.columns
        assert "price" in df.columns
        assert df.iloc[0]["symbol"] == "AAPL:US"
        assert df.iloc[1]["symbol"] == "MSFT:US"
