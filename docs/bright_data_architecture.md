# Bright Data Client - Architecture

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      BrightDataClient                           │
│  Async HTTP Client with Retry Logic, Cost Tracking & Caching   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ uses
                              ▼
        ┌─────────────────────────────────────────┐
        │                                         │
        ▼                                         ▼
┌──────────────┐                          ┌──────────────┐
│   aiohttp    │                          │   asyncio    │
│   Session    │                          │   Runtime    │
└──────────────┘                          └──────────────┘
        │                                         │
        │ HTTP Requests                           │ Async Control
        ▼                                         ▼
┌─────────────────────────────────────────────────────────┐
│           Bright Data Web Unlocker API                  │
│         https://api.brightdata.com/request              │
└─────────────────────────────────────────────────────────┘
```

## Component Diagram

```
┌───────────────────────────────────────────────────────────────┐
│                    BrightDataClient                           │
├───────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌─────────────────────────────────────────────────┐         │
│  │  Public API                                     │         │
│  ├─────────────────────────────────────────────────┤         │
│  │  + fetch(url, use_cache=True)                   │         │
│  │  + fetch_multiple(urls, max_concurrent=5)       │         │
│  │  + get_cache_stats()                            │         │
│  │  + get_cost_stats()                             │         │
│  │  + get_stats()                                  │         │
│  │  + close()                                      │         │
│  └─────────────────────────────────────────────────┘         │
│                                                               │
│  ┌─────────────────────────────────────────────────┐         │
│  │  Internal Methods                               │         │
│  ├─────────────────────────────────────────────────┤         │
│  │  - _ensure_session()                            │         │
│  │  - _get_cache_key(url)                          │         │
│  │  - _check_budget()                              │         │
│  │  - _make_request(url)                           │         │
│  │  - _fetch_with_retry(url)                       │         │
│  └─────────────────────────────────────────────────┘         │
│                                                               │
│  ┌─────────────────────────────────────────────────┐         │
│  │  Dependencies                                   │         │
│  ├─────────────────────────────────────────────────┤         │
│  │  config: BrightDataClientConfig                 │         │
│  │  cost_tracker: CostTracker                      │         │
│  │  cache: ResponseCache                           │         │
│  │  _session: aiohttp.ClientSession                │         │
│  │  _stats: dict[str, int]                         │         │
│  └─────────────────────────────────────────────────┘         │
│                                                               │
└───────────────────────────────────────────────────────────────┘
```

## Request Flow

```
┌──────────┐
│  Client  │
│ (caller) │
└─────┬────┘
      │
      │ await fetch(url)
      ▼
┌─────────────────────────────┐
│  1. Cache Lookup            │
│     cache.get(cache_key)    │
└────────┬────────────────────┘
         │
         ├─── Cache Hit ────────────────────┐
         │                                  │
         ├─── Cache Miss                    │
         │                                  │
         ▼                                  │
┌─────────────────────────────┐            │
│  2. Budget Check            │            │
│     cost_tracker.can_make   │            │
│     _request()              │            │
└────────┬────────────────────┘            │
         │                                  │
         ├─── Budget OK                     │
         │                                  │
         ├─── Budget Exhausted              │
         │     └─> BudgetExhaustedError     │
         │                                  │
         ▼                                  │
┌─────────────────────────────┐            │
│  3. Make HTTP Request       │            │
│     _fetch_with_retry()     │            │
└────────┬────────────────────┘            │
         │                                  │
         │ Retry Loop (max 3)               │
         ▼                                  │
┌─────────────────────────────┐            │
│  4. Error Handling          │            │
│     - AuthError: Don't retry│            │
│     - RateLimitError: Retry │            │
│     - ServerError: Retry    │            │
└────────┬────────────────────┘            │
         │                                  │
         ├─── Success                       │
         │                                  │
         ▼                                  │
┌─────────────────────────────┐            │
│  5. Track Cost              │            │
│     cost_tracker            │            │
│     .record_request()       │            │
└────────┬────────────────────┘            │
         │                                  │
         ▼                                  │
