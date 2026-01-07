# Orchestrator Components Guide

Comprehensive guide to the Bloomberg Data Crawler orchestration layer.

## Overview

The orchestrator layer provides intelligent coordination of data retrieval, cost optimization, fault tolerance, and automated scheduling.

## Components

### 1. CircuitBreaker

Implements the circuit breaker pattern for fault tolerance and resilience.

#### Purpose
- Prevent cascading failures
- Automatic recovery from transient errors
- Protect external services from overload

#### States
- **CLOSED**: Normal operation, requests pass through
- **OPEN**: Blocking requests due to failures
- **HALF_OPEN**: Testing recovery with single request

#### Usage

```python
from src.orchestrator import CircuitBreaker

# Initialize
breaker = CircuitBreaker(
    name="api_service",
    failure_threshold=5,      # Open after 5 consecutive failures
    recovery_timeout=60,      # Wait 60s before attempting recovery
    success_threshold=1       # Close after 1 success in HALF_OPEN
)

# Execute with protection
try:
    result = breaker.call(api_function, arg1, arg2)
    print(f"Success: {result}")
except CircuitBreakerError:
    print("Service unavailable - circuit is open")
```

#### Configuration

| Parameter | Default | Description |
|-----------|---------|-------------|
| `failure_threshold` | 5 | Failures before opening |
| `recovery_timeout` | 60 | Seconds before recovery attempt |
| `success_threshold` | 1 | Successes to close from HALF_OPEN |

#### Statistics

```python
stats = breaker.get_statistics()

# Key metrics:
# - state: Current circuit state
# - total_calls: Total function calls
# - total_failures: Total failures
# - failure_rate_pct: Percentage of failed calls
# - recovery_in_seconds: Time until recovery attempt
```

---

### 2. HybridDataSource

Priority-based data retrieval system with cost optimization.

#### Purpose
- Minimize API costs through intelligent source selection
- Automatic fallback through data source hierarchy
- Cache management for frequently accessed data

#### Data Source Priority

1. **Cache** (Cost: $0, TTL: 15 minutes)
2. **Bright Data** (Cost: $0.0015 per request, Bloomberg data)
3. **YFinance** (Cost: $0, fallback)

#### Usage

```python
import asyncio
from src.orchestrator import HybridDataSource
from src.normalizer.schemas import AssetClass

async def fetch_quotes():
    source = HybridDataSource()

    # Single quote
    quote = await source.get_quote("AAPL", AssetClass.STOCKS)
    if quote:
        print(f"{quote.symbol}: ${quote.price}")

    # Multiple quotes (concurrent)
    symbols = ["AAPL", "MSFT", "GOOGL"]
    quotes = await source.get_quotes(symbols, AssetClass.STOCKS)
    print(f"Fetched {len(quotes)} quotes")

    # Force fresh data (skip cache)
    fresh_quote = await source.get_quote("AAPL", AssetClass.STOCKS, force_fresh=True)

    # Cleanup
    await source.cleanup()

asyncio.run(fetch_quotes())
```

#### Symbol Format Conversion

HybridDataSource automatically converts between formats:

| Source | Format | Example |
|--------|--------|---------|
| Bloomberg | SYMBOL:EXCHANGE | `AAPL:US` |
| YFinance (Stocks) | SYMBOL | `AAPL` |
| YFinance (Forex) | PAIR=X | `EURUSD=X` |
| YFinance (Commodities) | SYMBOL=F | `GC=F` |

#### Statistics

```python
stats = source.get_statistics()

# Cache Performance
print(f"Cache Hit Rate: {stats['cache_statistics']['hit_rate_pct']}%")

# Source Usage
yf_stats = stats['source_usage']['yfinance']
print(f"YFinance Success Rate: {yf_stats['success_rate_pct']}%")
print(f"YFinance Cost: ${yf_stats['total_cost']}")

bd_stats = stats['source_usage']['bright_data']
print(f"Bright Data Requests: {bd_stats['total_requests']}")
print(f"Bright Data Cost: ${bd_stats['total_cost']}")

# Total Cost
cost = stats['cost_tracking']
print(f"Total Cost: ${cost['total_cost']}")
print(f"Budget Used: {cost['budget_used_pct']}%")
```

#### Error Handling

```python
from src.utils.exceptions import BudgetExhaustedError

try:
    quote = await source.get_quote("AAPL", AssetClass.STOCKS)
except BudgetExhaustedError as e:
    print(f"Budget limit reached: {e}")
    # Handle budget exhaustion (e.g., wait until reset)
```

---

### 3. DataScheduler

APScheduler-based automated data collection with maintenance tasks.

