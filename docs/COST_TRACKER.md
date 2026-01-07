# CostTracker Documentation

## Overview

`CostTracker` is a thread-safe singleton class for managing API request budgets in the Bloomberg Data Crawler. It provides real-time cost tracking, multi-level alerts, usage statistics, and budget exhaustion predictions with persistent JSON storage.

## Features

- **Thread-Safe Singleton**: Single instance across application with thread-safe initialization
- **Budget Management**: Configurable budget tracking with $5.50 default, $0.0015 per request
- **Multi-Level Alerts**: 50% (WARNING), 80% (CRITICAL), 95% (DANGER) thresholds
- **Persistent Storage**: Automatic JSON persistence in `logs/cost_tracking.json`
- **Detailed Tracking**: Date-based and asset-class-based request tracking
- **Predictions**: Budget exhaustion estimation based on daily averages
- **Real-Time Statistics**: Comprehensive usage metrics and success rates

## Installation

```python
from src.orchestrator import CostTracker
```

## Configuration

Configuration is loaded from `src/config.py`:

```python
# Budget settings (from .env or defaults)
TOTAL_BUDGET = 5.50          # USD
COST_PER_REQUEST = 0.0015    # USD per API call

# Alert thresholds (hardcoded in CostTracker)
WARNING_THRESHOLD = 50%      # Budget half consumed
CRITICAL_THRESHOLD = 80%     # Budget mostly consumed
DANGER_THRESHOLD = 95%       # Budget nearly exhausted
```

## Basic Usage

### Initialize Tracker

```python
from src.orchestrator import CostTracker

# Get singleton instance
tracker = CostTracker()
```

### Check Budget Availability

```python
try:
    if tracker.can_make_request():
        # Budget available - proceed with request
        make_api_call()
except BudgetExhaustedError as e:
    # Budget exhausted - handle gracefully
    print(f"Budget exhausted: {e.message}")
    print(f"Used: {e.current_usage} / {e.budget_limit} requests")
```

### Record Request

```python
# Record successful request
result = tracker.record_request(
    asset_class='equity',
    symbol='AAPL:US',
    success=True
)

print(f"Request #{result['request_count']}")
print(f"Cost: ${result['total_cost']}")
print(f"Remaining: ${result['budget_remaining']}")
print(f"Alert: {result['alert_level']}")
```

### Get Statistics

```python
stats = tracker.get_statistics()

# Usage metrics
print(f"Total requests: {stats['total_requests']}")
print(f"Success rate: {stats['success_rate_pct']}%")
print(f"Budget used: {stats['budget_used_pct']}%")

# Prediction
if stats['prediction']['days_until_exhaustion']:
    print(f"Budget exhausted in {stats['prediction']['days_until_exhaustion']} days")
    print(f"Estimated date: {stats['prediction']['estimated_exhaustion_date']}")
```

## API Reference

### Core Methods

#### `can_make_request() -> bool`

Check if a new request can be made within budget.

**Returns:**
- `True` if budget available

**Raises:**
- `BudgetExhaustedError`: If budget completely exhausted

**Example:**
```python
if tracker.can_make_request():
    # Safe to proceed
    pass
```

#### `record_request(asset_class: str, symbol: str, success: bool = True) -> dict`

Record an API request and update all tracking metrics.

**Parameters:**
- `asset_class` (str): Asset type (e.g., 'equity', 'index', 'currency')
- `symbol` (str): Asset symbol (e.g., 'AAPL:US')
- `success` (bool): Whether request succeeded (default: True)

**Returns:**
Dictionary with:
- `request_count`: Total requests made
- `total_cost`: Total cost in USD
- `budget_remaining`: Remaining budget in USD
- `budget_used_pct`: Percentage of budget used
- `alert_level`: Current alert level
- `success`: Request success status
- `asset_class`: Asset class
- `symbol`: Symbol
- `timestamp`: ISO timestamp

**Example:**
```python
result = tracker.record_request('equity', 'MSFT:US', success=True)
if result['alert_level'] == 'critical':
    send_alert(f"Budget {result['budget_used_pct']}% consumed")
```

