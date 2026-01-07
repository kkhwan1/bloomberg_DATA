# Bright Data Client Usage Guide

## Overview

The `BrightDataClient` is an asynchronous HTTP client for the Bright Data Web Unlocker API with built-in retry logic, cost tracking, and caching.

## Features

- **Async HTTP**: Built on `aiohttp` for high-performance concurrent requests
- **Exponential Backoff**: Automatic retry with exponential backoff (max 3 attempts)
- **Cost Tracking**: Integration with `CostTracker` for budget management
- **Caching**: Response caching to minimize API costs
- **Timeout Handling**: 30-second default timeout
- **Error Handling**: Comprehensive error classification and handling

## Installation

```bash
pip install -r requirements.txt
```

Ensure `.env` file contains:
```env
BRIGHT_DATA_TOKEN=your_api_token_here
BRIGHT_DATA_ZONE=bloomberg
```

## Basic Usage

### Single URL Fetch

```python
import asyncio
from src.clients import BrightDataClient, BrightDataClientConfig
from src.tracking.cost_tracker import CostTracker
from src.cache.response_cache import ResponseCache

async def fetch_bloomberg_data():
    # Initialize dependencies
    config = BrightDataClientConfig.from_env()
    cost_tracker = CostTracker()
    cache = ResponseCache()

    # Use async context manager
    async with BrightDataClient(config, cost_tracker, cache) as client:
        url = "https://www.bloomberg.com/quote/AAPL:US"
        html = await client.fetch(url)

        if html:
            print(f"Fetched {len(html)} bytes")
            print(f"Cache stats: {client.get_cache_stats()}")
            print(f"Cost stats: {client.get_cost_stats()}")
        else:
            print("Failed to fetch data")

# Run
asyncio.run(fetch_bloomberg_data())
```

### Multiple URLs (Concurrent)

```python
async def fetch_multiple_stocks():
    config = BrightDataClientConfig.from_env()
    cost_tracker = CostTracker()
    cache = ResponseCache()

    urls = [
        "https://www.bloomberg.com/quote/AAPL:US",
        "https://www.bloomberg.com/quote/MSFT:US",
        "https://www.bloomberg.com/quote/GOOGL:US",
        "https://www.bloomberg.com/quote/AMZN:US",
        "https://www.bloomberg.com/quote/TSLA:US",
    ]

    async with BrightDataClient(config, cost_tracker, cache) as client:
        # Fetch with max 5 concurrent requests
        results = await client.fetch_multiple(urls, max_concurrent=5)

        for url, html in results.items():
            if html:
                print(f"{url}: {len(html)} bytes")
            else:
                print(f"{url}: FAILED")

        # Print statistics
        stats = client.get_stats()
        print(f"\nStatistics:")
        print(f"  Requests made: {stats['requests_made']}")
        print(f"  Cache hit rate: {stats['cache']['hit_rate']}")
        print(f"  Total cost: ${stats['cost']['total_cost']:.4f}")

asyncio.run(fetch_multiple_stocks())
```

### Disable Caching

```python
async def fetch_fresh_data():
    config = BrightDataClientConfig.from_env()
    cost_tracker = CostTracker()
    cache = ResponseCache()

    async with BrightDataClient(config, cost_tracker, cache) as client:
        # Disable cache to get fresh data
        html = await client.fetch(
            "https://www.bloomberg.com/quote/AAPL:US",
            use_cache=False
        )
        print(f"Fresh data: {len(html)} bytes")

asyncio.run(fetch_fresh_data())
```

## Configuration

### Environment Variables

```env
# Bright Data credentials
BRIGHT_DATA_TOKEN=your_api_token
BRIGHT_DATA_ZONE=bloomberg

# Request settings
REQUEST_TIMEOUT=30

# Budget settings
TOTAL_BUDGET=5.50
COST_PER_REQUEST=0.0015
SAFETY_MARGIN=0.10
ALERT_THRESHOLD=0.80

# Cache settings
CACHE_TTL_SECONDS=900
```

### Custom Configuration

```python
from src.clients import BrightDataClientConfig

config = BrightDataClientConfig(
    api_token="custom_token",
    zone="custom_zone",
    endpoint="https://api.brightdata.com/request",
    timeout=60,  # 60 seconds
    max_retries=5,
    base_delay=2.0,  # 2 seconds initial delay
)
```

## Error Handling

### Exception Types

```python
from src.clients import AuthError, ServerError
from src.utils.exceptions import (
    BudgetExhaustedError,
    RateLimitError,
    APIError,
)

async def handle_errors():
    async with BrightDataClient(config, cost_tracker, cache) as client:
        try:
            html = await client.fetch(url)

        except BudgetExhaustedError as e:
            print(f"Budget exhausted: {e.current_usage}/{e.budget_limit}")

        except AuthError as e:
            print(f"Authentication failed: {e.status_code}")

        except RateLimitError as e:
            print(f"Rate limited. Retry after: {e.retry_after}s")

        except ServerError as e:
            print(f"Server error: {e.status_code}")

        except APIError as e:
            print(f"API error: {e.message}")
```

### Retry Behavior

| Error Type | Retry? | Max Retries | Backoff |
|------------|--------|-------------|---------|
| `AuthError` (401/403) | No | - | - |
| `RateLimitError` (429) | Yes | 3 | Exponential |
| `ServerError` (5xx) | Yes | 3 | Exponential |
| Other `APIError` | No | - | - |

**Exponential Backoff Formula**:
```
delay = base_delay * (2 ^ attempt) + random_jitter
```

