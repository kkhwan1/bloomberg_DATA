# CacheManager Documentation

## Overview

`CacheManager` is a SQLite-based caching system for the Bloomberg Data Crawler that reduces API costs by storing frequently accessed data with automatic expiration and comprehensive statistics tracking.

## Features

- **SQLite Backend**: Reliable, file-based storage with ACID guarantees
- **Automatic TTL**: 15-minute default expiration (configurable)
- **Hit Tracking**: Monitor cache effectiveness with detailed statistics
- **Thread-Safe**: Concurrent read/write operations supported
- **Automatic Cleanup**: Remove expired entries on demand
- **Multiple Asset Classes**: Organize cache by asset type (stocks, bonds, commodities, etc.)

## Quick Start

```python
from src.orchestrator.cache_manager import CacheManager

# Initialize cache manager
cache = CacheManager()

# Store data
stock_data = {
    "symbol": "AAPL",
    "price": 150.25,
    "volume": 85000000
}
cache.set("stocks", "AAPL", stock_data)

# Retrieve data
data = cache.get("stocks", "AAPL")
if data:
    print(f"Price: ${data['price']}")
else:
    print("Cache miss - fetch from API")

# Cleanup
cache.close()
```

## API Reference

### Initialization

```python
cache = CacheManager(
    db_path: Optional[Path] = None,    # Defaults to CacheConfig.DB_PATH
    ttl_seconds: Optional[int] = None  # Defaults to CacheConfig.TTL_SECONDS (900)
)
```

### Core Methods

#### `get(asset_class: str, symbol: str) -> Optional[dict]`

Retrieve cached data if valid (not expired).

**Parameters:**
- `asset_class`: Asset category (e.g., "stocks", "bonds", "commodities")
- `symbol`: Asset identifier (e.g., "AAPL", "MSFT")

**Returns:**
- `dict`: Cached data if found and valid
- `None`: Cache miss or expired entry

**Raises:**
- `CacheError`: Database read failure or JSON decode error

**Example:**
```python
data = cache.get("stocks", "AAPL")
if data:
    print("Cache hit:", data)
else:
    # Fetch from API and cache
    data = fetch_from_bloomberg("AAPL")
    cache.set("stocks", "AAPL", data)
```

#### `set(asset_class: str, symbol: str, data: dict) -> bool`

Store data in cache with automatic expiration.

**Parameters:**
- `asset_class`: Asset category
- `symbol`: Asset identifier
- `data`: Dictionary to cache (must be JSON-serializable)

**Returns:**
- `bool`: True if successfully cached

**Raises:**
- `CacheError`: Database write failure or JSON encode error

**Example:**
```python
stock_data = {
    "symbol": "AAPL",
    "price": 150.25,
    "change": 2.15,
    "timestamp": "2025-01-07T10:00:00Z"
}
cache.set("stocks", "AAPL", stock_data)
```

#### `invalidate(asset_class: str, symbol: str) -> bool`

Delete specific cache entry.

**Parameters:**
- `asset_class`: Asset category
- `symbol`: Asset identifier

**Returns:**
- `bool`: True if entry was deleted, False if not found

**Example:**
```python
if cache.invalidate("stocks", "AAPL"):
    print("Cache invalidated")
else:
    print("Entry not found")
```

#### `clear_expired() -> int`

Remove all expired cache entries.

**Returns:**
- `int`: Number of entries deleted

**Example:**
```python
deleted = cache.clear_expired()
print(f"Removed {deleted} expired entries")
```

#### `get_statistics() -> dict`

Get comprehensive cache statistics.

**Returns:**
```python
{
    "total_entries": 25,           # Total cached items
    "expired_entries": 3,          # Expired items (not auto-removed)
    "valid_entries": 22,           # Active cached items
    "total_hits": 150,             # Sum of all hit counts
    "average_hits": 6.0,           # Average hits per entry
    "most_accessed": [             # Top 5 most accessed
        {
            "cache_key": "stocks:AAPL",
            "hit_count": 45,
            "last_accessed": "2025-01-07T10:15:00Z"
        },
        # ... up to 5 entries
    ],
    "cache_size_bytes": 524288,    # Database file size
    "cache_size_mb": 0.5,          # Size in MB
    "ttl_seconds": 900,            # Configured TTL
    "db_path": "/path/to/cache.db" # Database location
}
```

**Example:**
```python
stats = cache.get_statistics()
print(f"Cache efficiency: {stats['total_hits']} hits")
print(f"Most accessed: {stats['most_accessed'][0]['cache_key']}")
```

#### `clear_all(confirm: bool = True) -> int`

Delete all cache entries (requires confirmation).

**Parameters:**
- `confirm`: Must be `True` to execute (safety mechanism)

**Returns:**
- `int`: Number of entries deleted

**Raises:**
- `CacheError`: If `confirm=False`

