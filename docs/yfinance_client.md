# YFinance Client Documentation

## Overview

The `YFinanceClient` provides a wrapper around the `yfinance` library for fetching financial data from Yahoo Finance. This is a **free data source** (no API key required) supporting stocks, forex pairs, and commodity futures.

## Features

- **Zero Cost**: No API credentials or subscription required
- **Multi-Asset Support**: Stocks, forex, commodities
- **Data Normalization**: Standardized output format across all asset types
- **Error Handling**: Wraps yfinance exceptions into custom `APIError`
- **Bulk Fetching**: Efficient multi-symbol queries with error isolation
- **Historical Data**: OHLCV data with flexible periods and intervals
- **Context Manager**: Optional session reuse for better performance

## Supported Assets

### Stocks
```python
symbols = ["AAPL", "MSFT", "GOOGL", "AMZN", "META", "TSLA", "NVDA"]
```

### Forex Pairs
```python
forex_pairs = [
    "EURUSD=X",  # Euro to USD
    "GBPUSD=X",  # British Pound to USD
    "JPYUSD=X",  # Japanese Yen to USD
    "AUDUSD=X",  # Australian Dollar to USD
]
```

### Commodities
```python
commodities = [
    "GC=F",  # Gold Futures
    "CL=F",  # Crude Oil Futures
    "SI=F",  # Silver Futures
    "NG=F",  # Natural Gas Futures
]
```

## Installation

YFinance is included in the project dependencies:

```bash
pip install -r requirements.txt
```

Or install directly:

```bash
pip install yfinance>=0.2.32
```

## Basic Usage

### Fetch Single Quote

```python
from src.clients.yfinance_client import YFinanceClient

client = YFinanceClient()
quote = client.fetch_quote("AAPL")

if quote:
    print(f"{quote['symbol']}: ${quote['price']:.2f}")
    print(f"Change: {quote['change_percent']:+.2f}%")
```

### Fetch Historical Data

```python
client = YFinanceClient()

# Get 1 month of daily data
history = client.fetch_history("MSFT", period="1mo", interval="1d")

if history is not None:
    print(history[['Open', 'High', 'Low', 'Close', 'Volume']].tail())
```

### Fetch Multiple Symbols

```python
client = YFinanceClient()
symbols = ["AAPL", "MSFT", "GOOGL"]
quotes = client.fetch_multiple(symbols)

for symbol, quote in quotes.items():
    if quote:
        print(f"{symbol}: ${quote['price']:.2f}")
```

### Using Context Manager (Recommended for Bulk Operations)

```python
symbols = ["AAPL", "MSFT", "GOOGL", "AMZN", "META"]

# Reuses HTTP session for better performance
with YFinanceClient() as client:
    for symbol in symbols:
        quote = client.fetch_quote(symbol)
        if quote:
            print(f"{symbol}: ${quote['price']:.2f}")
```

## API Reference

### YFinanceClient

#### `__init__(timeout: int = 10)`

Initialize the client.

**Parameters:**
- `timeout` (int): Request timeout in seconds (default: 10)

#### `fetch_quote(symbol: str) -> Optional[dict]`

Fetch current market quote for a symbol.

**Parameters:**
- `symbol` (str): Ticker symbol (e.g., 'AAPL', 'EURUSD=X', 'GC=F')

**Returns:**
- `dict`: Normalized quote data or `None` if unavailable

**Raises:**
- `APIError`: If request fails

**Example:**
```python
quote = client.fetch_quote("AAPL")
# Returns:
# {
#     'symbol': 'AAPL',
#     'name': 'Apple Inc.',
#     'price': 150.25,
#     'change': 2.50,
#     'change_percent': 1.69,
#     'volume': 52000000,
#     'market_cap': 2400000000000,
#     'day_high': 152.00,
#     'day_low': 148.50,
#     'year_high': 180.00,
#     'year_low': 130.00,
#     'timestamp': '2026-01-07T16:00:00Z',
#     'source': 'yfinance'
# }
```

#### `fetch_history(symbol: str, period: str = "1d", interval: str = "1d") -> Optional[DataFrame]`

Fetch historical OHLCV data.

**Parameters:**
- `symbol` (str): Ticker symbol
- `period` (str): Time period
  - Valid: `1d`, `5d`, `1mo`, `3mo`, `6mo`, `1y`, `2y`, `5y`, `10y`, `ytd`, `max`
- `interval` (str): Data interval
  - Valid: `1m`, `2m`, `5m`, `15m`, `30m`, `60m`, `90m`, `1h`, `1d`, `5d`, `1wk`, `1mo`, `3mo`

**Returns:**
- `DataFrame`: OHLCV data with UTC timestamps, or `None` if unavailable

**Raises:**
- `APIError`: If request fails

**Example:**
```python
history = client.fetch_history("MSFT", period="1mo", interval="1d")
# Returns DataFrame with columns: Open, High, Low, Close, Volume, Symbol
```