Example delays:
- Attempt 1: ~1.0s (+ jitter)
- Attempt 2: ~2.0s (+ jitter)
- Attempt 3: ~4.0s (+ jitter)

## Statistics and Monitoring

### Cache Statistics

```python
cache_stats = client.get_cache_stats()
print(f"Cache hits: {cache_stats['cache_hits']}")
print(f"Cache misses: {cache_stats['cache_misses']}")
print(f"Hit rate: {cache_stats['hit_rate']:.1%}")
```

### Cost Statistics

```python
cost_stats = client.get_cost_stats()
print(f"Requests made: {cost_stats['requests_made']}")
print(f"Total cost: ${cost_stats['total_cost']:.4f}")
print(f"Remaining: ${cost_stats['remaining_budget']:.2f}")
print(f"Used: {cost_stats['budget_used_percent']:.1f}%")
```

### All Statistics

```python
stats = client.get_stats()
print(f"Requests: {stats['requests_made']}")
print(f"Cache hits: {stats['cache']['cache_hits']}")
print(f"Retries: {stats['retries']}")
print(f"Errors: {stats['errors']}")
print(f"Total cost: ${stats['cost']['total_cost']:.4f}")
```

## Best Practices

### 1. Use Context Manager

Always use async context manager to ensure proper session cleanup:

```python
async with BrightDataClient(config, cost_tracker, cache) as client:
    # Your code here
    pass
# Session automatically closed
```

### 2. Enable Caching

Use caching for repeated requests to save costs:

```python
# First call: fetches from API
html1 = await client.fetch(url, use_cache=True)

# Second call: returns cached data (no API cost)
html2 = await client.fetch(url, use_cache=True)
```

### 3. Batch Requests

Use `fetch_multiple()` for concurrent requests:

```python
# Efficient concurrent fetching
results = await client.fetch_multiple(urls, max_concurrent=5)

# Avoid sequential fetching
for url in urls:
    html = await client.fetch(url)  # Slower
```

### 4. Monitor Budget

Check budget before large operations:

```python
if cost_tracker.can_make_request():
    html = await client.fetch(url)
else:
    print("Budget exhausted!")
```

### 5. Handle Errors Gracefully

```python
try:
    html = await client.fetch(url)
except BudgetExhaustedError:
    # Stop operations
    return None
except RateLimitError:
    # Will auto-retry
    pass
except AuthError:
    # Check credentials
    raise
```

## API Payload Structure

The client sends the following payload to Bright Data API:

```json
{
  "zone": "bloomberg",
  "url": "https://www.bloomberg.com/quote/AAPL:US",
  "format": "raw"
}
```

Headers:
```
Authorization: Bearer {api_token}
Content-Type: application/json
```

## Troubleshooting

### Authentication Failed

**Error**: `AuthError: Authentication failed: 401`

**Solutions**:
1. Check `BRIGHT_DATA_TOKEN` in `.env`
2. Verify token is valid and not expired
3. Ensure token has proper permissions

### Rate Limit Exceeded

**Error**: `RateLimitError: Rate limit exceeded`

**Solutions**:
- Wait for automatic retry (exponential backoff)
- Reduce `max_concurrent` parameter
- Add delays between requests

### Budget Exhausted

**Error**: `BudgetExhaustedError: API request budget exhausted`

**Solutions**:
1. Increase `TOTAL_BUDGET` in `.env`
2. Enable caching to reduce API calls
3. Review and optimize request patterns

### Timeout Errors

**Error**: Connection timeout after 30s

**Solutions**:
1. Increase timeout in configuration
2. Check network connectivity
3. Verify API endpoint is accessible

## Performance Tips

1. **Use Concurrent Requests**: `fetch_multiple()` is faster than sequential fetches
2. **Enable Caching**: Reduces API costs by ~70% for repeated requests
3. **Optimize Concurrency**: Start with `max_concurrent=5`, adjust based on performance
4. **Monitor Stats**: Use `get_stats()` to identify bottlenecks

## Example: Production Usage

```python
import asyncio
import logging
from src.clients import BrightDataClient, BrightDataClientConfig
from src.tracking.cost_tracker import CostTracker
from src.cache.response_cache import ResponseCache

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def production_crawler():
    """Production-ready crawler with error handling and monitoring."""
    config = BrightDataClientConfig.from_env()
    cost_tracker = CostTracker()
    cache = ResponseCache()

    symbols = ["AAPL:US", "MSFT:US", "GOOGL:US", "AMZN:US", "TSLA:US"]
    urls = [f"https://www.bloomberg.com/quote/{s}" for s in symbols]

    try:
        async with BrightDataClient(config, cost_tracker, cache) as client:
            logger.info(f"Starting crawl for {len(urls)} URLs")

            # Fetch with concurrency control
            results = await client.fetch_multiple(
                urls,
                max_concurrent=3  # Conservative for production
            )

            # Process results
            successful = sum(1 for v in results.values() if v)
            logger.info(f"Successful: {successful}/{len(urls)}")

            # Log statistics
            stats = client.get_stats()
            logger.info(
                f"Stats - Requests: {stats['requests_made']}, "
                f"Cache hit rate: {stats['cache']['hit_rate']:.1%}, "
                f"Cost: ${stats['cost']['total_cost']:.4f}"
            )

            return results

    except BudgetExhaustedError as e:
        logger.error(f"Budget exhausted: {e}")
        raise

    except Exception as e:
        logger.error(f"Crawler failed: {e}", exc_info=True)
        raise

if __name__ == "__main__":
    asyncio.run(production_crawler())
```
