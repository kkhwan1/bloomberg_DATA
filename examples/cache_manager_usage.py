"""
CacheManager usage examples.

Demonstrates common cache operations, statistics tracking,
and best practices for the Bloomberg Data Crawler.
"""

import json
from pathlib import Path

from src.orchestrator.cache_manager import CacheManager
from src.utils.exceptions import CacheError


def example_basic_operations():
    """Demonstrate basic cache operations."""
    print("=== Basic Cache Operations ===\n")

    # Initialize cache manager
    cache = CacheManager()

    # Store stock data
    stock_data = {
        "symbol": "AAPL",
        "price": 150.25,
        "change": 2.15,
        "volume": 85000000,
        "timestamp": "2025-01-07T10:00:00Z",
        "market": "NASDAQ"
    }

    print("1. Setting cache for AAPL...")
    cache.set("stocks", "AAPL", stock_data)
    print("   ✓ Cache stored\n")

    # Retrieve from cache
    print("2. Getting cache for AAPL...")
    cached_data = cache.get("stocks", "AAPL")
    if cached_data:
        print(f"   ✓ Cache hit: {cached_data['symbol']} = ${cached_data['price']}\n")
    else:
        print("   ✗ Cache miss\n")

    # Cache miss example
    print("3. Getting cache for non-existent symbol...")
    result = cache.get("stocks", "NONEXISTENT")
    if result is None:
        print("   ✓ Cache miss (as expected)\n")

    cache.close()


def example_multiple_asset_classes():
    """Demonstrate caching different asset classes."""
    print("=== Multiple Asset Classes ===\n")

    cache = CacheManager()

    # Stock data
    cache.set("stocks", "AAPL", {
        "price": 150.25,
        "type": "equity",
        "exchange": "NASDAQ"
    })

    # Bond data
    cache.set("bonds", "US10Y", {
        "yield": 3.85,
        "type": "treasury",
        "maturity": "2035-01-01"
    })

    # Commodity data
    cache.set("commodities", "GC", {
        "price": 2050.00,
        "type": "gold",
        "unit": "troy_ounce"
    })

    # Currency data
    cache.set("currencies", "EURUSD", {
        "rate": 1.0925,
        "type": "forex_pair"
    })

    print("Cached data for different asset classes:")
    print(f"  Stock (AAPL): {cache.get('stocks', 'AAPL')['price']}")
    print(f"  Bond (US10Y): {cache.get('bonds', 'US10Y')['yield']}%")
    print(f"  Commodity (GC): ${cache.get('commodities', 'GC')['price']}")
    print(f"  Currency (EURUSD): {cache.get('currencies', 'EURUSD')['rate']}")
    print()

    cache.close()


def example_statistics_tracking():
    """Demonstrate statistics and hit tracking."""
    print("=== Statistics Tracking ===\n")

    cache = CacheManager()

    # Add some data
    cache.set("stocks", "AAPL", {"price": 150.25})
    cache.set("stocks", "MSFT", {"price": 375.50})
    cache.set("stocks", "GOOGL", {"price": 142.75})

    # Access with different frequencies
    print("Simulating cache access patterns...")
    for _ in range(10):
        cache.get("stocks", "AAPL")  # High frequency
    for _ in range(5):
        cache.get("stocks", "MSFT")  # Medium frequency
    cache.get("stocks", "GOOGL")    # Low frequency

    # Get statistics
    stats = cache.get_statistics()

    print(f"\nCache Statistics:")
    print(f"  Total entries: {stats['total_entries']}")
    print(f"  Valid entries: {stats['valid_entries']}")
    print(f"  Expired entries: {stats['expired_entries']}")
    print(f"  Total hits: {stats['total_hits']}")
    print(f"  Average hits per entry: {stats['average_hits']}")
    print(f"  Cache size: {stats['cache_size_mb']} MB")
    print(f"  TTL: {stats['ttl_seconds']} seconds")

    print("\nMost accessed entries:")
    for i, entry in enumerate(stats['most_accessed'], 1):
        print(f"  {i}. {entry['cache_key']}: {entry['hit_count']} hits")

    print()
    cache.close()


def example_cache_invalidation():
    """Demonstrate cache invalidation strategies."""
    print("=== Cache Invalidation ===\n")

    cache = CacheManager()

    # Add data
    cache.set("stocks", "AAPL", {"price": 150.25})
    cache.set("stocks", "MSFT", {"price": 375.50})
    cache.set("stocks", "GOOGL", {"price": 142.75})

    print("Initial cache state:")
    stats = cache.get_statistics()
    print(f"  Total entries: {stats['total_entries']}\n")

    # Invalidate specific entry
    print("Invalidating AAPL...")
    result = cache.invalidate("stocks", "AAPL")
    print(f"  Result: {'✓ Deleted' if result else '✗ Not found'}\n")

    # Verify deletion
    data = cache.get("stocks", "AAPL")
    print(f"Attempting to retrieve AAPL: {'Found' if data else '✓ Not found (deleted)'}\n")

    # Clear expired entries
    print("Clearing expired entries...")
    deleted = cache.clear_expired()
    print(f"  Deleted {deleted} expired entries\n")

    cache.close()


