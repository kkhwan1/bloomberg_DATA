"""
HybridDataSource and DataScheduler Demo.

Demonstrates the priority-based hybrid data source and automated scheduler
with cost optimization, circuit breakers, and cache management.

Usage:
    python examples/hybrid_scheduler_demo.py
"""

import asyncio
import logging
import sys
import time
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import AppConfig
from src.normalizer.schemas import AssetClass
from src.orchestrator.circuit_breaker import CircuitBreaker
from src.orchestrator.hybrid_source import HybridDataSource
from src.orchestrator.scheduler import DataScheduler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger(__name__)


def print_separator(title: str = ""):
    """Print a formatted separator line."""
    if title:
        print(f"\n{'=' * 80}")
        print(f"  {title}")
        print(f"{'=' * 80}\n")
    else:
        print(f"{'=' * 80}\n")


async def demo_circuit_breaker():
    """Demonstrate circuit breaker functionality."""
    print_separator("Circuit Breaker Demo")

    breaker = CircuitBreaker("test_service", failure_threshold=3, recovery_timeout=5)

    def unreliable_function(fail: bool = False):
        """Simulated function that can fail."""
        if fail:
            raise Exception("Simulated failure")
        return "Success!"

    # Test successful calls
    print("Testing successful calls:")
    for i in range(3):
        try:
            result = breaker.call(unreliable_function, fail=False)
            print(f"  Call {i+1}: {result} - State: {breaker.state.value}")
        except Exception as e:
            print(f"  Call {i+1}: Failed - {e}")

    # Test failures to open circuit
    print("\nTesting failures (should open circuit):")
    for i in range(5):
        try:
            result = breaker.call(unreliable_function, fail=True)
            print(f"  Call {i+1}: {result}")
        except Exception as e:
            print(f"  Call {i+1}: {type(e).__name__} - State: {breaker.state.value}")

    # Show statistics
    stats = breaker.get_statistics()
    print(f"\nCircuit Breaker Statistics:")
    print(f"  State: {stats['state']}")
    print(f"  Total Calls: {stats['counters']['total_calls']}")
    print(f"  Successes: {stats['counters']['total_successes']}")
    print(f"  Failures: {stats['counters']['total_failures']}")
    print(f"  Failure Rate: {stats['metrics']['failure_rate_pct']}%")

    # Wait for recovery
    print(f"\nWaiting {breaker.recovery_timeout} seconds for recovery...")
    await asyncio.sleep(breaker.recovery_timeout + 1)

    # Test recovery
    print("\nTesting recovery (should transition to HALF_OPEN then CLOSED):")
    try:
        result = breaker.call(unreliable_function, fail=False)
        print(f"  Recovery call: {result} - State: {breaker.state.value}")
    except Exception as e:
        print(f"  Recovery call: Failed - {e}")


async def demo_hybrid_source():
    """Demonstrate hybrid data source functionality."""
    print_separator("Hybrid Data Source Demo")

    # Initialize hybrid source
    source = HybridDataSource()

    # Test symbols
    test_symbols = [
        ("AAPL", AssetClass.STOCKS),
        ("MSFT", AssetClass.STOCKS),
        ("GOOGL", AssetClass.STOCKS),
    ]

    print("Fetching quotes with priority-based retrieval:")
    print("  Priority: 1. Cache → 2. YFinance (free) → 3. Bright Data (paid)\n")

    # Fetch individual quotes
    for symbol, asset_class in test_symbols:
        print(f"Fetching {symbol}...")
        quote = await source.get_quote(symbol, asset_class)

        if quote:
            print(f"  ✓ {quote.symbol}: ${quote.price:.2f}")
            print(f"    Change: {quote.change_percent:+.2f}%")
            print(f"    Source: {quote.source.value}")
            print(f"    Timestamp: {quote.timestamp}")
        else:
            print(f"  ✗ Failed to fetch {symbol}")
        print()

    # Test cache hit on second fetch
    print("\nFetching AAPL again (should hit cache):")
    quote = await source.get_quote("AAPL", AssetClass.STOCKS)
    if quote:
        print(f"  ✓ {quote.symbol}: ${quote.price:.2f} (from {quote.source.value})")

    # Test bulk fetching
    print("\n\nBulk fetch demo:")
    symbols = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"]
    quotes = await source.get_quotes(symbols, AssetClass.STOCKS)
    print(f"  Successfully fetched {len(quotes)}/{len(symbols)} quotes")

    # Show statistics
    print_separator("Hybrid Source Statistics")
    stats = source.get_statistics()

    print("Cache Performance:")
    print(f"  Total Requests: {stats['total_requests']}")
    print(f"  Cache Hits: {stats['cache_statistics']['hits']}")
    print(f"  Cache Misses: {stats['cache_statistics']['misses']}")
    print(f"  Hit Rate: {stats['cache_statistics']['hit_rate_pct']}%")

    print("\nYFinance Usage:")
    yf_stats = stats["source_usage"]["yfinance"]
    print(f"  Requests: {yf_stats['total_requests']}")
    print(f"  Successes: {yf_stats['successes']}")
    print(f"  Success Rate: {yf_stats['success_rate_pct']}%")
    print(f"  Total Cost: ${yf_stats['total_cost']:.4f}")

    print("\nBright Data Usage:")
    bd_stats = stats["source_usage"]["bright_data"]
    print(f"  Requests: {bd_stats['total_requests']}")
    print(f"  Successes: {bd_stats['successes']}")
    print(f"  Success Rate: {bd_stats['success_rate_pct']}%")
    print(f"  Total Cost: ${bd_stats['total_cost']:.4f}")

    print("\nCost Tracking:")
    cost_stats = stats["cost_tracking"]
    print(f"  Total Cost: ${cost_stats['total_cost']:.4f}")
    print(f"  Budget Used: {cost_stats['budget_used_pct']:.2f}%")
    print(f"  Requests Remaining: {cost_stats['budget_remaining']:.4f}")

    # Cleanup
    await source.cleanup()