#### Purpose
- Periodic data collection for tracked symbols
- Automatic budget reset at midnight
- Cache cleanup to remove expired entries

#### Scheduled Tasks

| Task | Schedule | Description |
|------|----------|-------------|
| Data Collection | Every N minutes | Fetch quotes for all tracked symbols |
| Budget Reset | Daily at 00:00 | Reset cost tracker for new day |
| Cache Cleanup | Every hour | Remove expired cache entries |

#### Usage

```python
from src.orchestrator import DataScheduler
from src.normalizer.schemas import AssetClass

# Define tracking list
symbols = ["AAPL:US", "MSFT:US", "GOOGL:US"]
asset_classes = {
    "AAPL:US": AssetClass.STOCKS,
    "MSFT:US": AssetClass.STOCKS,
    "GOOGL:US": AssetClass.STOCKS,
}

# Create scheduler
scheduler = DataScheduler(
    symbols=symbols,
    asset_classes=asset_classes,
    update_interval_minutes=15  # Collect every 15 minutes
)

# Start scheduler
scheduler.start()

# ... let it run ...

# Check statistics
stats = scheduler.get_statistics()
print(f"Collections: {stats['collection_metrics']['total_collections']}")
print(f"Quotes Collected: {stats['collection_metrics']['total_quotes_collected']}")

# Stop scheduler
scheduler.stop()
```

#### Dynamic Symbol Management

```python
# Add symbol during runtime
scheduler.add_symbol("TSLA:US", AssetClass.STOCKS)

# Remove symbol
scheduler.remove_symbol("TSLA:US")

# Get tracked symbols
symbols = scheduler.get_tracked_symbols()
print(f"Tracking {len(symbols)} symbols")
```

#### Context Manager

```python
with DataScheduler(symbols, asset_classes) as scheduler:
    # Scheduler is automatically started
    print("Scheduler running...")
    time.sleep(60)  # Run for 1 minute
# Scheduler is automatically stopped on exit
```

#### Force Collection

```python
# Trigger immediate collection outside schedule
scheduler.force_collection()
```

#### Statistics

```python
stats = scheduler.get_statistics()

# Scheduler State
state = stats['scheduler_state']
print(f"Running: {state['is_running']}")
print(f"Symbols Tracked: {state['symbols_tracked']}")

# Collection Metrics
metrics = stats['collection_metrics']
print(f"Total Collections: {metrics['total_collections']}")
print(f"Success Rate: {metrics['success_rate_pct']}%")
print(f"Quotes Collected: {metrics['total_quotes_collected']}")

# Scheduled Jobs
for job in stats['scheduled_jobs']:
    print(f"Job: {job['name']}")
    print(f"Next Run: {job['next_run']}")
```

---

## Architecture Patterns

### Data Retrieval Flow

```
Request → Cache Check → Bright Data (Primary) → YFinance (Fallback)
            ↓                  ↓                      ↓
          $0.00             $0.0015                 $0.00
```

### Circuit Breaker Integration

Each data source has its own circuit breaker:

```python
# YFinance circuit breaker
- failure_threshold: 5
- recovery_timeout: 60 seconds

# Bright Data circuit breaker
- failure_threshold: 3
- recovery_timeout: 120 seconds
```

### Scheduler Workflow

```
Start Scheduler
    ↓
Schedule Jobs:
  - Data Collection (every N minutes)
  - Budget Reset (daily at midnight)
  - Cache Cleanup (hourly)
    ↓
Execute Jobs → Update Statistics → Repeat
    ↓
Stop Scheduler → Cleanup Resources
```

---

## Configuration

### Environment Variables

```bash
# Budget Configuration
TOTAL_BUDGET=5.50                    # Maximum daily budget (USD)
COST_PER_REQUEST=0.0015             # Cost per Bright Data request

# Cache Configuration
CACHE_TTL_SECONDS=900               # 15 minutes
DATA_DIR=data                       # Cache database location

# Scheduler Configuration
UPDATE_INTERVAL_SECONDS=900         # 15 minutes
AUTO_UPDATE_ENABLED=true
```

### Code Configuration

```python
from src.config import CostConfig, CacheConfig, SchedulerConfig

# View current configuration
print(f"Budget: ${CostConfig.TOTAL_BUDGET}")
print(f"Cache TTL: {CacheConfig.TTL_SECONDS}s")
print(f"Update Interval: {SchedulerConfig.UPDATE_INTERVAL_SECONDS}s")
```

---

## Error Handling

### Common Exceptions

