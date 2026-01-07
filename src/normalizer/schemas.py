"""
Data schemas for normalized market data.

Pydantic models providing type safety, validation, and serialization
for multi-source financial data.
"""

import json
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


class AssetClass(str, Enum):
    """Asset classification categories."""

    STOCKS = "stocks"
    FOREX = "forex"
    COMMODITIES = "commodities"
    BONDS = "bonds"
    CRYPTO = "crypto"
    INDICES = "indices"
    ETF = "etf"
    FUTURES = "futures"
    OPTIONS = "options"


class DataSource(str, Enum):
    """Data provider sources."""

    BLOOMBERG = "bloomberg"
    YFINANCE = "yfinance"
    FINNHUB = "finnhub"
    ALPHA_VANTAGE = "alpha_vantage"
    CACHE = "cache"
    MANUAL = "manual"


class MarketStatus(str, Enum):
    """Trading status indicators."""

    OPEN = "open"
    CLOSED = "closed"
    PRE_MARKET = "pre_market"
    POST_MARKET = "post_market"
    HALTED = "halted"
    UNKNOWN = "unknown"


class MarketQuote(BaseModel):
    """
    Normalized market quote data model.

    Standardizes data from multiple sources (Bloomberg, yfinance, Finnhub)
    into a consistent format for storage and analysis.
    """

    # Required fields
    symbol: str = Field(..., description="Trading symbol (e.g., AAPL:US, EUR/USD)")
    name: str = Field(..., description="Full security name")
    price: float = Field(..., description="Current/latest price", gt=0)
    timestamp: datetime = Field(..., description="Quote timestamp (UTC)")
    source: DataSource = Field(..., description="Data provider source")
    asset_class: AssetClass = Field(..., description="Asset classification")

    # Price changes
    change: Optional[float] = Field(None, description="Absolute price change")
    change_percent: Optional[float] = Field(None, description="Percentage change")

    # Trading volume
    volume: Optional[float] = Field(None, description="Trading volume", ge=0)
    volume_avg: Optional[float] = Field(None, description="Average volume", ge=0)

    # Market metrics
    market_cap: Optional[float] = Field(None, description="Market capitalization", ge=0)
    shares_outstanding: Optional[float] = Field(None, description="Shares outstanding", ge=0)

    # Price range
    day_high: Optional[float] = Field(None, description="Day high price", gt=0)
    day_low: Optional[float] = Field(None, description="Day low price", gt=0)
    week_52_high: Optional[float] = Field(None, description="52-week high", gt=0)
    week_52_low: Optional[float] = Field(None, description="52-week low", gt=0)

    # Trading session info
    open_price: Optional[float] = Field(None, description="Opening price", gt=0)
    previous_close: Optional[float] = Field(None, description="Previous close price", gt=0)
    market_status: Optional[MarketStatus] = Field(None, description="Current market status")

    # Valuation metrics
    pe_ratio: Optional[float] = Field(None, description="Price-to-earnings ratio")
    eps: Optional[float] = Field(None, description="Earnings per share")
    dividend_yield: Optional[float] = Field(None, description="Dividend yield %", ge=0)
    beta: Optional[float] = Field(None, description="Beta coefficient")

    # Forex-specific
    bid: Optional[float] = Field(None, description="Bid price", gt=0)
    ask: Optional[float] = Field(None, description="Ask price", gt=0)
    spread: Optional[float] = Field(None, description="Bid-ask spread", ge=0)

    # Metadata
    currency: Optional[str] = Field(None, description="Price currency (e.g., USD)")
    exchange: Optional[str] = Field(None, description="Exchange name")
    sector: Optional[str] = Field(None, description="Industry sector")
    industry: Optional[str] = Field(None, description="Industry classification")

    # Data quality
    data_freshness_seconds: Optional[int] = Field(None, description="Age of data in seconds", ge=0)
    confidence_score: Optional[float] = Field(None, description="Data quality score", ge=0, le=1)

    # Internal tracking
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Record creation time")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Last update time")

    model_config = {
        "json_schema_extra": {
            "example": {
                "symbol": "AAPL:US",
                "name": "Apple Inc.",
                "price": 175.50,
                "timestamp": "2024-01-15T16:00:00Z",
                "source": "bloomberg",
                "asset_class": "stocks",
                "change": 2.50,
                "change_percent": 1.45,
                "volume": 52000000,
                "market_cap": 2750000000000,
                "currency": "USD",
                "exchange": "NASDAQ",
            }
        }
    }

    @field_validator("symbol")
    @classmethod
    def validate_symbol(cls, v: str) -> str:
        """Ensure symbol is uppercase and non-empty."""
        if not v or not v.strip():
            raise ValueError("Symbol cannot be empty")
        return v.strip().upper()

    @field_validator("timestamp", "created_at", "updated_at")
    @classmethod
    def validate_timestamp(cls, v: datetime) -> datetime:
        """Ensure timestamp is timezone-aware UTC."""
        if v.tzinfo is None:
            # Assume UTC if no timezone
            return v.replace(tzinfo=None)  # Store as UTC naive
        return v

    @model_validator(mode="after")
    def validate_price_ranges(self) -> "MarketQuote":
        """Validate logical consistency of price ranges."""
        # Check day high/low consistency
        if self.day_high is not None and self.day_low is not None:
            if self.day_low > self.day_high:
                raise ValueError("day_low cannot exceed day_high")
            if not (self.day_low <= self.price <= self.day_high):
                # Allow some tolerance for pre/post market
                if self.market_status not in [MarketStatus.PRE_MARKET, MarketStatus.POST_MARKET]:
                    pass  # Log warning but don't fail

        # Check 52-week high/low consistency
        if self.week_52_high is not None and self.week_52_low is not None:
            if self.week_52_low > self.week_52_high:
                raise ValueError("week_52_low cannot exceed week_52_high")

        # Calculate change_percent if change and previous_close are available
        if self.change is not None and self.previous_close is not None and self.previous_close > 0:
            calculated_pct = (self.change / self.previous_close) * 100
            if self.change_percent is None:
                self.change_percent = round(calculated_pct, 2)

        # Calculate spread if bid and ask are available
        if self.bid is not None and self.ask is not None:
            if self.spread is None:
                self.spread = round(self.ask - self.bid, 6)

        return self

    def is_valid(self) -> bool:
        """
        Check if the quote has minimum required data quality.

        Returns:
            bool: True if quote meets quality standards
        """
        # Must have basic required fields (enforced by Pydantic)
        if not all([self.symbol, self.name, self.price, self.timestamp]):
            return False

        # Price must be positive
        if self.price <= 0:
            return False

        # Check data freshness if available
        if self.data_freshness_seconds is not None:
            # Consider stale if older than 1 hour (3600 seconds)
            if self.data_freshness_seconds > 3600:
                return False

        # Check confidence score if available
        if self.confidence_score is not None:
            # Require at least 50% confidence
            if self.confidence_score < 0.5:
                return False

        return True

    def to_csv_row(self) -> dict[str, Any]:
        """
        Convert to flat dictionary for CSV export.

        Returns:
            dict: Flattened data suitable for CSV writing
        """
        return {
            "symbol": self.symbol,
            "name": self.name,
            "price": self.price,
            "timestamp": self.timestamp.isoformat(),
            "source": self.source.value,
            "asset_class": self.asset_class.value,
            "change": self.change,
            "change_percent": self.change_percent,
            "volume": self.volume,
            "market_cap": self.market_cap,
            "day_high": self.day_high,
            "day_low": self.day_low,
            "open_price": self.open_price,
            "previous_close": self.previous_close,
            "market_status": self.market_status.value if self.market_status else None,
            "pe_ratio": self.pe_ratio,
            "eps": self.eps,
            "dividend_yield": self.dividend_yield,
            "beta": self.beta,
            "currency": self.currency,
            "exchange": self.exchange,
            "sector": self.sector,
            "industry": self.industry,
        }

    def to_json(self, **kwargs) -> str:
        """
        Serialize to JSON string.

        Args:
            **kwargs: Additional arguments for json.dumps

        Returns:
            str: JSON-formatted string
        """
        return self.model_dump_json(**kwargs)

    def to_dict(self) -> dict[str, Any]:
        """
        Convert to dictionary with enum values serialized.

        Returns:
            dict: Python dictionary representation
        """
        return self.model_dump(mode="python")

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MarketQuote":
        """
        Create instance from dictionary.

        Args:
            data: Dictionary with quote data

        Returns:
            MarketQuote: Validated instance
        """
        return cls(**data)

    def calculate_data_age(self) -> int:
        """
        Calculate age of data in seconds from current time.

        Returns:
            int: Seconds since timestamp
        """
        now = datetime.utcnow()
        delta = now - self.timestamp
        return int(delta.total_seconds())

    def is_fresh(self, max_age_seconds: int = 900) -> bool:
        """
        Check if data is fresh (within specified age).

        Args:
            max_age_seconds: Maximum acceptable age in seconds (default: 15 minutes)

        Returns:
            bool: True if data is fresh
        """
        age = self.calculate_data_age()
        return age <= max_age_seconds

    def get_display_name(self) -> str:
        """
        Get formatted display name for UI.

        Returns:
            str: Formatted name with symbol
        """
        return f"{self.name} ({self.symbol})"

    def __str__(self) -> str:
        """String representation."""
        return (
            f"{self.symbol}: ${self.price:.2f} "
            f"({self.change_percent:+.2f}% @ {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')})"
        )

    def __repr__(self) -> str:
        """Developer-friendly representation."""
        return (
            f"MarketQuote(symbol={self.symbol!r}, price={self.price}, "
            f"source={self.source.value}, timestamp={self.timestamp})"
        )