def example_expiration_behavior():
    """Demonstrate TTL expiration behavior."""
    print("=== TTL Expiration ===\n")

    import time

    # Create cache with short TTL for demonstration
    cache = CacheManager(ttl_seconds=2)

    print("Setting cache with 2-second TTL...")
    cache.set("stocks", "AAPL", {"price": 150.25})

    print("Immediately retrieving cache...")
    data = cache.get("stocks", "AAPL")
    print(f"  Result: {'✓ Cache hit' if data else '✗ Cache miss'}\n")

    print("Waiting 3 seconds for expiration...")
    time.sleep(3)

    print("Retrieving after expiration...")
    data = cache.get("stocks", "AAPL")
    print(f"  Result: {'✗ Cache hit' if data else '✓ Cache miss (expired)'}\n")

    # Cleanup
    stats = cache.get_statistics()
    print(f"Expired entries in cache: {stats['expired_entries']}")

    print("\nCleaning up expired entries...")
    deleted = cache.clear_expired()
    print(f"  Deleted {deleted} entries\n")

    cache.close()


def example_error_handling():
    """Demonstrate error handling best practices."""
    print("=== Error Handling ===\n")

    cache = CacheManager()

    # Handle cache errors gracefully
    try:
        cache.set("stocks", "AAPL", {"price": 150.25})
        print("✓ Cache write successful")

        data = cache.get("stocks", "AAPL")
        print(f"✓ Cache read successful: {data}")

    except CacheError as e:
        print(f"✗ Cache error: {e}")
        print(f"  Operation: {e.operation}")
        print(f"  Details: {e.details}")

    # Clear all with safety check
    try:
        print("\nAttempting clear_all without confirmation...")
        cache.clear_all(confirm=False)
    except CacheError as e:
        print(f"✓ Prevented: {e.message}")

    try:
        print("\nClearing all with confirmation...")
        deleted = cache.clear_all(confirm=True)
        print(f"✓ Deleted {deleted} entries")
    except CacheError as e:
        print(f"✗ Error: {e}")

    print()
    cache.close()


def example_context_manager():
    """Demonstrate context manager usage."""
    print("=== Context Manager Usage ===\n")

    # Using context manager for automatic cleanup
    with CacheManager() as cache:
        cache.set("stocks", "AAPL", {"price": 150.25})
        data = cache.get("stocks", "AAPL")
        print(f"Cache data: {data}")

    # Connection automatically closed after context
    print("✓ Cache connection automatically closed\n")


def example_realistic_workflow():
    """Demonstrate realistic Bloomberg crawler workflow."""
    print("=== Realistic Workflow ===\n")

    cache = CacheManager()

    def fetch_bloomberg_data(symbol: str) -> dict:
        """Simulate fetching data from Bloomberg API."""
        print(f"  → Fetching {symbol} from Bloomberg API...")
        return {
            "symbol": symbol,
            "price": 150.25,
            "timestamp": "2025-01-07T10:00:00Z"
        }

    def get_stock_data(symbol: str, use_cache: bool = True) -> dict:
        """Get stock data with caching logic."""
        if use_cache:
            # Try cache first
            cached = cache.get("stocks", symbol)
            if cached:
                print(f"  ✓ Cache hit for {symbol}")
                return cached

            print(f"  ✗ Cache miss for {symbol}")

        # Fetch from API
        data = fetch_bloomberg_data(symbol)

        # Store in cache
        cache.set("stocks", symbol, data)
        print(f"  ✓ Cached {symbol}")

        return data

    # Simulate workflow
    symbols = ["AAPL", "MSFT", "GOOGL", "AAPL", "MSFT"]

    print("Processing symbols with caching:")
    for symbol in symbols:
        print(f"\n{symbol}:")
        data = get_stock_data(symbol)

    # Show statistics
    print("\n" + "="*50)
    stats = cache.get_statistics()
    print(f"\nWorkflow Statistics:")
    print(f"  Total API calls avoided: {stats['total_hits']}")
    print(f"  Unique symbols cached: {stats['total_entries']}")
    print(f"  Cache efficiency: {stats['total_hits'] / len(symbols) * 100:.1f}%")

    print()
    cache.close()


def main():
    """Run all examples."""
    examples = [
        ("Basic Operations", example_basic_operations),
        ("Multiple Asset Classes", example_multiple_asset_classes),
        ("Statistics Tracking", example_statistics_tracking),
        ("Cache Invalidation", example_cache_invalidation),
        ("TTL Expiration", example_expiration_behavior),
        ("Error Handling", example_error_handling),
        ("Context Manager", example_context_manager),
        ("Realistic Workflow", example_realistic_workflow),
    ]

    print("=" * 60)
    print("CacheManager Usage Examples")
    print("=" * 60)
    print()

    for title, example_func in examples:
        try:
            example_func()
            print("-" * 60)
            print()
        except Exception as e:
            print(f"Error in {title}: {e}\n")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    main()
