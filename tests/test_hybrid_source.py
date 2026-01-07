"""
Unit tests for HybridDataSource orchestrator.

Tests cover:
    - Cache hit scenarios
    - YFinance fallback behavior
    - Bright Data fallback behavior
    - Cost-aware fallback logic
    - Circuit breaker integration
    - Multi-source failure handling
    - Statistics tracking
    - Concurrent request handling
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, Mock, patch

from src.normalizer.schemas import AssetClass, MarketQuote
from src.orchestrator.hybrid_source import HybridDataSource
from src.utils.exceptions import APIError, BudgetExhaustedError


@pytest.fixture
def mock_cache():
    """Mock CacheManager for testing."""
    cache = Mock()
    cache.get = Mock(return_value=None)
    cache.set = Mock(return_value=True)
    cache.get_statistics = Mock(return_value={
        'total_entries': 0,
        'expired_entries': 0,
        'valid_entries': 0,
        'total_hits': 0,
        'average_hits': 0.0
    })
    return cache


@pytest.fixture
def mock_yfinance():
    """Mock YFinanceClient for testing."""
    client = Mock()
    client.fetch_quote = Mock(return_value={
        'symbol': 'AAPL',
        'shortName': 'Apple Inc.',
        'regularMarketPrice': 185.50,
        'regularMarketChange': 2.35,
        'regularMarketChangePercent': 1.28,
        'regularMarketVolume': 45678900,
        'marketCap': 2850000000000,
        'currency': 'USD'
    })
    return client


@pytest.fixture
def mock_bright_data():
    """Mock BrightDataClient for testing."""
    client = Mock()

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
                "priceCurrency": "USD",
                "volume": 45678900
            }
            </script>
        </head>
        </html>
        """

    client.fetch = AsyncMock(side_effect=mock_fetch)
    return client


@pytest.fixture
def hybrid_source(mock_cache, mock_yfinance, mock_cost_tracker):
    """Create HybridDataSource instance with mocked dependencies."""
    with patch('src.orchestrator.hybrid_source.CacheManager', return_value=mock_cache), \
         patch('src.orchestrator.hybrid_source.YFinanceClient', return_value=mock_yfinance), \
         patch('src.orchestrator.hybrid_source.CostTracker', return_value=mock_cost_tracker):

        source = HybridDataSource()
        return source


class TestCacheHitScenarios:
    """Test cache hit scenarios and cache-first behavior."""

    @pytest.mark.asyncio
    async def test_cache_hit_returns_cached_data(self, hybrid_source, mock_cache, mock_market_quote):
        """Test that cache hit returns cached data without calling other sources."""
        # Setup cache to return data
        mock_cache.get.return_value = mock_market_quote.to_dict()

        # Get quote
        result = await hybrid_source.get_quote("AAPL:US", AssetClass.STOCKS)

        # Verify cache was checked
        mock_cache.get.assert_called_once_with("stocks", "AAPL:US")

        # Verify result
        assert result is not None
        assert result.symbol == "AAPL:US"
        assert result.price == 185.50

        # Verify stats
        assert hybrid_source._stats['cache_hits'] == 1
        assert hybrid_source._stats['cache_misses'] == 0

        # Verify yfinance was NOT called
        assert hybrid_source.yfinance.fetch_quote.call_count == 0

    @pytest.mark.asyncio
    async def test_cache_hit_with_force_fresh_skips_cache(self, hybrid_source, mock_cache, mock_yfinance):
        """Test that force_fresh=True skips cache and fetches fresh data."""
        # Setup cache with data
        mock_cache.get.return_value = {'symbol': 'AAPL:US', 'price': 100.0}

        # Get quote with force_fresh
        result = await hybrid_source.get_quote("AAPL:US", AssetClass.STOCKS, force_fresh=True)

        # Verify cache was NOT checked
        mock_cache.get.assert_not_called()

        # Verify yfinance was called
        assert hybrid_source.yfinance.fetch_quote.call_count == 1

        # Verify stats show cache miss
        assert hybrid_source._stats['cache_misses'] == 1

    @pytest.mark.asyncio
    async def test_corrupted_cache_data_falls_back(self, hybrid_source, mock_cache, mock_yfinance):
        """Test that corrupted cache data falls back to fresh fetch."""
        # Setup cache to return invalid data
        mock_cache.get.return_value = {'invalid': 'data'}

        # Get quote
        result = await hybrid_source.get_quote("AAPL:US", AssetClass.STOCKS)

        # Should fall back to yfinance
        assert hybrid_source.yfinance.fetch_quote.call_count == 1
        assert result is not None


