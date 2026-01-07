# CostTracker Quick Reference

## Initialization
```python
from src.orchestrator import CostTracker
tracker = CostTracker()  # Thread-safe singleton
```

## Core Operations

### Check Budget
```python
if tracker.can_make_request():
    # Proceed with request
    pass
```

### Record Request
```python
result = tracker.record_request(
    asset_class='equity',  # 'equity', 'index', 'currency', etc.
    symbol='AAPL:US',
    success=True
)
```

### Get Statistics
```python
stats = tracker.get_statistics()
print(f"Budget used: {stats['budget_used_pct']}%")
print(f"Alert: {stats['alert_level']}")
```

### Check Alert Status
```python
alert = tracker.get_alert_status()
print(alert['recommendation'])
```

### Reset Tracker
```python
result = tracker.reset(confirm=True)
```

## Alert Levels

| Level | Threshold | Action |
|-------|-----------|--------|
| **OK** | 0-49% | Normal operations |
| **WARNING** | 50-79% | Monitor carefully |
| **CRITICAL** | 80-94% | Reduce request frequency |
| **DANGER** | 95-100% | Immediate action required |

## Configuration

From `src/config.py` (via `.env`):
- `TOTAL_BUDGET`: $5.50 (default)
- `COST_PER_REQUEST`: $0.0015 (default)

## Exception Handling

```python
from src.utils.exceptions import BudgetExhaustedError

try:
    tracker.can_make_request()
except BudgetExhaustedError as e:
    print(f"Budget exhausted: {e.message}")
```

## Common Patterns

### API Client Integration
```python
try:
    tracker.can_make_request()
    result = api_client.fetch(symbol)
    tracker.record_request('equity', symbol, success=True)
except BudgetExhaustedError:
    logger.error("Budget exhausted")
except APIError:
    tracker.record_request('equity', symbol, success=False)
    raise
```

### Alert Monitoring
```python
alert = tracker.get_alert_status()
if alert['alert_level'] in ['critical', 'danger']:
    send_alert(f"Budget {alert['budget_used_pct']}% consumed")
```

### Daily Report
```python
stats = tracker.get_statistics()
print(f"""
Budget Report
=============
Requests: {stats['total_requests']}
Success Rate: {stats['success_rate_pct']:.1f}%
Budget Used: {stats['budget_used_pct']:.1f}%
Days Until Exhaustion: {stats['prediction']['days_until_exhaustion']:.0f}
""")
```

## Important Statistics

```python
stats = tracker.get_statistics()

# Current status
stats['total_requests']        # Total requests made
stats['successful_requests']   # Successful requests
stats['failed_requests']       # Failed requests
stats['success_rate_pct']      # Success rate %

# Budget
stats['total_cost']            # Total cost ($)
stats['budget_remaining']      # Remaining budget ($)
stats['budget_used_pct']       # Budget used %
stats['alert_level']           # 'ok', 'warning', 'critical', 'danger'

# Averages
stats['daily_average_requests'] # Avg requests/day
stats['daily_average_cost']     # Avg cost/day ($)

# Prediction
stats['prediction']['days_until_exhaustion']     # Days until budget exhausted
stats['prediction']['estimated_exhaustion_date'] # Estimated date

# Breakdowns
stats['requests_by_date']      # {date: count}
stats['requests_by_asset']     # {asset_class: {symbol: count}}
```

## Files

- **Implementation**: `src/orchestrator/cost_tracker.py`
- **Tests**: `tests/test_cost_tracker.py`
- **Demo**: `examples/cost_tracker_demo.py`
- **Storage**: `logs/cost_tracking.json`
- **Docs**: `docs/COST_TRACKER.md`

## Testing

```bash
# Run tests
pytest tests/test_cost_tracker.py -v

# Run demo
python examples/cost_tracker_demo.py
```

## Thread Safety

- ✅ Singleton initialization is thread-safe
- ✅ Request recording is thread-safe
- ✅ Statistics reading is thread-safe
- ✅ Safe for concurrent access from multiple threads

## Best Practices

1. ✅ Always check `can_make_request()` before API calls
2. ✅ Record all requests (including failures)
3. ✅ Monitor alert levels regularly
4. ✅ Use descriptive asset classes
5. ✅ Handle `BudgetExhaustedError` gracefully
6. ❌ Don't create instances directly (use singleton)
7. ❌ Don't cache statistics (get fresh data)
8. ❌ Don't skip recording failed requests
