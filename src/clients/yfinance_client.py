"""
YFinance Client Module

Provides a wrapper around the yfinance library for fetching financial data
from Yahoo Finance. This is a free data source supporting stocks, forex,
and select commodities.

Key Features:
    - Zero-cost data access (no API key required)
    - Support for stocks, forex, and commodities
    - Data normalization to standard format
    - Error handling with custom exceptions
    - Bulk symbol fetching with error isolation

Supported Assets:
    - Stocks: AAPL, MSFT, GOOGL, etc.
    - FX: EURUSD=X, GBPUSD=X, etc.
    - Commodities: GC=F (Gold), CL=F (Crude Oil), SI=F (Silver)
"""

from datetime import datetime, timezone
from typing import Any, Optional

import pandas as pd
import yfinance as yf

from ..utils.exceptions import APIError


class YFinanceClient:
    """Client for fetching financial data from Yahoo Finance via yfinance library.

    This client wraps the yfinance library to provide consistent error handling
    and data normalization. All data is returned in a standardized format
    regardless of asset type.

    Attributes:
        timeout: Request timeout in seconds
        session: Optional requests.Session for connection pooling

    Example:
        >>> client = YFinanceClient()
        >>> quote = client.fetch_quote("AAPL")
        >>> print(quote['price'])
        150.25

        >>> history = client.fetch_history("MSFT", period="1mo")
        >>> print(history.tail())
    """

    def __init__(self, timeout: int = 10):
        """Initialize YFinance client.

        Args:
            timeout: Request timeout in seconds (default: 10)
        """
        self.timeout = timeout
        self.session = None

    def fetch_quote(self, symbol: str) -> Optional[dict[str, Any]]:
        """Fetch current quote for a single symbol.

        Retrieves current market data including price, volume, market cap,
        and daily range. Data is normalized to a standard format.

        Args:
            symbol: Ticker symbol (e.g., 'AAPL', 'EURUSD=X', 'GC=F')

        Returns:
            Normalized quote dictionary with standardized fields, or None if fetch fails

        Raises:
            APIError: If yfinance request fails or returns invalid data

        Example:
            >>> client = YFinanceClient()
            >>> quote = client.fetch_quote("AAPL")
            >>> print(f"{quote['symbol']}: ${quote['price']}")
            AAPL: $150.25
        """
        try:
            ticker = yf.Ticker(symbol, session=self.session)
            info = ticker.info

            # Check if valid data was returned
            if not info or 'regularMarketPrice' not in info:
                # Try fast_info as fallback
                try:
                    fast_info = ticker.fast_info
                    return self._normalize_fast_info(symbol, fast_info)
                except Exception:
                    return None

            return self._normalize_quote(symbol, info)

        except Exception as e:
            raise APIError(
                message=f"Failed to fetch quote for {symbol}",
                endpoint=f"yfinance.Ticker({symbol})",
                response_body=str(e),
                request_params={"symbol": symbol}
            ) from e

    def fetch_history(
        self,
        symbol: str,
        period: str = "1d",
        interval: str = "1d"
    ) -> Optional[pd.DataFrame]:
        """Fetch historical price data for a symbol.

        Retrieves OHLCV (Open, High, Low, Close, Volume) data for the
        specified time period and interval.

        Args:
            symbol: Ticker symbol (e.g., 'AAPL', 'EURUSD=X')
            period: Time period (valid: 1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max)
            interval: Data interval (valid: 1m, 2m, 5m, 15m, 30m, 60m, 90m, 1h, 1d, 5d, 1wk, 1mo, 3mo)

        Returns:
            DataFrame with OHLCV data indexed by timestamp, or None if fetch fails

        Raises:
            APIError: If yfinance request fails

        Example:
            >>> client = YFinanceClient()
            >>> history = client.fetch_history("MSFT", period="1mo", interval="1d")
            >>> print(history[['Open', 'Close', 'Volume']].tail())
        """
        try:
            ticker = yf.Ticker(symbol, session=self.session)
            hist = ticker.history(period=period, interval=interval, timeout=self.timeout)

            if hist.empty:
                return None

            # Ensure timezone-aware datetime index
            if hist.index.tz is None:
                hist.index = hist.index.tz_localize('UTC')
            else:
                hist.index = hist.index.tz_convert('UTC')

            # Add symbol column for reference
            hist['Symbol'] = symbol

            return hist

        except Exception as e:
            raise APIError(
                message=f"Failed to fetch history for {symbol}",
                endpoint=f"yfinance.Ticker({symbol}).history",
                response_body=str(e),
                request_params={"symbol": symbol, "period": period, "interval": interval}
            ) from e

    def fetch_multiple(self, symbols: list[str]) -> dict[str, Optional[dict[str, Any]]]:
        """Fetch quotes for multiple symbols in bulk.

        Fetches data for multiple symbols, isolating errors so that failures
        for one symbol don't affect others. This is more efficient than
        calling fetch_quote() in a loop.

        Args:
            symbols: List of ticker symbols

        Returns:
            Dictionary mapping symbol to quote data (or None if fetch failed)

        Example:
            >>> client = YFinanceClient()
            >>> quotes = client.fetch_multiple(["AAPL", "MSFT", "GOOGL"])
            >>> for symbol, quote in quotes.items():
            ...     if quote:
            ...         print(f"{symbol}: ${quote['price']}")
        """
        results: dict[str, Optional[dict[str, Any]]] = {}

        for symbol in symbols:
            try:
                results[symbol] = self.fetch_quote(symbol)
            except APIError:
                # Isolate errors - one failure shouldn't break the batch
                results[symbol] = None

        return results

    def _normalize_quote(self, symbol: str, info: dict[str, Any]) -> dict[str, Any]:
        """Normalize yfinance info dict to standard format.

        Args:
            symbol: Ticker symbol
            info: Raw info dictionary from yfinance

        Returns:
            Normalized quote dictionary
        """
        # Extract current price (try multiple fields)
        price = (
            info.get('regularMarketPrice') or
            info.get('currentPrice') or
            info.get('previousClose') or
            0.0
        )

        # Calculate change and percent change
        previous_close = info.get('previousClose', price)
        change = price - previous_close if previous_close else 0.0
        change_percent = (change / previous_close * 100) if previous_close else 0.0

        return {
            'symbol': symbol,
            'name': info.get('longName') or info.get('shortName') or symbol,
            'price': float(price),
            'change': float(change),
            'change_percent': float(change_percent),
            'volume': int(info.get('volume') or info.get('regularMarketVolume') or 0),
            'market_cap': int(info.get('marketCap', 0)),
            'day_high': float(info.get('dayHigh') or info.get('regularMarketDayHigh') or 0),
            'day_low': float(info.get('dayLow') or info.get('regularMarketDayLow') or 0),
            'year_high': float(info.get('fiftyTwoWeekHigh', 0)),
            'year_low': float(info.get('fiftyTwoWeekLow', 0)),
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'source': 'yfinance'
        }

    def _normalize_fast_info(self, symbol: str, fast_info: Any) -> dict[str, Any]:
        """Normalize yfinance fast_info to standard format.

        Used as fallback when full info is unavailable. Provides limited
        data but faster response times.

        Args:
            symbol: Ticker symbol
            fast_info: Fast info object from yfinance

        Returns:
            Normalized quote dictionary with available fields
        """
        price = getattr(fast_info, 'last_price', 0.0)
        previous_close = getattr(fast_info, 'previous_close', price)
        change = price - previous_close if previous_close else 0.0
        change_percent = (change / previous_close * 100) if previous_close else 0.0

        return {
            'symbol': symbol,
            'name': symbol,  # Fast info doesn't include name
            'price': float(price),
            'change': float(change),
            'change_percent': float(change_percent),
            'volume': int(getattr(fast_info, 'last_volume', 0)),
            'market_cap': int(getattr(fast_info, 'market_cap', 0)),
            'day_high': float(getattr(fast_info, 'day_high', 0)),
            'day_low': float(getattr(fast_info, 'day_low', 0)),
            'year_high': float(getattr(fast_info, 'year_high', 0)),
            'year_low': float(getattr(fast_info, 'year_low', 0)),
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'source': 'yfinance'
        }

    def __enter__(self):
        """Context manager entry - creates persistent session."""
        import requests
        self.session = requests.Session()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - closes session."""
        if self.session:
            self.session.close()
            self.session = None