class TestYFinanceFallback:
    """Test YFinance fallback behavior."""

    @pytest.mark.asyncio
    async def test_cache_miss_tries_yfinance(self, hybrid_source, mock_cache, mock_yfinance):
        """Test that cache miss triggers yfinance fetch."""
        # Cache returns None (miss)
        mock_cache.get.return_value = None

        # Get quote
        result = await hybrid_source.get_quote("AAPL:US", AssetClass.STOCKS)

        # Verify yfinance was called
        assert hybrid_source.yfinance.fetch_quote.call_count == 1

        # Verify result
        assert result is not None
        assert result.symbol == "AAPL:US"
        assert result.price == 185.50

        # Verify stats
        assert hybrid_source._stats['yfinance_successes'] == 1
        assert hybrid_source._stats['yfinance_failures'] == 0

        # Verify data was cached
        mock_cache.set.assert_called_once()

    @pytest.mark.asyncio
    async def test_yfinance_symbol_conversion_stocks(self, hybrid_source, mock_cache):
        """Test symbol conversion for stocks (removes :US suffix)."""
        mock_cache.get.return_value = None

        await hybrid_source.get_quote("AAPL:US", AssetClass.STOCKS)

        # Verify yfinance was called with converted symbol
        hybrid_source.yfinance.fetch_quote.assert_called_once_with("AAPL")

    @pytest.mark.asyncio
    async def test_yfinance_symbol_conversion_forex(self, hybrid_source, mock_cache):
        """Test symbol conversion for forex pairs."""
        mock_cache.get.return_value = None

        await hybrid_source.get_quote("EUR/USD", AssetClass.FOREX)

        # Should convert to EURUSD=X
        hybrid_source.yfinance.fetch_quote.assert_called_once_with("EURUSD=X")

    @pytest.mark.asyncio
    async def test_yfinance_symbol_conversion_commodities(self, hybrid_source, mock_cache):
        """Test symbol conversion for commodities."""
        mock_cache.get.return_value = None

        await hybrid_source.get_quote("GC", AssetClass.COMMODITIES)

        # Should add =F suffix
        hybrid_source.yfinance.fetch_quote.assert_called_once_with("GC=F")

    @pytest.mark.asyncio
    async def test_yfinance_failure_increments_stats(self, hybrid_source, mock_cache, mock_yfinance):
        """Test that yfinance failure increments failure stats."""
        mock_cache.get.return_value = None
        mock_yfinance.fetch_quote.side_effect = APIError("API Error")

        result = await hybrid_source.get_quote("AAPL:US", AssetClass.STOCKS)

        # Verify stats
        assert hybrid_source._stats['yfinance_failures'] == 1
        assert hybrid_source._stats['yfinance_successes'] == 0

    @pytest.mark.asyncio
    async def test_yfinance_circuit_breaker_open(self, hybrid_source, mock_cache):
        """Test behavior when yfinance circuit breaker is open."""
        mock_cache.get.return_value = None

        # Open circuit breaker
        hybrid_source.breakers['yfinance']._failure_count = 10
        hybrid_source.breakers['yfinance']._state = 'open'

        result = await hybrid_source.get_quote("AAPL:US", AssetClass.STOCKS)

        # Should skip yfinance (circuit open)
        assert hybrid_source.yfinance.fetch_quote.call_count == 0


