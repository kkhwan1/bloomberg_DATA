"""
Tests for orchestrator components.

Tests for CircuitBreaker, HybridDataSource, and DataScheduler.
"""

import asyncio
import pytest
import time
from datetime import datetime

from src.normalizer.schemas import AssetClass
from src.orchestrator.circuit_breaker import CircuitBreaker, CircuitBreakerError, CircuitState
from src.orchestrator.hybrid_source import HybridDataSource
from src.orchestrator.scheduler import DataScheduler


class TestCircuitBreaker:
    """Test CircuitBreaker functionality."""

    def test_circuit_breaker_initialization(self):
        """Test circuit breaker initializes in CLOSED state."""
        breaker = CircuitBreaker("test", failure_threshold=3, recovery_timeout=10)

        assert breaker.name == "test"
        assert breaker.failure_threshold == 3
        assert breaker.recovery_timeout == 10
        assert breaker.state == CircuitState.CLOSED
        assert breaker.is_available() is True

    def test_successful_calls(self):
        """Test successful calls keep circuit CLOSED."""
        breaker = CircuitBreaker("test", failure_threshold=3)

        def success_func():
            return "success"

        # Execute successful calls
        for _ in range(5):
            result = breaker.call(success_func)
            assert result == "success"
            assert breaker.state == CircuitState.CLOSED

        stats = breaker.get_statistics()
        assert stats["counters"]["total_calls"] == 5
        assert stats["counters"]["total_successes"] == 5
        assert stats["counters"]["total_failures"] == 0

    def test_circuit_opens_on_failures(self):
        """Test circuit opens after threshold failures."""
        breaker = CircuitBreaker("test", failure_threshold=3)

        def failing_func():
            raise Exception("Simulated failure")

        # Execute failing calls
        for i in range(3):
            with pytest.raises(Exception, match="Simulated failure"):
                breaker.call(failing_func)

        # Circuit should now be OPEN
        assert breaker.state == CircuitState.OPEN
        assert breaker.is_available() is False

        # Next call should be blocked
        with pytest.raises(CircuitBreakerError):
            breaker.call(failing_func)

    def test_circuit_half_open_recovery(self):
        """Test circuit transitions to HALF_OPEN after timeout."""
        breaker = CircuitBreaker("test", failure_threshold=2, recovery_timeout=1)

        def failing_func():
            raise Exception("Failure")

        # Open the circuit
        for _ in range(2):
            with pytest.raises(Exception):
                breaker.call(failing_func)

        assert breaker.state == CircuitState.OPEN

        # Wait for recovery timeout
        time.sleep(1.5)

        # Check state (should transition to HALF_OPEN)
        assert breaker.state == CircuitState.HALF_OPEN

    def test_circuit_closes_after_success_in_half_open(self):
        """Test circuit closes after successful call in HALF_OPEN."""
        breaker = CircuitBreaker("test", failure_threshold=2, recovery_timeout=1)

        def failing_func():
            raise Exception("Failure")

        def success_func():
            return "success"

        # Open the circuit
        for _ in range(2):
            with pytest.raises(Exception):
                breaker.call(failing_func)

        assert breaker.state == CircuitState.OPEN

        # Wait for recovery
        time.sleep(1.5)

        # Successful call should close circuit
        result = breaker.call(success_func)
        assert result == "success"
        assert breaker.state == CircuitState.CLOSED

    def test_circuit_statistics(self):
        """Test circuit breaker statistics tracking."""
        breaker = CircuitBreaker("test", failure_threshold=3)

        def success_func():
            return "ok"

        def fail_func():
            raise Exception("error")

        # Execute mixed calls
        breaker.call(success_func)
        breaker.call(success_func)

        try:
            breaker.call(fail_func)
        except Exception:
            pass

        stats = breaker.get_statistics()

        assert stats["name"] == "test"
        assert stats["counters"]["total_calls"] == 3
        assert stats["counters"]["total_successes"] == 2
        assert stats["counters"]["total_failures"] == 1
        assert stats["state"] == CircuitState.CLOSED.value