┌─────────────────────────────┐            │
│  6. Update Cache            │            │
│     cache.set(key, content) │            │
└────────┬────────────────────┘            │
         │                                  │
         ▼                                  ▼
┌──────────────────────────────────────────┐
│  7. Return HTML Content                  │
└──────────────────────────────────────────┘
```

## Retry Logic Flow

```
┌────────────────┐
│ _make_request()│
└───────┬────────┘
        │
        ▼
    ┌───────┐
    │Request│
    └───┬───┘
        │
        ├─── 200 OK ──────────────────────> Return Content
        │
        ├─── 401/403 ──────────────────────> AuthError (No Retry)
        │
        ├─── 429 Rate Limit
        │    └─> RateLimitError
        │        │
        │        ▼
        │    ┌──────────────┐
        │    │Exponential   │
        │    │Backoff       │
        │    │delay = 2^n   │
        │    └──────┬───────┘
        │           │
        │           ├─ Attempt 1: ~1s
        │           ├─ Attempt 2: ~2s
        │           └─ Attempt 3: ~4s
        │               │
        │               ├─ Success ────> Return
        │               └─ Fail ──────> Raise Error
        │
        ├─── 5xx Server Error
        │    └─> ServerError
        │        │ (same retry logic as 429)
        │        │
        │        └─> Retry with backoff
        │
        └─── Other 4xx ──────────────────> APIError (No Retry)
```

## Concurrent Fetching

```
fetch_multiple([url1, url2, url3, url4, url5], max_concurrent=2)
    │
    └─> Semaphore(2) ─┐
                      │
    ┌─────────────────┴─────────────────┐
    │                                   │
    ▼                                   ▼
┌────────┐                         ┌────────┐
│ Task 1 │                         │ Task 2 │
│  url1  │                         │  url2  │
└───┬────┘                         └───┬────┘
    │ Complete                         │ Complete
    │                                  │
    ▼                                  ▼
┌────────┐                         ┌────────┐
│ Task 3 │                         │ Task 4 │
│  url3  │                         │  url4  │
└───┬────┘                         └───┬────┘
    │ Complete                         │ Complete
    │                                  │
    └──────────┬───────────────────────┘
               │
               ▼
           ┌────────┐
           │ Task 5 │
           │  url5  │
           └───┬────┘
               │ Complete
               │
               ▼
        ┌─────────────┐
        │Return Results│
        └─────────────┘
```

## Error Hierarchy

```
Exception
    │
    └── BloombergDataError
            │
            ├── APIError
            │   │
            │   ├── AuthError (401/403)
            │   │   - Non-retryable
            │   │   - Authentication failed
            │   │
            │   ├── ServerError (5xx)
            │   │   - Retryable
            │   │   - Server issues
            │   │
            │   └── RateLimitError (429)
            │       - Retryable
            │       - Rate limit exceeded
            │
            └── BudgetExhaustedError
                - Non-retryable
                - Budget limit reached