class TestBrightDataFallback:
    """Test Bright Data fallback behavior."""

    @pytest.mark.asyncio
    async def test_yfinance_fail_tries_bright_data(self, hybrid_source, mock_cache, mock_yfinance, mock_bright_data, mock_cost_tracker):
        """Test that yfinance failure triggers Bright Data fallback."""
        mock_cache.get.return_value = None
        mock_yfinance.fetch_quote.return_value = None

        # Mock bright data client
        hybrid_source._bright_data = mock_bright_data

        # Ensure budget available
        mock_cost_tracker.can_make_request.return_value = True

        # Get quote
        result = await hybrid_source.get_quote("AAPL:US", AssetClass.STOCKS)

        # Verify Bright Data was called
        assert mock_bright_data.fetch.call_count == 1

        # Verify cost was tracked
        assert mock_cost_tracker.record_request.call_count == 1

    @pytest.mark.asyncio
    async def test_bright_data_checks_budget_first(self, hybrid_source, mock_cache, mock_yfinance, mock_cost_tracker):
        """Test that Bright Data checks budget before making request."""
        mock_cache.get.return_value = None
        mock_yfinance.fetch_quote.return_value = None

        # Simulate budget exhausted
        mock_cost_tracker.can_make_request.side_effect = BudgetExhaustedError(
            message="Budget exhausted",
            current_usage=100,
            budget_limit=100,
            reset_time="Manual"
        )

        # Should raise BudgetExhaustedError
        with pytest.raises(BudgetExhaustedError):
            await hybrid_source.get_quote("AAPL:US", AssetClass.STOCKS)

    @pytest.mark.asyncio
    async def test_bright_data_success_increments_stats(self, hybrid_source, mock_cache, mock_yfinance, mock_bright_data, mock_cost_tracker):
        """Test that successful Bright Data fetch increments stats."""
        mock_cache.get.return_value = None
        mock_yfinance.fetch_quote.return_value = None
        hybrid_source._bright_data = mock_bright_data
        mock_cost_tracker.can_make_request.return_value = True

        result = await hybrid_source.get_quote("AAPL:US", AssetClass.STOCKS)

        # Verify stats
        assert hybrid_source._stats['bright_data_successes'] == 1
        assert hybrid_source._stats['bright_data_failures'] == 0

    @pytest.mark.asyncio
    async def test_bright_data_failure_tracks_cost(self, hybrid_source, mock_cache, mock_yfinance, mock_bright_data, mock_cost_tracker):
        """Test that Bright Data failure still tracks cost."""
        mock_cache.get.return_value = None
        mock_yfinance.fetch_quote.return_value = None
        hybrid_source._bright_data = mock_bright_data
        mock_cost_tracker.can_make_request.return_value = True

        # Make fetch fail
        mock_bright_data.fetch.side_effect = APIError("Fetch failed")

        result = await hybrid_source.get_quote("AAPL:US", AssetClass.STOCKS)

        # Verify cost was tracked with success=False
        assert mock_cost_tracker.record_request.call_count == 1
        assert mock_cost_tracker.record_request.call_args[1]['success'] is False

    @pytest.mark.asyncio
    async def test_bright_data_circuit_breaker_open(self, hybrid_source, mock_cache, mock_yfinance, mock_bright_data, mock_cost_tracker):
        """Test behavior when Bright Data circuit breaker is open."""
        mock_cache.get.return_value = None
        mock_yfinance.fetch_quote.return_value = None
        hybrid_source._bright_data = mock_bright_data

        # Open circuit breaker
        hybrid_source.breakers['bright_data']._failure_count = 10
        hybrid_source.breakers['bright_data']._state = 'open'

        result = await hybrid_source.get_quote("AAPL:US", AssetClass.STOCKS)

        # Should skip Bright Data (circuit open)
        assert mock_bright_data.fetch.call_count == 0
        assert result is None


