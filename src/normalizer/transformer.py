"""
Data transformation module for normalizing multi-source financial data.

Transforms raw data from Bloomberg, yfinance, Finnhub, and other sources
into standardized MarketQuote objects.
"""

import re
from datetime import datetime, timezone
from typing import Any, Optional

from ..utils.exceptions import DataNormalizationError
from .schemas import AssetClass, DataSource, MarketQuote, MarketStatus


class DataTransformer:
    """
    Transform and normalize data from multiple financial data sources.

    Handles field mapping, type conversion, and data validation for
    Bloomberg, yfinance, Finnhub, and Alpha Vantage data formats.
    """

    # Bloomberg field mapping
    BLOOMBERG_FIELD_MAP = {
        "price": ["last_price", "price", "last", "value"],
        "name": ["name", "security_name", "longName", "securityName"],
        "change": ["change", "price_change", "netChange", "net_change"],
        "change_percent": [
            "change_percent",
            "pct_change",
            "percentChange",
            "percent_change",
        ],
        "volume": ["volume", "totalVolume", "total_volume"],
        "market_cap": ["market_cap", "marketCap", "mktCap"],
        "open": ["open", "open_price", "openPrice"],
        "high": ["high", "day_high", "dayHigh", "highPrice"],
        "low": ["low", "day_low", "dayLow", "lowPrice"],
        "previous_close": [
            "previous_close",
            "previousClose",
            "prev_close",
            "prevClose",
        ],
        "pe_ratio": ["pe_ratio", "peRatio", "PE", "price_earnings"],
        "eps": ["eps", "earningsPerShare", "earnings_per_share"],
        "dividend_yield": ["dividend_yield", "dividendYield", "yield"],
        "beta": ["beta"],
        "52_week_high": ["week_52_high", "52WeekHigh", "fiftyTwoWeekHigh"],
        "52_week_low": ["week_52_low", "52WeekLow", "fiftyTwoWeekLow"],
    }

    # yfinance field mapping
    YFINANCE_FIELD_MAP = {
        "price": ["currentPrice", "regularMarketPrice", "price"],
        "name": ["longName", "shortName"],
        "change": ["regularMarketChange"],
        "change_percent": ["regularMarketChangePercent"],
        "volume": ["regularMarketVolume", "volume"],
        "market_cap": ["marketCap"],
        "open": ["regularMarketOpen", "open"],
        "high": ["regularMarketDayHigh", "dayHigh"],
        "low": ["regularMarketDayLow", "dayLow"],
        "previous_close": ["regularMarketPreviousClose", "previousClose"],
        "pe_ratio": ["trailingPE", "forwardPE"],
        "eps": ["trailingEps", "forwardEps"],
        "dividend_yield": ["dividendYield"],
        "beta": ["beta"],
        "52_week_high": ["fiftyTwoWeekHigh"],
        "52_week_low": ["fiftyTwoWeekLow"],
        "currency": ["currency", "financialCurrency"],
        "exchange": ["exchange", "exchangeName"],
        "sector": ["sector"],
        "industry": ["industry"],
    }

    # Finnhub field mapping
    FINNHUB_FIELD_MAP = {
        "price": ["c", "current", "price"],  # 'c' = current price
        "change": ["d", "change"],  # 'd' = change
        "change_percent": ["dp", "percent_change"],  # 'dp' = percent change
        "high": ["h", "high"],  # 'h' = high
        "low": ["l", "low"],  # 'l' = low
        "open": ["o", "open"],  # 'o' = open
        "previous_close": ["pc", "previous_close"],  # 'pc' = previous close
    }

    @staticmethod
    def from_bloomberg(data: dict[str, Any], asset_class: AssetClass) -> MarketQuote:
        """
        Transform Bloomberg data to MarketQuote.

        Args:
            data: Raw Bloomberg data dictionary
            asset_class: Asset classification

        Returns:
            MarketQuote: Normalized quote object

        Raises:
            DataNormalizationError: If required fields are missing or invalid
        """
        try:
            # Extract required fields
            symbol = DataTransformer._extract_field(data, ["symbol", "ticker", "id"])
            if not symbol:
                raise DataNormalizationError("Missing required field: symbol")

            name = DataTransformer._extract_field(
                data, DataTransformer.BLOOMBERG_FIELD_MAP["name"]
            )
            if not name:
                name = symbol  # Fallback to symbol if name not available

            price = DataTransformer._extract_numeric(
                data, DataTransformer.BLOOMBERG_FIELD_MAP["price"]
            )
            if price is None or price <= 0:
                raise DataNormalizationError(f"Invalid or missing price for {symbol}")

            # Extract timestamp
            timestamp = DataTransformer.normalize_timestamp(
                DataTransformer._extract_field(
                    data, ["timestamp", "time", "date", "quote_time"]
                )
            )

            # Extract optional fields
            change = DataTransformer._extract_numeric(
                data, DataTransformer.BLOOMBERG_FIELD_MAP["change"]
            )
            change_percent = DataTransformer._extract_numeric(
                data, DataTransformer.BLOOMBERG_FIELD_MAP["change_percent"]
            )
            volume = DataTransformer._extract_numeric(
                data, DataTransformer.BLOOMBERG_FIELD_MAP["volume"]
            )
            market_cap = DataTransformer._extract_numeric(
                data, DataTransformer.BLOOMBERG_FIELD_MAP["market_cap"]
            )

            # Price range data
            day_high = DataTransformer._extract_numeric(
                data, DataTransformer.BLOOMBERG_FIELD_MAP["high"]
            )
            day_low = DataTransformer._extract_numeric(
                data, DataTransformer.BLOOMBERG_FIELD_MAP["low"]
            )
            open_price = DataTransformer._extract_numeric(
                data, DataTransformer.BLOOMBERG_FIELD_MAP["open"]
            )
            previous_close = DataTransformer._extract_numeric(
                data, DataTransformer.BLOOMBERG_FIELD_MAP["previous_close"]
            )

            # Valuation metrics
            pe_ratio = DataTransformer._extract_numeric(
                data, DataTransformer.BLOOMBERG_FIELD_MAP["pe_ratio"]
            )
            eps = DataTransformer._extract_numeric(
                data, DataTransformer.BLOOMBERG_FIELD_MAP["eps"]
            )
            dividend_yield = DataTransformer._extract_numeric(
                data, DataTransformer.BLOOMBERG_FIELD_MAP["dividend_yield"]
            )
            beta = DataTransformer._extract_numeric(
                data, DataTransformer.BLOOMBERG_FIELD_MAP["beta"]
            )

            # 52-week range
            week_52_high = DataTransformer._extract_numeric(
                data, DataTransformer.BLOOMBERG_FIELD_MAP["52_week_high"]
            )
            week_52_low = DataTransformer._extract_numeric(
                data, DataTransformer.BLOOMBERG_FIELD_MAP["52_week_low"]
            )

            # Metadata
            currency = DataTransformer._extract_field(data, ["currency", "ccy"])
            exchange = DataTransformer._extract_field(data, ["exchange", "market"])
            sector = DataTransformer._extract_field(data, ["sector", "gics_sector"])
            industry = DataTransformer._extract_field(
                data, ["industry", "gics_industry"]
            )

            # Market status
            market_status = DataTransformer._parse_market_status(
                DataTransformer._extract_field(data, ["market_status", "status"])
            )

            # Forex-specific fields
            bid = DataTransformer._extract_numeric(data, ["bid", "bid_price"])
            ask = DataTransformer._extract_numeric(data, ["ask", "ask_price"])

            return MarketQuote(
                symbol=symbol,
                name=name,
                price=price,
                timestamp=timestamp,
                source=DataSource.BLOOMBERG,
                asset_class=asset_class,
                change=change,
                change_percent=change_percent,
                volume=volume,
                market_cap=market_cap,
                day_high=day_high,
                day_low=day_low,
                open_price=open_price,
                previous_close=previous_close,
                pe_ratio=pe_ratio,
                eps=eps,
                dividend_yield=dividend_yield,
                beta=beta,
                week_52_high=week_52_high,
                week_52_low=week_52_low,
                currency=currency,
                exchange=exchange,
                sector=sector,
                industry=industry,
                market_status=market_status,
                bid=bid,
                ask=ask,
                confidence_score=0.95,  # Bloomberg data is high quality
            )

        except Exception as e:
            raise DataNormalizationError(
                f"Failed to normalize Bloomberg data: {str(e)}"
            ) from e

    @staticmethod
    def from_yfinance(data: dict[str, Any], asset_class: AssetClass) -> MarketQuote:
        """
        Transform yfinance data to MarketQuote.

        Args:
            data: Raw yfinance data dictionary (from ticker.info or ticker.history)
            asset_class: Asset classification

        Returns:
            MarketQuote: Normalized quote object

        Raises:
            DataNormalizationError: If required fields are missing or invalid
        """
        try:
            # Extract required fields
            symbol = DataTransformer._extract_field(data, ["symbol", "ticker"])
            if not symbol:
                raise DataNormalizationError("Missing required field: symbol")

            # yfinance uses different field names for info vs history data
            name = DataTransformer._extract_field(
                data, DataTransformer.YFINANCE_FIELD_MAP["name"]
            )
            if not name:
                name = symbol

            # Try different price field names
            price = DataTransformer._extract_numeric(
                data, DataTransformer.YFINANCE_FIELD_MAP["price"]
            )
            if price is None or price <= 0:
                # Try 'Close' for historical data
                price = DataTransformer._extract_numeric(data, ["Close", "close"])
                if price is None or price <= 0:
                    raise DataNormalizationError(
                        f"Invalid or missing price for {symbol}"
                    )

            # Extract timestamp
            timestamp = DataTransformer.normalize_timestamp(
                DataTransformer._extract_field(
                    data, ["regularMarketTime", "timestamp", "Date", "date"]
                )
            )

            # Extract optional fields
            change = DataTransformer._extract_numeric(
                data, DataTransformer.YFINANCE_FIELD_MAP["change"]
            )
            change_percent = DataTransformer._extract_numeric(
                data, DataTransformer.YFINANCE_FIELD_MAP["change_percent"]
            )

            # Convert decimal percentage to percentage (yfinance gives 0.0145 for 1.45%)
            if change_percent is not None and abs(change_percent) < 1:
                change_percent = change_percent * 100

            volume = DataTransformer._extract_numeric(
                data, DataTransformer.YFINANCE_FIELD_MAP["volume"]
            )
            market_cap = DataTransformer._extract_numeric(
                data, DataTransformer.YFINANCE_FIELD_MAP["market_cap"]
            )

            # Price range
            day_high = DataTransformer._extract_numeric(
                data, DataTransformer.YFINANCE_FIELD_MAP["high"]
            )
            day_low = DataTransformer._extract_numeric(
                data, DataTransformer.YFINANCE_FIELD_MAP["low"]
            )
            open_price = DataTransformer._extract_numeric(
                data, DataTransformer.YFINANCE_FIELD_MAP["open"]
            )
            previous_close = DataTransformer._extract_numeric(
                data, DataTransformer.YFINANCE_FIELD_MAP["previous_close"]
            )

            # Valuation metrics
            pe_ratio = DataTransformer._extract_numeric(
                data, DataTransformer.YFINANCE_FIELD_MAP["pe_ratio"]
            )
            eps = DataTransformer._extract_numeric(
                data, DataTransformer.YFINANCE_FIELD_MAP["eps"]
            )
            dividend_yield = DataTransformer._extract_numeric(
                data, DataTransformer.YFINANCE_FIELD_MAP["dividend_yield"]
            )

            # Convert decimal yield to percentage if needed
            if dividend_yield is not None and dividend_yield < 1:
                dividend_yield = dividend_yield * 100

            beta = DataTransformer._extract_numeric(
                data, DataTransformer.YFINANCE_FIELD_MAP["beta"]
            )

            # 52-week range
            week_52_high = DataTransformer._extract_numeric(
                data, DataTransformer.YFINANCE_FIELD_MAP["52_week_high"]
            )
            week_52_low = DataTransformer._extract_numeric(
                data, DataTransformer.YFINANCE_FIELD_MAP["52_week_low"]
            )

            # Metadata
            currency = DataTransformer._extract_field(
                data, DataTransformer.YFINANCE_FIELD_MAP["currency"]
            )
            exchange = DataTransformer._extract_field(
                data, DataTransformer.YFINANCE_FIELD_MAP["exchange"]
            )
            sector = DataTransformer._extract_field(
                data, DataTransformer.YFINANCE_FIELD_MAP["sector"]
            )
            industry = DataTransformer._extract_field(
                data, DataTransformer.YFINANCE_FIELD_MAP["industry"]
            )

            # Market status from yfinance
            market_state = DataTransformer._extract_field(
                data, ["marketState", "market_state"]
            )
            market_status = DataTransformer._parse_market_status(market_state)

            # Bid/Ask for forex and options
            bid = DataTransformer._extract_numeric(data, ["bid", "bidPrice"])
            ask = DataTransformer._extract_numeric(data, ["ask", "askPrice"])

            return MarketQuote(
                symbol=symbol,
                name=name,
                price=price,
                timestamp=timestamp,
                source=DataSource.YFINANCE,
                asset_class=asset_class,
                change=change,
                change_percent=change_percent,
                volume=volume,
                market_cap=market_cap,
                day_high=day_high,
                day_low=day_low,
                open_price=open_price,
                previous_close=previous_close,
                pe_ratio=pe_ratio,
                eps=eps,
                dividend_yield=dividend_yield,
                beta=beta,
                week_52_high=week_52_high,
                week_52_low=week_52_low,
                currency=currency,
                exchange=exchange,
                sector=sector,
                industry=industry,
                market_status=market_status,
                bid=bid,
                ask=ask,
                confidence_score=0.85,  # yfinance is generally reliable
            )

        except Exception as e:
            raise DataNormalizationError(
                f"Failed to normalize yfinance data: {str(e)}"
            ) from e

    @staticmethod
    def from_finnhub(
        data: dict[str, Any], asset_class: AssetClass, symbol: str, name: str = None
    ) -> MarketQuote:
        """
        Transform Finnhub data to MarketQuote.

        Args:
            data: Raw Finnhub quote data (uses single-letter field names)
            asset_class: Asset classification
            symbol: Stock symbol (required as Finnhub doesn't include it in quotes)
            name: Company name (optional)

        Returns:
            MarketQuote: Normalized quote object

        Raises:
            DataNormalizationError: If required fields are missing or invalid
        """
        try:
            # Finnhub requires symbol to be passed separately
            if not symbol:
                raise DataNormalizationError("Symbol is required for Finnhub data")

            # Use provided name or default to symbol
            if not name:
                name = symbol

            # Extract price (Finnhub uses 'c' for current price)
            price = DataTransformer._extract_numeric(
                data, DataTransformer.FINNHUB_FIELD_MAP["price"]
            )
            if price is None or price <= 0:
                raise DataNormalizationError(f"Invalid or missing price for {symbol}")

            # Extract timestamp (Finnhub uses 't' for timestamp in Unix seconds)
            timestamp_val = DataTransformer._extract_field(data, ["t", "timestamp"])
            timestamp = DataTransformer.normalize_timestamp(timestamp_val)

            # Extract optional fields
            change = DataTransformer._extract_numeric(
                data, DataTransformer.FINNHUB_FIELD_MAP["change"]
            )
            change_percent = DataTransformer._extract_numeric(
                data, DataTransformer.FINNHUB_FIELD_MAP["change_percent"]
            )

            # Price range (day)
            day_high = DataTransformer._extract_numeric(
                data, DataTransformer.FINNHUB_FIELD_MAP["high"]
            )
            day_low = DataTransformer._extract_numeric(
                data, DataTransformer.FINNHUB_FIELD_MAP["low"]
            )
            open_price = DataTransformer._extract_numeric(
                data, DataTransformer.FINNHUB_FIELD_MAP["open"]
            )
            previous_close = DataTransformer._extract_numeric(
                data, DataTransformer.FINNHUB_FIELD_MAP["previous_close"]
            )

            return MarketQuote(
                symbol=symbol,
                name=name,
                price=price,
                timestamp=timestamp,
                source=DataSource.FINNHUB,
                asset_class=asset_class,
                change=change,
                change_percent=change_percent,
                day_high=day_high,
                day_low=day_low,
                open_price=open_price,
                previous_close=previous_close,
                confidence_score=0.80,  # Finnhub provides limited fields
            )

        except Exception as e:
            raise DataNormalizationError(
                f"Failed to normalize Finnhub data: {str(e)}"
            ) from e

    @staticmethod
    def normalize_timestamp(ts: Any) -> datetime:
        """
        Normalize various timestamp formats to datetime object.

        Args:
            ts: Timestamp in various formats (datetime, Unix timestamp, ISO string)

        Returns:
            datetime: Normalized UTC datetime object

        Raises:
            DataNormalizationError: If timestamp cannot be parsed
        """
        if ts is None:
            # Default to current time if not provided
            return datetime.utcnow()

        # Already a datetime object
        if isinstance(ts, datetime):
            # Ensure UTC
            if ts.tzinfo is None:
                return ts
            return ts.astimezone(timezone.utc).replace(tzinfo=None)

        # Unix timestamp (integer or float)
        if isinstance(ts, (int, float)):
            try:
                # Handle both seconds and milliseconds
                if ts > 1e10:  # Likely milliseconds
                    ts = ts / 1000
                return datetime.fromtimestamp(ts, tz=timezone.utc).replace(tzinfo=None)
            except (ValueError, OSError) as e:
                raise DataNormalizationError(f"Invalid Unix timestamp: {ts}") from e

        # ISO format string
        if isinstance(ts, str):
            # Try parsing ISO format
            for fmt in [
                "%Y-%m-%dT%H:%M:%S.%fZ",
                "%Y-%m-%dT%H:%M:%SZ",
                "%Y-%m-%dT%H:%M:%S",
                "%Y-%m-%d %H:%M:%S",
                "%Y-%m-%d",
            ]:
                try:
                    return datetime.strptime(ts, fmt)
                except ValueError:
                    continue

            # Try pandas/dateutil parsing as fallback
            try:
                import pandas as pd

                parsed = pd.to_datetime(ts, utc=True)
                return parsed.to_pydatetime().replace(tzinfo=None)
            except Exception as e:
                raise DataNormalizationError(
                    f"Unable to parse timestamp: {ts}"
                ) from e

        raise DataNormalizationError(f"Unsupported timestamp type: {type(ts)}")

    @staticmethod
    def normalize_number(value: Any) -> Optional[float]:
        """
        Normalize various numeric formats to float.

        Args:
            value: Numeric value in various formats (int, float, string, None)

        Returns:
            Optional[float]: Normalized float value or None
        """
        if value is None or value == "":
            return None

        # Already a number
        if isinstance(value, (int, float)):
            return float(value)

        # String representation
        if isinstance(value, str):
            # Remove common formatting (commas, currency symbols, percent signs)
            cleaned = value.strip()
            cleaned = re.sub(r"[$,€£¥%]", "", cleaned)
            cleaned = cleaned.replace(" ", "")

            # Handle special cases
            if cleaned.lower() in ["n/a", "na", "nan", "null", "none", "-"]:
                return None

            # Handle 'K', 'M', 'B', 'T' suffixes
            multiplier = 1.0
            if cleaned and cleaned[-1].upper() in ["K", "M", "B", "T"]:
                suffix = cleaned[-1].upper()
                cleaned = cleaned[:-1]
                multipliers = {"K": 1e3, "M": 1e6, "B": 1e9, "T": 1e12}
                multiplier = multipliers[suffix]

            try:
                return float(cleaned) * multiplier
            except ValueError:
                return None

        return None

    @staticmethod
    def _extract_field(data: dict[str, Any], field_names: list[str]) -> Optional[Any]:
        """
        Extract field from data dictionary trying multiple field names.

        Args:
            data: Source data dictionary
            field_names: List of possible field names to try

        Returns:
            Optional[Any]: Field value or None if not found
        """
        for field_name in field_names:
            if field_name in data and data[field_name] is not None:
                return data[field_name]
        return None

    @staticmethod
    def _extract_numeric(
        data: dict[str, Any], field_names: list[str]
    ) -> Optional[float]:
        """
        Extract and normalize numeric field from data dictionary.

        Args:
            data: Source data dictionary
            field_names: List of possible field names to try

        Returns:
            Optional[float]: Normalized numeric value or None
        """
        value = DataTransformer._extract_field(data, field_names)
        return DataTransformer.normalize_number(value)

    @staticmethod
    def _parse_market_status(status: Optional[str]) -> Optional[MarketStatus]:
        """
        Parse market status string to MarketStatus enum.

        Args:
            status: Market status string

        Returns:
            Optional[MarketStatus]: Parsed status or None
        """
        if not status:
            return None

        status_lower = status.lower().strip()

        # Map common status strings to enum values
        status_map = {
            "open": MarketStatus.OPEN,
            "regular": MarketStatus.OPEN,
            "trading": MarketStatus.OPEN,
            "closed": MarketStatus.CLOSED,
            "close": MarketStatus.CLOSED,
            "after-hours": MarketStatus.POST_MARKET,
            "post": MarketStatus.POST_MARKET,
            "post-market": MarketStatus.POST_MARKET,
            "aftermarket": MarketStatus.POST_MARKET,
            "pre-market": MarketStatus.PRE_MARKET,
            "pre": MarketStatus.PRE_MARKET,
            "premarket": MarketStatus.PRE_MARKET,
            "halted": MarketStatus.HALTED,
            "suspended": MarketStatus.HALTED,
            "paused": MarketStatus.HALTED,
        }

        return status_map.get(status_lower, MarketStatus.UNKNOWN)

    @staticmethod
    def infer_asset_class(symbol: str, data: dict[str, Any] = None) -> AssetClass:
        """
        Infer asset class from symbol and data.

        Args:
            symbol: Trading symbol
            data: Optional additional data to help classification

        Returns:
            AssetClass: Inferred asset class
        """
        symbol_upper = symbol.upper()

        # Check data for asset type hints first (most reliable)
        if data:
            asset_type = DataTransformer._extract_field(
                data, ["assetType", "asset_type", "type", "quoteType"]
            )
            if asset_type:
                asset_type_lower = str(asset_type).lower()
                if "forex" in asset_type_lower or "currency" in asset_type_lower:
                    return AssetClass.FOREX
                elif "etf" in asset_type_lower:
                    return AssetClass.ETF
                elif "option" in asset_type_lower:
                    return AssetClass.OPTIONS
                elif "future" in asset_type_lower:
                    return AssetClass.FUTURES
                elif "crypto" in asset_type_lower:
                    return AssetClass.CRYPTO
                elif "bond" in asset_type_lower:
                    return AssetClass.BONDS
                elif "commodity" in asset_type_lower:
                    return AssetClass.COMMODITIES

        # Crypto patterns (check before forex to avoid confusion)
        crypto_prefixes = ["BTC", "ETH", "XRP", "LTC", "ADA", "DOT", "DOGE"]
        if any(symbol_upper.startswith(prefix) for prefix in crypto_prefixes):
            return AssetClass.CRYPTO

        # Forex patterns (e.g., EUR/USD)
        if "/" in symbol_upper:
            return AssetClass.FOREX

        # 6-letter pure alpha without crypto prefix is likely forex (e.g., EURUSD)
        # But exclude if it has crypto prefix
        if len(symbol_upper) == 6 and symbol_upper.isalpha():
            if not any(symbol_upper.startswith(prefix) for prefix in crypto_prefixes):
                return AssetClass.FOREX

        # Futures patterns (e.g., ESZ23, CLF24)
        if re.match(r"^[A-Z]{1,3}[FGHJKMNQUVXZ]\d{2}$", symbol_upper):
            return AssetClass.FUTURES

        # Index patterns (e.g., ^GSPC, ^DJI)
        if symbol_upper.startswith("^"):
            return AssetClass.INDICES

        # Default to stocks
        return AssetClass.STOCKS