def demo_scheduler():
    """Demonstrate scheduler functionality."""
    print_separator("Data Scheduler Demo")

    # Define symbols to track
    symbols = ["AAPL", "MSFT", "GOOGL"]
    asset_classes = {
        "AAPL": AssetClass.STOCKS,
        "MSFT": AssetClass.STOCKS,
        "GOOGL": AssetClass.STOCKS,
    }

    print(f"Initializing scheduler for {len(symbols)} symbols:")
    for symbol in symbols:
        print(f"  - {symbol}")

    # Create scheduler with 1-minute interval for demo
    scheduler = DataScheduler(symbols, asset_classes, update_interval_minutes=1)

    print("\nStarting scheduler (will run for 3 minutes)...")
    scheduler.start()

    try:
        # Let it run for a few collections
        print("\nScheduler running. Will show statistics in 3 minutes...")
        print("(Press Ctrl+C to stop early)\n")

        for i in range(180):  # 3 minutes
            time.sleep(1)
            if i % 30 == 0 and i > 0:
                print(f"  ... {i} seconds elapsed ...")

    except KeyboardInterrupt:
        print("\n\nKeyboard interrupt detected")

    finally:
        # Show statistics before stopping
        print_separator("Scheduler Statistics")
        stats = scheduler.get_statistics()

        print("Scheduler State:")
        state = stats["scheduler_state"]
        print(f"  Running: {state['is_running']}")
        print(f"  Update Interval: {state['update_interval_minutes']} minutes")
        print(f"  Symbols Tracked: {state['symbols_tracked']}")
        print(f"  Total Collections: {state['total_collections']}")

        print("\nCollection Metrics:")
        metrics = stats["collection_metrics"]
        print(f"  Total Collections: {metrics['total_collections']}")
        print(f"  Successful: {metrics['successful_collections']}")
        print(f"  Failed: {metrics['failed_collections']}")
        print(f"  Quotes Collected: {metrics['total_quotes_collected']}")
        print(f"  Success Rate: {metrics['success_rate_pct']}%")

        print("\nScheduled Jobs:")
        for job in stats["scheduled_jobs"]:
            print(f"  - {job['name']} (ID: {job['id']})")
            print(f"    Next run: {job['next_run']}")

        # Stop scheduler
        print("\nStopping scheduler...")
        scheduler.stop()
        print("Scheduler stopped successfully")


async def main():
    """Run all demonstrations."""
    print_separator("Bloomberg Data Crawler - Orchestrator Components Demo")

    # Initialize configuration
    AppConfig.initialize()

    try:
        # Demo 1: Circuit Breaker
        await demo_circuit_breaker()

        # Demo 2: Hybrid Data Source
        await demo_hybrid_source()

        # Demo 3: Scheduler (synchronous, runs for set duration)
        demo_scheduler()

    except Exception as e:
        logger.error(f"Demo failed: {e}", exc_info=True)
        raise

    print_separator("Demo Completed")
    print("All demonstrations completed successfully!")


if __name__ == "__main__":
    # Run async main
    asyncio.run(main())