class TestCostAwareFallback:
    """Test cost-aware fallback logic."""

    @pytest.mark.asyncio
    async def test_prefers_free_source_when_available(self, hybrid_source, mock_cache, mock_yfinance, mock_bright_data):
        """Test that free sources are preferred over paid sources."""
        mock_cache.get.return_value = None

        # Both sources available
        hybrid_source._bright_data = mock_bright_data

        result = await hybrid_source.get_quote("AAPL:US", AssetClass.STOCKS)

        # Should use yfinance (free)
        assert hybrid_source.yfinance.fetch_quote.call_count == 1

        # Should NOT use Bright Data
        assert mock_bright_data.fetch.call_count == 0

    @pytest.mark.asyncio
    async def test_cache_saves_cost_on_subsequent_requests(self, hybrid_source, mock_cache, mock_yfinance, mock_market_quote):
        """Test that cache saves costs on repeated requests."""
        # First request - cache miss
        mock_cache.get.return_value = None

        result1 = await hybrid_source.get_quote("AAPL:US", AssetClass.STOCKS)

        # Data should be cached
        assert mock_cache.set.call_count == 1

        # Second request - cache hit
        mock_cache.get.return_value = mock_market_quote.to_dict()

        result2 = await hybrid_source.get_quote("AAPL:US", AssetClass.STOCKS)

        # Should only call yfinance once
        assert hybrid_source.yfinance.fetch_quote.call_count == 1

        # Cache stats should reflect hit
        assert hybrid_source._stats['cache_hits'] == 1

    @pytest.mark.asyncio
    async def test_budget_exhaustion_prevents_paid_requests(self, hybrid_source, mock_cache, mock_yfinance, mock_cost_tracker):
        """Test that budget exhaustion prevents Bright Data requests."""
        mock_cache.get.return_value = None
        mock_yfinance.fetch_quote.return_value = None

        # Simulate budget exhausted
        mock_cost_tracker.can_make_request.side_effect = BudgetExhaustedError(
            message="Budget exhausted",
            current_usage=1000,
            budget_limit=1000,
            reset_time="Manual"
        )

        with pytest.raises(BudgetExhaustedError):
            await hybrid_source.get_quote("AAPL:US", AssetClass.STOCKS)


class TestAllSourcesFail:
    """Test behavior when all data sources fail."""

    @pytest.mark.asyncio
    async def test_all_sources_fail_returns_none(self, hybrid_source, mock_cache, mock_yfinance, mock_bright_data, mock_cost_tracker):
        """Test that None is returned when all sources fail."""
        # All sources fail
        mock_cache.get.return_value = None
        mock_yfinance.fetch_quote.return_value = None
        hybrid_source._bright_data = mock_bright_data
        mock_bright_data.fetch.return_value = None
        mock_cost_tracker.can_make_request.return_value = True

        result = await hybrid_source.get_quote("AAPL:US", AssetClass.STOCKS)

        assert result is None

    @pytest.mark.asyncio
    async def test_all_sources_fail_tracks_failures(self, hybrid_source, mock_cache, mock_yfinance, mock_bright_data, mock_cost_tracker):
        """Test that failures are tracked when all sources fail."""
        mock_cache.get.return_value = None
        mock_yfinance.fetch_quote.side_effect = APIError("YFinance failed")
        hybrid_source._bright_data = mock_bright_data
        mock_bright_data.fetch.side_effect = APIError("Bright Data failed")
        mock_cost_tracker.can_make_request.return_value = True

        result = await hybrid_source.get_quote("AAPL:US", AssetClass.STOCKS)

        # Verify failure stats
        assert hybrid_source._stats['yfinance_failures'] == 1
        assert hybrid_source._stats['bright_data_failures'] == 1
        assert result is None


class TestBatchFetching:
    """Test concurrent batch fetching."""

    @pytest.mark.asyncio
    async def test_get_quotes_fetches_multiple_symbols(self, hybrid_source, mock_cache, sample_symbols):
        """Test fetching multiple quotes concurrently."""
        mock_cache.get.return_value = None

        results = await hybrid_source.get_quotes(sample_symbols, AssetClass.STOCKS)

        # Should have fetched all symbols
        assert len(results) == len(sample_symbols)
        assert all(isinstance(q, MarketQuote) for q in results)

    @pytest.mark.asyncio
    async def test_get_quotes_handles_partial_failures(self, hybrid_source, mock_cache, mock_yfinance):
        """Test that partial failures don't prevent successful fetches."""
        mock_cache.get.return_value = None

        # Make yfinance fail for some symbols
        def fetch_side_effect(symbol):
            if symbol in ["AAPL", "MSFT"]:
                return {
                    'symbol': symbol,
                    'regularMarketPrice': 100.0,
                    'currency': 'USD'
                }
            else:
                raise APIError("Failed")

        mock_yfinance.fetch_quote.side_effect = fetch_side_effect

        symbols = ["AAPL:US", "MSFT:US", "FAIL1:US", "FAIL2:US"]
        results = await hybrid_source.get_quotes(symbols, AssetClass.STOCKS)

        # Should have 2 successful results
        assert len(results) == 2