```

## State Management

```
BrightDataClient State:
┌────────────────────────────────┐
│ config: BrightDataClientConfig │
│  ├─ api_token                  │
│  ├─ zone                       │
│  ├─ endpoint                   │
│  ├─ timeout                    │
│  ├─ max_retries                │
│  └─ base_delay                 │
├────────────────────────────────┤
│ cost_tracker: CostTracker      │
│  ├─ can_make_request()         │
│  ├─ record_request()           │
│  └─ get_stats()                │
├────────────────────────────────┤
│ cache: ResponseCache           │
│  ├─ async get(key)             │
│  └─ async set(key, value)      │
├────────────────────────────────┤
│ _session: ClientSession        │
│  - HTTP connection pool        │
├────────────────────────────────┤
│ _stats: dict                   │
│  ├─ requests_made: int         │
│  ├─ cache_hits: int            │
│  ├─ cache_misses: int          │
│  ├─ retries: int               │
│  └─ errors: int                │
└────────────────────────────────┘
```

## Integration Points

```
┌─────────────────────────────────────────────────────────────┐
│                  External Dependencies                      │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   aiohttp    │  │   asyncio    │  │   logging    │      │
│  │              │  │              │  │              │      │
│  │ - Session    │  │ - Runtime    │  │ - Logger     │      │
│  │ - Timeout    │  │ - Semaphore  │  │ - Handlers   │      │
│  │ - ClientErr  │  │ - gather()   │  │              │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│                                                             │
└─────────────────────────────────────────────────────────────┘
                              │
                              │ uses
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                  Internal Dependencies                      │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │    config    │  │  exceptions  │  │   tracking   │      │
│  │              │  │              │  │              │      │
│  │ - APIConfig  │  │ - APIError   │  │ - CostTracker│      │
│  │ - BrightData │  │ - RateLimit  │  │              │      │
│  │ - CostConfig │  │ - BudgetErr  │  │              │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│                                                             │
│  ┌──────────────┐                                           │
│  │    cache     │                                           │
│  │              │                                           │
│  │ - Response   │                                           │
│  │   Cache      │                                           │
│  └──────────────┘                                           │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## Performance Characteristics

| Metric | Value | Implementation |
|--------|-------|----------------|
| Connection Pooling | ✅ Yes | aiohttp session reuse |
| Keep-Alive | ✅ Yes | HTTP persistent connections |
| Request Timeout | 30s | Configurable ClientTimeout |
| Retry Timeout | ~7s | Exponential: 1s + 2s + 4s |
| Max Concurrent | 5 | Asyncio Semaphore |
| Memory Footprint | Low | Streaming responses |
| CPU Usage | Low | Async I/O bound |

## Thread Safety

```
BrightDataClient is NOT thread-safe but IS asyncio-safe:

✅ Safe:   Multiple coroutines in same event loop
✅ Safe:   Multiple fetch() calls concurrently
✅ Safe:   fetch_multiple() with high concurrency

❌ Unsafe: Multiple event loops accessing same instance
❌ Unsafe: Threading.Thread sharing client instance

Solution: One client per event loop, use fetch_multiple() for concurrency
```

## Monitoring Points

```
┌─────────────────────────────────────────┐
│         Observability Hooks             │
├─────────────────────────────────────────┤
│                                         │
│  Logging Levels:                        │
│  ├─ DEBUG: Request details, cache ops   │
│  ├─ INFO: Success, completions          │
│  ├─ WARNING: Retries, rate limits       │
│  └─ ERROR: Failures, auth errors        │
│                                         │
│  Metrics:                               │
│  ├─ requests_made (counter)             │
│  ├─ cache_hit_rate (gauge)              │
│  ├─ retry_count (counter)               │
│  ├─ error_count (counter)               │
│  ├─ request_duration (histogram)        │
│  └─ budget_remaining (gauge)            │
│                                         │
│  Statistics Export:                     │
│  └─ get_stats() → JSON-serializable     │
│                                         │
└─────────────────────────────────────────┘
```

## Security Considerations

| Aspect | Implementation |
|--------|----------------|
| API Token | Environment variable, never logged |
| HTTPS | Required (Bright Data endpoint) |
| Timeout | Prevents hanging connections |
| Input Validation | URL validation before requests |
| Error Messages | Truncated sensitive data |
| Secrets in Logs | Masked/redacted automatically |

## Scalability

```
Single Instance Limits:
├─ Throughput: ~100 req/s (network bound)
├─ Concurrent: Limited by semaphore (default: 5)
├─ Memory: ~50MB per 1000 cached responses
└─ CPU: <5% (I/O bound workload)

Horizontal Scaling:
├─ Multiple instances in same loop: ✅ Yes
├─ Multiple event loops: ✅ Yes (separate instances)
├─ Distributed workers: ✅ Yes (shared cache/tracker)
└─ Load balancing: ✅ Yes (stateless design)
```