class TestHybridDataSource:
    """Test HybridDataSource functionality."""

    @pytest.mark.asyncio
    async def test_hybrid_source_initialization(self):
        """Test hybrid source initializes all components."""
        source = HybridDataSource()

        assert source.cache is not None
        assert source.yfinance is not None
        assert source.cost_tracker is not None
        assert "yfinance" in source.breakers
        assert "bright_data" in source.breakers

        await source.cleanup()

    @pytest.mark.asyncio
    async def test_get_quote_yfinance(self):
        """Test fetching quote from yfinance."""
        source = HybridDataSource()

        # Fetch a well-known stock
        quote = await source.get_quote("AAPL", AssetClass.STOCKS)

        if quote:  # May fail if network is down
            assert quote.symbol in ["AAPL", "AAPL:US"]
            assert quote.price > 0
            assert quote.asset_class == AssetClass.STOCKS
            assert quote.source.value in ["yfinance", "cache"]

        await source.cleanup()

    @pytest.mark.asyncio
    async def test_cache_hit_on_second_fetch(self):
        """Test second fetch hits cache."""
        source = HybridDataSource()

        # First fetch
        quote1 = await source.get_quote("AAPL", AssetClass.STOCKS)

        if quote1:
            # Second fetch should hit cache
            quote2 = await source.get_quote("AAPL", AssetClass.STOCKS)

            assert quote2 is not None
            assert quote2.symbol == quote1.symbol
            assert quote2.price == quote1.price

            # Check statistics
            stats = source.get_statistics()
            assert stats["cache_statistics"]["hits"] >= 1

        await source.cleanup()

    @pytest.mark.asyncio
    async def test_get_multiple_quotes(self):
        """Test bulk quote fetching."""
        source = HybridDataSource()

        symbols = ["AAPL", "MSFT"]
        quotes = await source.get_quotes(symbols, AssetClass.STOCKS)

        # Should get at least one quote (if network available)
        assert isinstance(quotes, list)

        for quote in quotes:
            assert quote.price > 0
            assert quote.asset_class == AssetClass.STOCKS

        await source.cleanup()

    @pytest.mark.asyncio
    async def test_statistics_tracking(self):
        """Test statistics are tracked correctly."""
        source = HybridDataSource()

        # Make a request
        await source.get_quote("AAPL", AssetClass.STOCKS)

        stats = source.get_statistics()

        assert "total_requests" in stats
        assert "cache_statistics" in stats
        assert "source_usage" in stats
        assert "cost_tracking" in stats

        assert stats["total_requests"] >= 1

        await source.cleanup()


class TestDataScheduler:
    """Test DataScheduler functionality."""

    def test_scheduler_initialization(self):
        """Test scheduler initializes correctly."""
        symbols = ["AAPL", "MSFT"]
        asset_classes = {
            "AAPL": AssetClass.STOCKS,
            "MSFT": AssetClass.STOCKS,
        }

        scheduler = DataScheduler(symbols, asset_classes, update_interval_minutes=15)

        assert scheduler.symbols == symbols
        assert scheduler.asset_classes == asset_classes
        assert scheduler.update_interval_minutes == 15
        assert scheduler.is_running() is False

    def test_scheduler_add_remove_symbols(self):
        """Test adding and removing symbols."""
        symbols = ["AAPL"]
        asset_classes = {"AAPL": AssetClass.STOCKS}

        scheduler = DataScheduler(symbols, asset_classes)

        # Add symbol
        scheduler.add_symbol("MSFT", AssetClass.STOCKS)
        assert "MSFT" in scheduler.symbols
        assert scheduler.asset_classes["MSFT"] == AssetClass.STOCKS

        # Remove symbol
        result = scheduler.remove_symbol("MSFT")
        assert result is True
        assert "MSFT" not in scheduler.symbols

        # Remove non-existent symbol
        result = scheduler.remove_symbol("GOOGL")
        assert result is False

    def test_scheduler_start_stop(self):
        """Test scheduler can start and stop."""
        symbols = ["AAPL"]
        asset_classes = {"AAPL": AssetClass.STOCKS}

        scheduler = DataScheduler(symbols, asset_classes, update_interval_minutes=60)

        # Start scheduler
        scheduler.start()
        assert scheduler.is_running() is True

        # Give it a moment to initialize
        time.sleep(2)

        # Check jobs are scheduled
        stats = scheduler.get_statistics()
        assert len(stats["scheduled_jobs"]) > 0

        # Stop scheduler
        scheduler.stop()
        assert scheduler.is_running() is False

    def test_scheduler_statistics(self):
        """Test scheduler statistics."""
        symbols = ["AAPL"]
        asset_classes = {"AAPL": AssetClass.STOCKS}

        scheduler = DataScheduler(symbols, asset_classes)

        stats = scheduler.get_statistics()

        assert "scheduler_state" in stats
        assert "collection_metrics" in stats
        assert "maintenance_metrics" in stats

        assert stats["scheduler_state"]["symbols_tracked"] == 1
        assert stats["scheduler_state"]["is_running"] is False

    def test_scheduler_context_manager(self):
        """Test scheduler works as context manager."""
        symbols = ["AAPL"]
        asset_classes = {"AAPL": AssetClass.STOCKS}

        with DataScheduler(symbols, asset_classes) as scheduler:
            assert scheduler.is_running() is True

        # Should be stopped after context exit
        assert scheduler.is_running() is False


# Integration test
@pytest.mark.asyncio
async def test_full_integration():
    """Test full integration of all components."""
    # Create scheduler with hybrid source
    symbols = ["AAPL"]
    asset_classes = {"AAPL": AssetClass.STOCKS}

    scheduler = DataScheduler(symbols, asset_classes, update_interval_minutes=60)

    # Start scheduler
    scheduler.start()

    # Wait a moment
    await asyncio.sleep(2)

    # Force a collection
    scheduler.force_collection()

    # Wait for collection to complete
    await asyncio.sleep(3)

    # Check statistics
    stats = scheduler.get_statistics()

    # Should have attempted at least one collection
    assert stats["collection_metrics"]["total_collections"] >= 1

    # Stop scheduler
    scheduler.stop()