**Example:**
```python
# Requires explicit confirmation
deleted = cache.clear_all(confirm=True)
print(f"Cleared {deleted} entries")

# This will raise CacheError
cache.clear_all(confirm=False)  # Safety check
```

### Context Manager Support

```python
with CacheManager() as cache:
    cache.set("stocks", "AAPL", {"price": 150.25})
    data = cache.get("stocks", "AAPL")
# Connection automatically closed
```

## Database Schema

```sql
CREATE TABLE cache (
    cache_key TEXT PRIMARY KEY,        -- Format: "asset_class:SYMBOL"
    asset_class TEXT NOT NULL,         -- Asset category (stocks, bonds, etc.)
    symbol TEXT NOT NULL,              -- Asset identifier (AAPL, MSFT, etc.)
    data TEXT NOT NULL,                -- JSON-encoded data
    created_at TEXT NOT NULL,          -- ISO 8601 timestamp
    expires_at TEXT NOT NULL,          -- ISO 8601 expiration time
    hit_count INTEGER DEFAULT 0,       -- Number of cache hits
    last_accessed TEXT                 -- Last access timestamp
);

-- Indexes
CREATE INDEX idx_asset_symbol ON cache(asset_class, symbol);
CREATE INDEX idx_expires_at ON cache(expires_at);
```

## Cache Key Format

Cache keys follow the pattern: `{asset_class}:{SYMBOL}`

**Examples:**
- `stocks:AAPL` - Apple stock
- `bonds:US10Y` - 10-year US Treasury
- `commodities:GC` - Gold futures
- `currencies:EURUSD` - EUR/USD pair

**Normalization:**
- Asset class: Converted to lowercase
- Symbol: Converted to uppercase

```python
# All of these generate "stocks:AAPL"
cache.get("stocks", "AAPL")
cache.get("STOCKS", "aapl")
cache.get("Stocks", "AaPl")
```

## Configuration

Configured via `src.config.CacheConfig`:

```python
class CacheConfig:
    # Cache TTL (default: 15 minutes)
    TTL_SECONDS: int = 900

    # Database location
    DATA_DIR: Path = Path("data")
    DB_PATH: Path = DATA_DIR / "bloomberg_cache.db"
```

**Environment Variables:**
```bash
# .env file
CACHE_TTL_SECONDS=900           # 15 minutes
DATA_DIR=data                   # Data directory
```

## Usage Patterns

### Pattern 1: Simple Cache-Aside

```python
def get_stock_data(symbol: str) -> dict:
    """Fetch stock data with caching."""
    # Check cache first
    cached = cache.get("stocks", symbol)
    if cached:
        return cached

    # Cache miss - fetch from API
    data = fetch_from_bloomberg_api(symbol)

    # Store in cache
    cache.set("stocks", symbol, data)

    return data
```

### Pattern 2: Batch Processing with Statistics

```python
def process_symbols(symbols: list[str]):
    """Process multiple symbols efficiently."""
    results = []

    for symbol in symbols:
        data = cache.get("stocks", symbol)
        if not data:
            data = fetch_from_api(symbol)
            cache.set("stocks", symbol, data)
        results.append(data)

    # Show efficiency
    stats = cache.get_statistics()
    efficiency = (stats['total_hits'] / len(symbols)) * 100
    print(f"Cache efficiency: {efficiency:.1f}%")

    return results
```

### Pattern 3: Periodic Cleanup

```python
import schedule

def cleanup_cache():
    """Periodic cache maintenance."""
    deleted = cache.clear_expired()
    logger.info(f"Removed {deleted} expired entries")

    stats = cache.get_statistics()
    if stats['cache_size_mb'] > 100:  # 100 MB limit
        logger.warning(f"Cache size: {stats['cache_size_mb']} MB")

# Schedule cleanup every hour
schedule.every().hour.do(cleanup_cache)
```

### Pattern 4: Error Handling

```python
from src.utils.exceptions import CacheError

def safe_cache_operation(symbol: str):
    """Robust cache operations with fallback."""
    try:
        # Try cache
        data = cache.get("stocks", symbol)
        if data:
            return data

        # Fetch and cache
        data = fetch_from_api(symbol)
        cache.set("stocks", symbol, data)
        return data

    except CacheError as e:
        logger.error(f"Cache error: {e}")
        # Fallback to direct API call
        return fetch_from_api(symbol)
```

## Performance Characteristics

### Time Complexity
- `get()`: O(1) - Primary key lookup with index
- `set()`: O(1) - Single row insert/replace
- `invalidate()`: O(1) - Primary key delete
- `clear_expired()`: O(n) - Full table scan (uses index)
- `get_statistics()`: O(n) - Aggregation queries

### Space Complexity
- Each entry: ~500 bytes + JSON data size
- Indexes: ~50 bytes per entry
- Total: `(entry_count * (550 + avg_data_size)) bytes`

### Benchmarks (Approximate)