class QuoteCollection(BaseModel):
    """Collection of market quotes with metadata."""

    quotes: list[MarketQuote] = Field(default_factory=list, description="List of quotes")
    collected_at: datetime = Field(default_factory=datetime.utcnow, description="Collection timestamp")
    source: Optional[DataSource] = Field(None, description="Primary data source")
    total_count: int = Field(0, description="Total number of quotes")
    valid_count: int = Field(0, description="Number of valid quotes")

    @model_validator(mode="after")
    def update_counts(self) -> "QuoteCollection":
        """Update count fields based on quotes list."""
        self.total_count = len(self.quotes)
        self.valid_count = sum(1 for q in self.quotes if q.is_valid())
        return self

    def add_quote(self, quote: MarketQuote) -> None:
        """Add a quote to the collection."""
        self.quotes.append(quote)
        self.total_count = len(self.quotes)
        self.valid_count = sum(1 for q in self.quotes if q.is_valid())

    def get_valid_quotes(self) -> list[MarketQuote]:
        """Get only valid quotes."""
        return [q for q in self.quotes if q.is_valid()]

    def get_by_symbol(self, symbol: str) -> Optional[MarketQuote]:
        """Get quote by symbol."""
        symbol = symbol.upper().strip()
        for quote in self.quotes:
            if quote.symbol == symbol:
                return quote
        return None

    def to_dataframe(self):
        """
        Convert to pandas DataFrame.

        Returns:
            pd.DataFrame: DataFrame with all quotes
        """
        import pandas as pd

        if not self.quotes:
            return pd.DataFrame()

        data = [q.to_csv_row() for q in self.quotes]
        return pd.DataFrame(data)