#### `fetch_multiple(symbols: list[str]) -> dict[str, Optional[dict]]`

Fetch quotes for multiple symbols in bulk.

**Parameters:**
- `symbols` (list[str]): List of ticker symbols

**Returns:**
- `dict`: Mapping of symbol to quote data (or `None` if failed)

**Example:**
```python
quotes = client.fetch_multiple(["AAPL", "MSFT", "GOOGL"])
# Returns:
# {
#     'AAPL': {...},
#     'MSFT': {...},
#     'GOOGL': {...}
# }
```

## Data Format

All quote data is normalized to a standard format:

```python
{
    'symbol': str,           # Ticker symbol
    'name': str,             # Company/asset name
    'price': float,          # Current price
    'change': float,         # Price change from previous close
    'change_percent': float, # Percentage change
    'volume': int,           # Trading volume
    'market_cap': int,       # Market capitalization (stocks only)
    'day_high': float,       # Day's high price
    'day_low': float,        # Day's low price
    'year_high': float,      # 52-week high
    'year_low': float,       # 52-week low
    'timestamp': str,        # ISO 8601 timestamp (UTC)
    'source': str            # Always 'yfinance'
}
```

## Error Handling

All yfinance exceptions are wrapped in `APIError`:

```python
from src.utils.exceptions import APIError

try:
    quote = client.fetch_quote("AAPL")
except APIError as e:
    print(f"Error: {e.message}")
    print(f"Endpoint: {e.endpoint}")
    print(f"Details: {e.details}")
```

Graceful handling for missing data:

```python
quote = client.fetch_quote("INVALID_SYMBOL")
if quote is None:
    print("No data available for symbol")
```

## Performance Considerations

### Session Reuse

For multiple requests, use context manager to reuse HTTP session:

```python
# GOOD: Session reused across requests
with YFinanceClient() as client:
    for symbol in symbols:
        quote = client.fetch_quote(symbol)

# LESS EFFICIENT: New session per client instance
for symbol in symbols:
    client = YFinanceClient()
    quote = client.fetch_quote(symbol)
```

### Bulk Operations

Use `fetch_multiple()` for bulk queries - it isolates errors so one failure doesn't break the batch:

```python
# Handles partial failures gracefully
quotes = client.fetch_multiple(["AAPL", "INVALID", "MSFT"])
# Returns: {'AAPL': {...}, 'INVALID': None, 'MSFT': {...}}
```

### Rate Limiting

Yahoo Finance has informal rate limits. Best practices:
- Use reasonable timeouts (10-30 seconds)
- Implement retry logic for production use
- Cache frequently accessed data
- Avoid excessive concurrent requests

## Integration with Bloomberg Data Crawler

The YFinanceClient integrates seamlessly with the Bloomberg Data Crawler architecture:

```python
from src.clients.yfinance_client import YFinanceClient
from src.normalizer import DataNormalizer
from src.storage import StockRepository

# Fetch data
client = YFinanceClient()
quote = client.fetch_quote("AAPL")

# Normalize (already in standard format)
normalizer = DataNormalizer()
normalized = normalizer.normalize(quote)

# Store
repo = StockRepository()
repo.save(normalized)
```

## Limitations

1. **Data Quality**: Free tier data may have delays or gaps
2. **Rate Limits**: Undocumented but exists; be respectful
3. **Asset Coverage**: Not all assets available (limited bond/options data)
4. **Real-Time Data**: Quotes may be delayed 15-20 minutes
5. **Historical Limits**: Some intervals have period restrictions

## Testing

Comprehensive test suite included:

```bash
# Run all tests
pytest tests/test_yfinance_client.py -v

# Run with coverage
pytest tests/test_yfinance_client.py --cov=src.clients.yfinance_client
```

Test coverage includes:
- Quote fetching (success, fallback, errors)
- Historical data (timezones, empty data)
- Bulk operations (partial failures)
- Data normalization (missing fields, alternatives)
- Context manager behavior
- Multi-asset types (stocks, forex, commodities)

## Examples

See `examples/yfinance_demo.py` for comprehensive usage examples:

```bash
cd C:\Users\USER\claude_code\bloomberg_data
python examples/yfinance_demo.py
```

## Troubleshooting

### "No data available"

```python
quote = client.fetch_quote("SYMBOL")
if quote is None:
    # Check symbol validity at finance.yahoo.com
    # Try alternative symbol format (e.g., add exchange suffix)
```

### Timeout errors

```python
# Increase timeout
client = YFinanceClient(timeout=30)
```

### Import errors

```python
# Ensure yfinance is installed
pip install yfinance>=0.2.32

# Verify import
from src.clients.yfinance_client import YFinanceClient
```

## References

- [yfinance Documentation](https://pypi.org/project/yfinance/)
- [Yahoo Finance](https://finance.yahoo.com/)
- [Bloomberg Data Crawler Architecture](../STRUCTURE.md)
