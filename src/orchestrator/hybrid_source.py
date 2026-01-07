"""
Hybrid Data Source Orchestrator.

Priority-based data retrieval system that checks cache first,
then Bright Data (Bloomberg), with yfinance as fallback.
"""

import asyncio
import logging
from datetime import datetime
from typing import List, Optional

from src.clients.bright_data import BrightDataClient, BrightDataClientConfig
from src.clients.yfinance_client import YFinanceClient
from src.normalizer.schemas import AssetClass, MarketQuote
from src.normalizer.transformer import DataTransformer
from src.orchestrator.cache_manager import CacheManager
from src.orchestrator.circuit_breaker import CircuitBreaker, CircuitBreakerError
from src.orchestrator.cost_tracker import CostTracker
from src.parsers.bloomberg_parser import BloombergParser
from src.utils.exceptions import APIError, BudgetExhaustedError

logger = logging.getLogger(__name__)


class HybridDataSource:
    """
    Hybrid data source with priority-based retrieval.

    Retrieval Priority:
        1. Cache (cost: $0, TTL: 15 min)
        2. Bright Data (cost: $0.0015 per request, Bloomberg data)
        3. YFinance (cost: $0, fallback)

    Features:
        - Automatic fallback through data source hierarchy
        - Circuit breaker protection for each source
        - Comprehensive cost tracking and statistics
        - Configurable cache TTL and budget limits
        - Thread-safe operations with async support

    Example:
        >>> source = HybridDataSource()
        >>> quote = await source.get_quote("AAPL", AssetClass.STOCKS)
        >>> if quote:
        ...     print(f"{quote.symbol}: ${quote.price}")
        >>> stats = source.get_statistics()
        >>> print(f"Cache hit rate: {stats['cache_hit_rate_pct']}%")
    """

    def __init__(self):
        """Initialize hybrid data source with all components."""
        # Core components
        self.cache = CacheManager()
        self.yfinance = YFinanceClient()
        self.cost_tracker = CostTracker()

        # Bright Data client (initialized on demand)
        self._bright_data: Optional[BrightDataClient] = None

        # Circuit breakers for fault tolerance
        self.breakers = {
            "yfinance": CircuitBreaker("yfinance", failure_threshold=5, recovery_timeout=60),
            "bright_data": CircuitBreaker("bright_data", failure_threshold=3, recovery_timeout=120),
        }

        # Statistics tracking
        self._stats = {
            "cache_hits": 0,
            "cache_misses": 0,
            "yfinance_successes": 0,
            "yfinance_failures": 0,
            "bright_data_successes": 0,
            "bright_data_failures": 0,
            "total_requests": 0,
        }

        logger.info("HybridDataSource initialized with cache, yfinance, and Bright Data")

    async def _ensure_bright_data(self) -> BrightDataClient:
        """Lazy initialization of Bright Data client."""
        if self._bright_data is None:
            config = BrightDataClientConfig.from_env()
            self._bright_data = BrightDataClient(config, self.cost_tracker, self.cache)
        return self._bright_data

    def _convert_symbol_for_yfinance(self, symbol: str, asset_class: AssetClass) -> str:
        """
        Convert Bloomberg symbol format to yfinance format.

        Args:
            symbol: Bloomberg format symbol (e.g., "AAPL:US")
            asset_class: Asset classification

        Returns:
            yfinance-compatible symbol (e.g., "AAPL")
        """
        # Remove Bloomberg exchange suffix (e.g., ":US")
        base_symbol = symbol.split(":")[0]

        # Handle forex pairs
        if asset_class == AssetClass.FOREX:
            # Bloomberg: EUR/USD → yfinance: EURUSD=X
            if "/" in base_symbol:
                base_symbol = base_symbol.replace("/", "") + "=X"
            elif len(base_symbol) == 6:  # EURUSD format
                base_symbol = base_symbol + "=X"

        # Handle commodities
        elif asset_class == AssetClass.COMMODITIES:
            # Add futures suffix if not present
            if not base_symbol.endswith("=F"):
                base_symbol = base_symbol + "=F"

        return base_symbol

    def _convert_symbol_for_bloomberg(self, symbol: str, asset_class: AssetClass) -> str:
        """
        Convert symbol to Bloomberg URL format.

        Args:
            symbol: Base symbol
            asset_class: Asset classification

        Returns:
            Bloomberg URL-compatible symbol
        """
        # Bloomberg uses format like "AAPL:US"
        if ":" not in symbol:
            # Default to US exchange for stocks
            if asset_class == AssetClass.STOCKS:
                return f"{symbol}:US"
        return symbol

    async def get_quote(
        self,
        symbol: str,
        asset_class: AssetClass,
        force_fresh: bool = False,
    ) -> Optional[MarketQuote]:
        """
        Get market quote with priority-based data retrieval.

        Retrieval order:
            1. Cache (if not force_fresh)
            2. Bright Data (Bloomberg, paid)
            3. YFinance (fallback, free)

        Args:
            symbol: Trading symbol (Bloomberg format preferred)
            asset_class: Asset classification
            force_fresh: Skip cache and force fresh data retrieval

        Returns:
            MarketQuote if successful, None otherwise

        Example:
            >>> source = HybridDataSource()
            >>> quote = await source.get_quote("AAPL:US", AssetClass.STOCKS)
            >>> print(f"Source: {quote.source}, Price: ${quote.price}")
        """
        self._stats["total_requests"] += 1

        # Step 1: Check cache (unless force_fresh)
        if not force_fresh:
            cached_data = self.cache.get(asset_class.value, symbol)
            if cached_data:
                self._stats["cache_hits"] += 1
                logger.debug(f"Cache hit for {symbol}")
                try:
                    return MarketQuote.from_dict(cached_data)
                except Exception as e:
                    logger.warning(f"Failed to deserialize cached data for {symbol}: {e}")
                    # Continue to fresh data retrieval

        self._stats["cache_misses"] += 1

        # Step 2: Try Bright Data (primary source - Bloomberg data)
        if self.breakers["bright_data"].is_available():
            try:
                # Check budget before making paid request
                if not self.cost_tracker.can_make_request():
                    raise BudgetExhaustedError(
                        message="Cannot fetch from Bright Data - budget exhausted",
                        current_usage=self.cost_tracker.total_requests,
                        budget_limit=int(
                            self.cost_tracker.budget_limit
                            / self.cost_tracker.cost_per_request
                        ),
                        reset_time="Manual reset required",
                    )

                bloomberg_symbol = self._convert_symbol_for_bloomberg(symbol, asset_class)
                url = f"https://www.bloomberg.com/quote/{bloomberg_symbol}"

                logger.debug(f"Attempting Bright Data fetch for {bloomberg_symbol}")

                bright_data = await self._ensure_bright_data()
                html = await self.breakers["bright_data"].call(bright_data.fetch, url)

                if html:
                    # Parse Bloomberg HTML
                    parser = BloombergParser()
                    parsed_data = parser.parse_quote(html)

                    if parsed_data:
                        # Transform to MarketQuote
                        quote = DataTransformer.from_bloomberg(
                            {**parsed_data, "symbol": symbol}, asset_class
                        )

                        # Cache the result
                        self.cache.set(asset_class.value, symbol, quote.to_dict())

                        # Track the cost
                        self.cost_tracker.record_request(
                            asset_class=asset_class.value,
                            symbol=symbol,
                            success=True,
                        )
                        self._stats["bright_data_successes"] += 1

                        logger.info(
                            f"Successfully fetched {symbol} from Bright Data (cost: $0.0015)",
                            extra={
                                "source": "bright_data",
                                "symbol": symbol,
                                "price": quote.price,
                                "cost": 0.0015,
                            },
                        )
                        return quote

            except BudgetExhaustedError:
                logger.error(f"Budget exhausted - cannot fetch {symbol} from Bright Data")
                # Fall through to YFinance as fallback

            except CircuitBreakerError:
                logger.warning(f"Bright Data circuit breaker is open for {symbol}")
                self._stats["bright_data_failures"] += 1

            except APIError as e:
                logger.warning(f"Bright Data failed for {symbol}: {e}")
                self.cost_tracker.record_request(
                    asset_class=asset_class.value, symbol=symbol, success=False
                )
                self._stats["bright_data_failures"] += 1

            except Exception as e:
                logger.error(f"Unexpected error with Bright Data for {symbol}: {e}")
                self.cost_tracker.record_request(
                    asset_class=asset_class.value, symbol=symbol, success=False
                )
                self._stats["bright_data_failures"] += 1

        # Step 3: Try YFinance (fallback source)
        if self.breakers["yfinance"].is_available():
            try:
                yf_symbol = self._convert_symbol_for_yfinance(symbol, asset_class)
                logger.debug(f"Attempting yfinance fetch for {yf_symbol} (fallback)")

                yf_data = self.breakers["yfinance"].call(
                    self.yfinance.fetch_quote, yf_symbol
                )

                if yf_data:
                    # Transform to MarketQuote
                    quote = DataTransformer.from_yfinance(
                        {**yf_data, "symbol": symbol}, asset_class
                    )

                    # Cache the result
                    self.cache.set(asset_class.value, symbol, quote.to_dict())
                    self._stats["yfinance_successes"] += 1

                    logger.info(
                        f"Successfully fetched {symbol} from yfinance (fallback, cost: $0)",
                        extra={"source": "yfinance", "symbol": symbol, "price": quote.price},
                    )
                    return quote

            except CircuitBreakerError:
                logger.warning(f"YFinance circuit breaker is open for {symbol}")
                self._stats["yfinance_failures"] += 1

            except APIError as e:
                logger.warning(f"YFinance failed for {symbol}: {e}")
                self._stats["yfinance_failures"] += 1

            except Exception as e:
                logger.error(f"Unexpected error with yfinance for {symbol}: {e}")
                self._stats["yfinance_failures"] += 1

        # All sources failed
        logger.error(f"Failed to fetch {symbol} from all sources")
        return None

    async def get_quotes(
        self, symbols: List[str], asset_class: AssetClass
    ) -> List[MarketQuote]:
        """
        Fetch multiple quotes concurrently.

        Args:
            symbols: List of trading symbols
            asset_class: Asset classification for all symbols

        Returns:
            List of successfully fetched MarketQuote objects

        Example:
            >>> source = HybridDataSource()
            >>> symbols = ["AAPL:US", "MSFT:US", "GOOGL:US"]
            >>> quotes = await source.get_quotes(symbols, AssetClass.STOCKS)
            >>> print(f"Fetched {len(quotes)} quotes")
        """
        logger.info(f"Fetching {len(symbols)} quotes for {asset_class.value}")

        # Create tasks for concurrent fetching
        tasks = [self.get_quote(symbol, asset_class) for symbol in symbols]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Filter successful results
        quotes = []
        for result in results:
            if isinstance(result, MarketQuote):
                quotes.append(result)
            elif isinstance(result, Exception):
                logger.error(f"Error in concurrent fetch: {result}")

        logger.info(
            f"Successfully fetched {len(quotes)}/{len(symbols)} quotes",
            extra={
                "success_count": len(quotes),
                "total_count": len(symbols),
                "success_rate": round(len(quotes) / len(symbols) * 100, 2)
                if symbols
                else 0,
            },
        )

        return quotes

    def get_statistics(self) -> dict:
        """
        Get comprehensive statistics for hybrid data source.

        Returns:
            Dictionary with cache metrics, source usage, and cost information

        Example:
            >>> source = HybridDataSource()
            >>> stats = source.get_statistics()
            >>> print(f"Cache hit rate: {stats['cache_hit_rate_pct']}%")
            >>> print(f"Total cost: ${stats['cost_tracking']['total_cost']}")
        """
        total_cache_requests = self._stats["cache_hits"] + self._stats["cache_misses"]
        cache_hit_rate = (
            (self._stats["cache_hits"] / total_cache_requests * 100)
            if total_cache_requests > 0
            else 0
        )

        total_yfinance = (
            self._stats["yfinance_successes"] + self._stats["yfinance_failures"]
        )
        yfinance_success_rate = (
            (self._stats["yfinance_successes"] / total_yfinance * 100)
            if total_yfinance > 0
            else 0
        )

        total_bright_data = (
            self._stats["bright_data_successes"] + self._stats["bright_data_failures"]
        )
        bright_data_success_rate = (
            (self._stats["bright_data_successes"] / total_bright_data * 100)
            if total_bright_data > 0
            else 0
        )

        return {
            "total_requests": self._stats["total_requests"],
            "cache_statistics": {
                "hits": self._stats["cache_hits"],
                "misses": self._stats["cache_misses"],
                "hit_rate_pct": round(cache_hit_rate, 2),
                **self.cache.get_statistics(),
            },
            "source_usage": {
                "yfinance": {
                    "total_requests": total_yfinance,
                    "successes": self._stats["yfinance_successes"],
                    "failures": self._stats["yfinance_failures"],
                    "success_rate_pct": round(yfinance_success_rate, 2),
                    "cost_per_request": 0.0,
                    "total_cost": 0.0,
                    "circuit_breaker": self.breakers["yfinance"].get_statistics(),
                },
                "bright_data": {
                    "total_requests": total_bright_data,
                    "successes": self._stats["bright_data_successes"],
                    "failures": self._stats["bright_data_failures"],
                    "success_rate_pct": round(bright_data_success_rate, 2),
                    "cost_per_request": 0.0015,
                    "total_cost": round(self._stats["bright_data_successes"] * 0.0015, 4),
                    "circuit_breaker": self.breakers["bright_data"].get_statistics(),
                },
            },
            "cost_tracking": self.cost_tracker.get_statistics(),
        }

    def reset_statistics(self) -> dict:
        """
        Reset all statistics counters.

        Returns:
            Dictionary with pre-reset statistics
        """
        pre_reset_stats = self.get_statistics()

        self._stats = {
            "cache_hits": 0,
            "cache_misses": 0,
            "yfinance_successes": 0,
            "yfinance_failures": 0,
            "bright_data_successes": 0,
            "bright_data_failures": 0,
            "total_requests": 0,
        }

        logger.info("HybridDataSource statistics reset")
        return pre_reset_stats

    async def cleanup(self) -> None:
        """Cleanup resources and close connections."""
        if self._bright_data:
            await self._bright_data.close()
        self.cache.close()
        logger.info("HybridDataSource cleanup complete")

    def __repr__(self) -> str:
        """String representation for debugging."""
        return (
            f"HybridDataSource(requests={self._stats['total_requests']}, "
            f"cache_hits={self._stats['cache_hits']}, "
            f"yfinance={self._stats['yfinance_successes']}, "
            f"bright_data={self._stats['bright_data_successes']})"
        )
