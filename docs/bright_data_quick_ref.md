# Bright Data Client - Quick Reference

## Installation

```bash
pip install aiohttp>=3.9.0
```

## Basic Usage

```python
from src.clients import BrightDataClient, BrightDataClientConfig

config = BrightDataClientConfig.from_env()
async with BrightDataClient(config, cost_tracker, cache) as client:
    html = await client.fetch(url)
```

## Methods

| Method | Signature | Description |
|--------|-----------|-------------|
| `fetch()` | `async fetch(url, use_cache=True) -> Optional[str]` | Fetch single URL |
| `fetch_multiple()` | `async fetch_multiple(urls, max_concurrent=5) -> dict` | Fetch multiple URLs |
| `get_cache_stats()` | `get_cache_stats() -> dict` | Get cache metrics |
| `get_cost_stats()` | `get_cost_stats() -> dict` | Get cost metrics |
| `get_stats()` | `get_stats() -> dict` | Get all statistics |
| `close()` | `async close() -> None` | Close HTTP session |

## Configuration

```python
BrightDataClientConfig(
    api_token="token",      # Required
    zone="bloomberg",       # Default: "bloomberg"
    endpoint="...",         # Default: Bright Data API
    timeout=30,             # Default: 30 seconds
    max_retries=3,          # Default: 3
    base_delay=1.0          # Default: 1.0 second
)
```

## Error Handling

```python
from src.clients import AuthError, ServerError
from src.utils.exceptions import BudgetExhaustedError, RateLimitError

try:
    html = await client.fetch(url)
except BudgetExhaustedError:
    # Budget limit reached
    pass
except AuthError:
    # 401/403 authentication failed
    pass
except RateLimitError:
    # 429 rate limit (auto-retried)
    pass
except ServerError:
    # 5xx server error (auto-retried)
    pass
```

## Retry Logic

| Error | Retry? | Max | Backoff |
|-------|--------|-----|---------|
| 401/403 | ❌ No | - | - |
| 429 | ✅ Yes | 3 | Exponential |
| 5xx | ✅ Yes | 3 | Exponential |

**Backoff**: `delay = 1.0 * (2^attempt) + jitter`

## Statistics

```python
# Cache stats
cache_stats = client.get_cache_stats()
# → {"cache_hits": 10, "cache_misses": 5, "hit_rate": 0.667}

# Cost stats
cost_stats = client.get_cost_stats()
# → {"requests_made": 15, "total_cost": 0.0225, "remaining_budget": 5.4775}

# All stats
all_stats = client.get_stats()
# → {"requests_made": 15, "cache": {...}, "cost": {...}, ...}
```

## Environment Variables

```env
BRIGHT_DATA_TOKEN=your_token
BRIGHT_DATA_ZONE=bloomberg
REQUEST_TIMEOUT=30
TOTAL_BUDGET=5.50
COST_PER_REQUEST=0.0015
```

## Examples

### Single Fetch
```python
html = await client.fetch("https://www.bloomberg.com/quote/AAPL:US")
```

### Multiple Fetch
```python
urls = ["https://www.bloomberg.com/quote/AAPL:US", ...]
results = await client.fetch_multiple(urls, max_concurrent=5)
```

### Disable Cache
```python
html = await client.fetch(url, use_cache=False)
```

### Check Budget First
```python
if cost_tracker.can_make_request():
    html = await client.fetch(url)
```

## Best Practices

1. ✅ Use `async with` context manager
2. ✅ Enable caching for repeated requests
3. ✅ Use `fetch_multiple()` for concurrent requests
4. ✅ Monitor budget before large operations
5. ✅ Handle specific exceptions gracefully
6. ❌ Don't create multiple client instances
7. ❌ Don't disable retry without good reason
8. ❌ Don't ignore BudgetExhaustedError

## Common Patterns

### Production Crawler
```python
async def crawl():
    config = BrightDataClientConfig.from_env()
    async with BrightDataClient(config, tracker, cache) as client:
        try:
            results = await client.fetch_multiple(urls, max_concurrent=3)
            stats = client.get_stats()
            logger.info(f"Completed: {stats}")
            return results
        except BudgetExhaustedError:
            logger.error("Budget exhausted")
            raise
```

### With Error Recovery
```python
async def safe_fetch(url):
    try:
        return await client.fetch(url)
    except AuthError:
        logger.error("Auth failed, check credentials")
        return None
    except Exception as e:
        logger.error(f"Fetch failed: {e}")
        return None
```

## Performance Tips

- **Concurrency**: Start with `max_concurrent=5`, adjust based on performance
- **Caching**: Can reduce API costs by ~70%
- **Batch**: Use `fetch_multiple()` instead of loops
- **Monitor**: Check stats regularly to identify bottlenecks

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "Authentication failed" | Check `BRIGHT_DATA_TOKEN` in `.env` |
| "Budget exhausted" | Increase `TOTAL_BUDGET` or enable caching |
| Timeout errors | Increase `timeout` in config |
| Rate limit errors | Reduce `max_concurrent` |

## API Reference

See full documentation: `docs/bright_data_usage.md`