class TestStatistics:
    """Test statistics tracking and reporting."""

    @pytest.mark.asyncio
    async def test_get_statistics_structure(self, hybrid_source):
        """Test statistics output structure."""
        stats = hybrid_source.get_statistics()

        # Verify required keys
        assert 'total_requests' in stats
        assert 'cache_statistics' in stats
        assert 'source_usage' in stats
        assert 'cost_tracking' in stats

        # Verify source usage details
        assert 'yfinance' in stats['source_usage']
        assert 'bright_data' in stats['source_usage']

    @pytest.mark.asyncio
    async def test_statistics_track_cache_hit_rate(self, hybrid_source, mock_cache, mock_market_quote):
        """Test cache hit rate calculation."""
        # 3 cache hits
        mock_cache.get.return_value = mock_market_quote.to_dict()
        for _ in range(3):
            await hybrid_source.get_quote("AAPL:US", AssetClass.STOCKS)

        # 2 cache misses
        mock_cache.get.return_value = None
        for _ in range(2):
            await hybrid_source.get_quote("MSFT:US", AssetClass.STOCKS)

        stats = hybrid_source.get_statistics()

        # Hit rate should be 60% (3/5)
        assert stats['cache_statistics']['hits'] == 3
        assert stats['cache_statistics']['misses'] == 2
        assert abs(stats['cache_statistics']['hit_rate_pct'] - 60.0) < 0.1

    @pytest.mark.asyncio
    async def test_statistics_track_source_success_rate(self, hybrid_source, mock_cache, mock_yfinance):
        """Test source success rate calculation."""
        mock_cache.get.return_value = None

        # 7 successes
        for _ in range(7):
            await hybrid_source.get_quote("AAPL:US", AssetClass.STOCKS)

        # 3 failures
        mock_yfinance.fetch_quote.side_effect = APIError("Failed")
        for _ in range(3):
            await hybrid_source.get_quote("FAIL:US", AssetClass.STOCKS)

        stats = hybrid_source.get_statistics()

        # Success rate should be 70% (7/10)
        yf_stats = stats['source_usage']['yfinance']
        assert yf_stats['successes'] == 7
        assert yf_stats['failures'] == 3
        assert abs(yf_stats['success_rate_pct'] - 70.0) < 0.1

    def test_reset_statistics(self, hybrid_source):
        """Test statistics reset."""
        # Add some stats
        hybrid_source._stats['cache_hits'] = 10
        hybrid_source._stats['yfinance_successes'] = 5

        # Reset
        pre_reset = hybrid_source.reset_statistics()

        # Verify pre-reset stats returned
        assert pre_reset['cache_statistics']['hits'] == 10

        # Verify stats reset
        assert hybrid_source._stats['cache_hits'] == 0
        assert hybrid_source._stats['yfinance_successes'] == 0


class TestCleanup:
    """Test resource cleanup."""

    @pytest.mark.asyncio
    async def test_cleanup_closes_connections(self, hybrid_source, mock_cache, mock_bright_data):
        """Test that cleanup closes all connections."""
        hybrid_source._bright_data = mock_bright_data
        mock_bright_data.close = AsyncMock()

        await hybrid_source.cleanup()

        # Verify cache closed
        mock_cache.close.assert_called_once()

        # Verify bright data closed
        mock_bright_data.close.assert_called_once()


class TestRepr:
    """Test string representation."""

    def test_repr_includes_stats(self, hybrid_source):
        """Test that repr includes key statistics."""
        hybrid_source._stats['total_requests'] = 10
        hybrid_source._stats['cache_hits'] = 5
        hybrid_source._stats['yfinance_successes'] = 3
        hybrid_source._stats['bright_data_successes'] = 2

        repr_str = repr(hybrid_source)

        assert 'HybridDataSource' in repr_str
        assert 'requests=10' in repr_str
        assert 'cache_hits=5' in repr_str
        assert 'yfinance=3' in repr_str
        assert 'bright_data=2' in repr_str