```python
from src.utils.exceptions import (
    BudgetExhaustedError,
    APIError,
)
from src.orchestrator.circuit_breaker import CircuitBreakerError

# Budget Exhaustion
try:
    quote = await source.get_quote("AAPL", AssetClass.STOCKS)
except BudgetExhaustedError as e:
    print(f"Budget limit: {e.current_usage}/{e.budget_limit} requests")
    print(f"Cost spent: ${e.cost_spent}")

# Circuit Breaker Open
try:
    result = breaker.call(api_function)
except CircuitBreakerError as e:
    print(f"Circuit {e.state}: {e.message}")

# Generic API Error
try:
    quote = await source.get_quote("INVALID", AssetClass.STOCKS)
except APIError as e:
    print(f"API Error: {e.message}")
```

---

## Best Practices

### 1. Use Context Managers

```python
# Scheduler
with DataScheduler(symbols, asset_classes) as scheduler:
    # Resources automatically cleaned up on exit
    pass

# Hybrid Source
async def fetch():
    source = HybridDataSource()
    try:
        # ... use source ...
        pass
    finally:
        await source.cleanup()
```

### 2. Monitor Circuit Breakers

```python
# Check circuit breaker health
for name, breaker in source.breakers.items():
    if not breaker.is_available():
        print(f"Warning: {name} circuit is OPEN")
        stats = breaker.get_statistics()
        print(f"  Recovery in: {stats['state_info']['recovery_in_seconds']}s")
```

### 3. Track Costs

```python
# Regular cost monitoring
stats = source.get_statistics()
cost = stats['cost_tracking']

if cost['budget_used_pct'] > 80:
    print("Warning: 80% of budget used")
    print(f"Remaining: ${cost['budget_remaining']}")
```

### 4. Handle Budget Exhaustion

```python
# Graceful degradation
try:
    quote = await source.get_quote(symbol, asset_class)
except BudgetExhaustedError:
    # Fall back to cached data only
    quote = await source.get_quote(symbol, asset_class, force_fresh=False)
```

---

## Performance Considerations

### Cache Hit Rate
- **Target**: >60% for frequently accessed symbols
- **Optimization**: Longer TTL for stable data

### YFinance Success Rate
- **Target**: >80% for common stocks
- **Note**: Free tier has no rate limits

### Bright Data Usage
- **Target**: <20% of total requests
- **Optimization**: Maximize cache and YFinance usage

### Scheduler Interval
- **Minimum**: 1 minute (avoid excessive API calls)
- **Recommended**: 15 minutes (balance freshness and cost)
- **Maximum**: 60 minutes (data may become stale)

---

## Troubleshooting

### Circuit Breaker Stuck Open

```python
# Check state
print(f"State: {breaker.state}")
print(f"Recovery in: {breaker._get_recovery_time_remaining()}s")

# Manual reset (use with caution)
breaker.reset()
```

### High Bright Data Costs

```python
# Analyze usage
stats = source.get_statistics()
bd_stats = stats['source_usage']['bright_data']

print(f"Requests: {bd_stats['total_requests']}")
print(f"Cost: ${bd_stats['total_cost']}")
print(f"Failures: {bd_stats['failures']}")

# Solutions:
# 1. Increase cache TTL
# 2. Improve YFinance symbol conversion
# 3. Reduce collection frequency
```

### Scheduler Not Collecting

```python
# Check scheduler state
stats = scheduler.get_statistics()

print(f"Running: {stats['scheduler_state']['is_running']}")
print(f"Collections: {stats['collection_metrics']['total_collections']}")

# Check scheduled jobs
for job in stats['scheduled_jobs']:
    print(f"{job['name']}: next run at {job['next_run']}")

# Force collection to test
scheduler.force_collection()
```

---

## Examples

See `examples/hybrid_scheduler_demo.py` for comprehensive demonstrations.

### Quick Start

```python
import asyncio
from src.orchestrator import HybridDataSource, DataScheduler
from src.normalizer.schemas import AssetClass

async def main():
    # Option 1: Manual fetching
    source = HybridDataSource()
    quote = await source.get_quote("AAPL", AssetClass.STOCKS)
    print(f"{quote.symbol}: ${quote.price}")
    await source.cleanup()

    # Option 2: Automated scheduling
    symbols = ["AAPL", "MSFT"]
    asset_classes = {
        "AAPL": AssetClass.STOCKS,
        "MSFT": AssetClass.STOCKS,
    }

    with DataScheduler(symbols, asset_classes) as scheduler:
        # Let it collect data for 1 hour
        await asyncio.sleep(3600)

asyncio.run(main())
```

---

## API Reference

See source code docstrings for detailed API documentation:
- `src/orchestrator/circuit_breaker.py`
- `src/orchestrator/hybrid_source.py`
- `src/orchestrator/scheduler.py`