#### `get_statistics() -> dict`

Get comprehensive usage statistics and predictions.

**Returns:**
Dictionary with:

**Current Status:**
- `total_requests`: Total requests made
- `successful_requests`: Successful requests
- `failed_requests`: Failed requests
- `success_rate_pct`: Success rate percentage

**Budget Metrics:**
- `total_cost`: Total cost in USD
- `budget_limit`: Maximum budget
- `budget_remaining`: Remaining budget
- `budget_used_pct`: Percentage used
- `alert_level`: Current alert level

**Thresholds:**
- `thresholds`: Alert threshold percentages

**Time Tracking:**
- `tracking_start_date`: When tracking started
- `days_elapsed`: Days since start
- `daily_average_requests`: Average requests per day
- `daily_average_cost`: Average cost per day

**Prediction:**
- `prediction.days_until_exhaustion`: Estimated days until budget exhausted
- `prediction.estimated_exhaustion_date`: Predicted exhaustion date

**Detailed Breakdowns:**
- `requests_by_date`: Dictionary of date -> request count
- `daily_costs`: Dictionary of date -> cost
- `requests_by_asset`: Dictionary of asset_class -> {symbol: count}

**Example:**
```python
stats = tracker.get_statistics()

# Check alert level
if stats['alert_level'] in ['critical', 'danger']:
    print(f"⚠️ Budget alert: {stats['budget_used_pct']}% used")
    print(f"Only {stats['budget_remaining']:.2f} remaining")

# View asset breakdown
for asset_class, symbols in stats['requests_by_asset'].items():
    print(f"{asset_class}: {sum(symbols.values())} requests")
```

#### `get_alert_status() -> dict`

Get current alert status with actionable information.

**Returns:**
- `alert_level`: Current alert level
- `budget_used_pct`: Percentage of budget used
- `budget_remaining`: Remaining budget in USD
- `requests_remaining`: Number of requests remaining
- `recommendation`: Actionable recommendation
- `next_threshold`: Next threshold info (if applicable)
- `timestamp`: Current timestamp

**Example:**
```python
alert = tracker.get_alert_status()
print(f"Alert: {alert['alert_level'].upper()}")
print(f"Recommendation: {alert['recommendation']}")
print(f"Requests remaining: {alert['requests_remaining']}")
```

#### `reset(confirm: bool = True) -> dict`

Reset all tracking data and statistics.

**Parameters:**
- `confirm` (bool): Safety flag requiring explicit confirmation

**Returns:**
- `message`: Confirmation message
- `reset_timestamp`: When reset occurred
- `previous_statistics`: Statistics before reset

**Raises:**
- `ValueError`: If confirm=False

**Example:**
```python
# Reset tracker
result = tracker.reset(confirm=True)
print(f"{result['message']}")
print(f"Previous total: {result['previous_statistics']['total_requests']} requests")
```

## Alert Levels

### OK (0-49% budget used)
- **Status**: Healthy
- **Action**: None required
- **Recommendation**: Continue normal operations

### WARNING (50-79% budget used)
- **Status**: Moderate usage
- **Action**: Monitor carefully
- **Recommendation**: Review usage patterns, consider optimization

### CRITICAL (80-94% budget used)
- **Status**: High usage
- **Action**: Reduce request frequency
- **Recommendation**: Implement rate limiting, defer non-critical requests

### DANGER (95-100% budget used)
- **Status**: Near exhaustion
- **Action**: Immediate action required
- **Recommendation**: Stop non-essential requests, plan budget increase

## Persistence

### Automatic Storage

Data is automatically persisted to `logs/cost_tracking.json` after each request.

**Storage Location:**
```python
tracker.storage_path  # logs/cost_tracking.json
```

**Stored Data:**
- Total requests and costs
- Success/failure counts
- Date-based tracking
- Asset-based tracking
- Configuration snapshots

### Data Recovery

Data is automatically loaded on initialization:

```python
# Simulate application restart
CostTracker._instance = None
new_tracker = CostTracker()

# Data automatically recovered
print(f"Recovered {new_tracker.total_requests} requests")
```