**Operations per second (single-threaded):**
- `get()`: ~50,000 ops/sec
- `set()`: ~20,000 ops/sec
- `invalidate()`: ~30,000 ops/sec

**Concurrent access:**
- Thread-safe with `check_same_thread=False`
- SQLite lock contention under heavy writes
- Optimized for read-heavy workloads

## Thread Safety

SQLite connection configured for multi-threaded access:

```python
sqlite3.connect(
    str(db_path),
    check_same_thread=False,      # Allow multi-threaded
    isolation_level='IMMEDIATE'   # Better concurrency
)
```

**Best Practices:**
- Safe for concurrent reads
- Write operations serialized by SQLite
- Use connection pooling for high concurrency
- Consider Redis for >100 concurrent writers

## Error Handling

All operations raise `CacheError` with detailed context:

```python
try:
    cache.set("stocks", "AAPL", data)
except CacheError as e:
    print(f"Operation: {e.operation}")
    print(f"Key: {e.cache_key}")
    print(f"Details: {e.details}")
```

**Common Errors:**
- Database locked (concurrent writes)
- JSON serialization failure (invalid data types)
- Disk full (write operations)
- Corrupted database (file damage)

## Monitoring and Observability

### Log Levels

- `DEBUG`: Cache hits/misses, operations
- `INFO`: Initialization, cleanup, invalidations
- `WARNING`: Large cache size, high miss rate
- `ERROR`: Database errors, serialization failures

### Metrics to Track

```python
stats = cache.get_statistics()

# Key performance indicators
hit_rate = stats['total_hits'] / (stats['total_hits'] + miss_count)
avg_hits = stats['average_hits']
cache_size = stats['cache_size_mb']
valid_ratio = stats['valid_entries'] / stats['total_entries']

# Alert conditions
if hit_rate < 0.5:
    logger.warning(f"Low cache hit rate: {hit_rate:.2%}")
if cache_size > 100:
    logger.warning(f"Large cache size: {cache_size} MB")
if valid_ratio < 0.8:
    logger.info("Running cleanup...")
    cache.clear_expired()
```

## Testing

Run comprehensive test suite:

```bash
# Run all cache tests
pytest tests/test_cache_manager.py -v

# Run specific test class
pytest tests/test_cache_manager.py::TestCacheOperations -v

# Run with coverage
pytest tests/test_cache_manager.py --cov=src.orchestrator.cache_manager
```

## Examples

See `examples/cache_manager_usage.py` for complete examples:

```bash
cd C:\Users\USER\claude_code\bloomberg_data
python examples/cache_manager_usage.py
```

## Troubleshooting

### Cache Always Missing

**Symptom:** `get()` always returns `None`

**Solutions:**
1. Check if data was actually stored: `stats = cache.get_statistics()`
2. Verify TTL hasn't expired: `print(cache.ttl_seconds)`
3. Confirm asset_class/symbol match exactly
4. Check for database corruption

### Database Locked Errors

**Symptom:** `CacheError: database is locked`

**Solutions:**
1. Reduce concurrent write operations
2. Implement retry logic with backoff
3. Use read-only cache for read-heavy workloads
4. Consider Redis for high concurrency

### Large Cache Size

**Symptom:** Database file growing too large

**Solutions:**
1. Run `clear_expired()` more frequently
2. Reduce TTL for less critical data
3. Implement cache size limits
4. Archive old data to separate storage

### Performance Degradation

**Symptom:** Slow cache operations

**Solutions:**
1. Run `VACUUM` to defragment: `cache.clear_all(confirm=True)`
2. Check index health
3. Monitor disk I/O
4. Consider in-memory cache for hot data

## Migration and Upgrades

### Backing Up Cache

```python
import shutil
from pathlib import Path

# Backup database
db_path = Path("data/bloomberg_cache.db")
backup_path = Path("data/cache_backup.db")
shutil.copy2(db_path, backup_path)
```

### Clearing Cache

```python
# Safe clear with confirmation
cache.clear_all(confirm=True)

# Or delete database file
cache.close()
db_path.unlink()
```

## Best Practices

1. **Always use context manager** for automatic cleanup
2. **Check cache before API calls** to reduce costs
3. **Run periodic cleanup** to remove expired entries
4. **Monitor cache statistics** for optimization
5. **Handle CacheError gracefully** with fallbacks
6. **Use appropriate TTL** based on data volatility
7. **Close connections** when done to prevent leaks
8. **Validate data** before caching to avoid corruption

## Related Components

- `CostTracker`: Budget management and API cost tracking
- `BrightDataConfig`: Proxy configuration for API calls
- `SchedulerConfig`: Automatic update intervals
- `CacheConfig`: Cache-specific configuration

## References

- SQLite Documentation: https://www.sqlite.org/docs.html
- Python sqlite3: https://docs.python.org/3/library/sqlite3.html
- Cache-Aside Pattern: https://docs.microsoft.com/en-us/azure/architecture/patterns/cache-aside