### Manual Persistence Check

```python
import json

# Read persisted data
with open(tracker.storage_path, 'r') as f:
    data = json.load(f)

print(f"Last updated: {data['last_updated']}")
print(f"Total requests: {data['total_requests']}")
```

## Thread Safety

`CostTracker` is fully thread-safe with two-level locking:

### Singleton Initialization Lock
```python
# Multiple threads safely get same instance
threads = [threading.Thread(target=lambda: CostTracker()) for _ in range(10)]
for t in threads: t.start()
for t in threads: t.join()
# All threads get identical instance
```

### Request Recording Lock
```python
# Concurrent request recording is safe
def record_batch():
    for i in range(100):
        tracker.record_request('equity', f'SYM{i}:US', success=True)

threads = [threading.Thread(target=record_batch) for _ in range(5)]
for t in threads: t.start()
for t in threads: t.join()
# Exactly 500 requests recorded, no data corruption
```

## Integration Examples

### With API Client

```python
from src.orchestrator import CostTracker
from src.utils.exceptions import BudgetExhaustedError

class BloombergClient:
    def __init__(self):
        self.tracker = CostTracker()

    def fetch_data(self, symbol: str, asset_class: str = 'equity'):
        # Check budget before request
        try:
            self.tracker.can_make_request()
        except BudgetExhaustedError as e:
            logger.error(f"Budget exhausted: {e}")
            raise

        # Make API request
        try:
            response = self._make_request(symbol)

            # Record successful request
            self.tracker.record_request(asset_class, symbol, success=True)
            return response

        except Exception as e:
            # Record failed request
            self.tracker.record_request(asset_class, symbol, success=False)
            raise
```

### With Alert Monitoring

```python
import logging
from src.orchestrator import CostTracker

logger = logging.getLogger(__name__)

def monitor_budget():
    tracker = CostTracker()
    alert = tracker.get_alert_status()

    if alert['alert_level'] == 'warning':
        logger.warning(f"Budget 50% consumed: {alert['budget_used_pct']:.1f}%")
    elif alert['alert_level'] == 'critical':
        logger.critical(f"Budget 80% consumed: {alert['budget_used_pct']:.1f}%")
        send_email_alert(alert)
    elif alert['alert_level'] == 'danger':
        logger.critical(f"Budget 95% consumed - {alert['requests_remaining']} requests left")
        send_urgent_alert(alert)
        disable_non_critical_tasks()
```

### With Scheduler

```python
from apscheduler.schedulers.background import BackgroundScheduler
from src.orchestrator import CostTracker

def daily_budget_report():
    tracker = CostTracker()
    stats = tracker.get_statistics()

    report = f"""
    Daily Budget Report
    ==================
    Date: {stats['last_updated']}

    Requests Today: {stats['requests_by_date'].get(today, 0)}
    Total Requests: {stats['total_requests']}
    Success Rate: {stats['success_rate_pct']:.1f}%

    Budget Used: {stats['budget_used_pct']:.1f}%
    Budget Remaining: ${stats['budget_remaining']:.2f}

    Daily Average: {stats['daily_average_requests']:.1f} requests/day
    Days Until Exhaustion: {stats['prediction']['days_until_exhaustion']:.0f}
    """

    send_report(report)

# Schedule daily report
scheduler = BackgroundScheduler()
scheduler.add_job(daily_budget_report, 'cron', hour=0)
scheduler.start()
```

## Best Practices

### 1. Always Check Budget Before Requests

```python
# Good
if tracker.can_make_request():
    result = api_client.fetch(symbol)
    tracker.record_request('equity', symbol, success=True)

# Bad - no budget check
result = api_client.fetch(symbol)
tracker.record_request('equity', symbol, success=True)
```

### 2. Record All Requests (Including Failures)

```python
# Good
try:
    result = api_client.fetch(symbol)
    tracker.record_request('equity', symbol, success=True)
except APIError:
    tracker.record_request('equity', symbol, success=False)
    raise

# Bad - only recording successes skews statistics
result = api_client.fetch(symbol)
tracker.record_request('equity', symbol, success=True)
```

### 3. Monitor Alert Levels Regularly

```python
# Good - regular monitoring
def periodic_check():
    alert = tracker.get_alert_status()
    if alert['alert_level'] in ['critical', 'danger']:
        take_action(alert)

scheduler.add_job(periodic_check, 'interval', minutes=15)

# Bad - no monitoring until budget exhausted
```

### 4. Use Descriptive Asset Classes

```python
# Good - clear categorization
tracker.record_request('equity', 'AAPL:US', success=True)
tracker.record_request('index', 'SPX:IND', success=True)
tracker.record_request('currency', 'EURUSD:CUR', success=True)

# Bad - vague categories
tracker.record_request('stock', 'AAPL:US', success=True)
tracker.record_request('thing', 'SPX:IND', success=True)
```

### 5. Handle Budget Exhaustion Gracefully

```python
# Good - graceful degradation
try:
    tracker.can_make_request()
    fresh_data = api_client.fetch(symbol)
except BudgetExhaustedError:
    logger.warning("Budget exhausted, using cached data")
    fresh_data = cache.get(symbol)

# Bad - crashes on budget exhaustion
tracker.can_make_request()  # Unhandled exception
fresh_data = api_client.fetch(symbol)
```

## Troubleshooting

### Issue: Data Not Persisting

**Problem:** Changes not saved to `cost_tracking.json`

**Solution:**
```python
# Check write permissions
tracker = CostTracker()
print(f"Storage path: {tracker.storage_path}")
print(f"Path exists: {tracker.storage_path.exists()}")
print(f"Parent exists: {tracker.storage_path.parent.exists()}")

# Manually trigger save
tracker._save_data()
```

### Issue: Singleton Not Working

**Problem:** Multiple instances created

**Solution:**
```python
# Reset singleton properly
CostTracker._instance = None

# Don't create instances directly
tracker = CostTracker.__new__(CostTracker)  # Wrong!
tracker = CostTracker()  # Correct
```

### Issue: Inaccurate Predictions

**Problem:** Budget exhaustion prediction seems wrong

**Solution:**
```python
# Predictions based on daily averages
stats = tracker.get_statistics()
print(f"Days elapsed: {stats['days_elapsed']}")
print(f"Daily average cost: ${stats['daily_average_cost']}")

# More data = better predictions
# Need at least 3-7 days for accurate predictions
```

### Issue: Alert Level Not Updating

**Problem:** Alert stuck at old level

**Solution:**
```python
# Alert calculated on-demand
alert = tracker.get_alert_status()  # Always current

# Don't cache alert status
# alert = tracker.get_alert_status()  # Good
# cached_alert = alert  # Bad - becomes stale
```

## Performance Considerations

### Memory Usage
- Minimal overhead: ~1-2 KB for tracking data
- JSON file size: ~10-50 KB after 1000 requests
- Safe for high-volume applications

### Disk I/O
- Writes to disk on every request (async safe)
- Lightweight JSON serialization
- No performance impact on request throughput

### Thread Safety
- Double-checked locking for singleton
- Request-level locking for updates
- No lock contention in typical usage

## Testing

Run comprehensive test suite:

```bash
pytest tests/test_cost_tracker.py -v
```

Test coverage includes:
- Singleton pattern verification
- Thread safety under load
- Budget tracking accuracy
- Alert threshold triggers
- Statistics calculations
- Persistence and recovery
- Error handling
- Edge cases

## Migration Guide

### From Manual Tracking

**Before:**
```python
request_count = 0
total_cost = 0.0

def make_request(symbol):
    global request_count, total_cost
    request_count += 1
    total_cost += 0.0015
    return api.fetch(symbol)
```

**After:**
```python
tracker = CostTracker()

def make_request(symbol):
    if tracker.can_make_request():
        result = api.fetch(symbol)
        tracker.record_request('equity', symbol, success=True)
        return result
```

## See Also

- [Configuration Guide](CONFIG.md)
- [Error Handling](ERRORS.md)
- [API Client Integration](API_CLIENT.md)
- [Scheduler Integration](SCHEDULER.md)
