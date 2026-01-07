# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Bloomberg Data Crawler - Cost-optimized financial data collection system for algorithmic trading. Uses hybrid data sources with priority-based retrieval: Cache → Free APIs (yfinance, Finnhub) → Paid API (Bright Data).

**Budget**: $5.50 total, $0.0015/request = ~3,667 paid requests available.

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run CLI (one-time fetch)
python -m src.main AAPL MSFT GOOGL --once

# Run CLI (scheduled, 15min interval)
python -m src.main AAPL MSFT --interval 15

# Check budget status
python -m src.main --budget

# Run all tests
python -m pytest tests/ -v

# Run single test file
python -m pytest tests/test_cost_tracker.py -v

# Run single test function
python -m pytest tests/test_bloomberg_parser.py::test_parse_next_data -v

# Run tests with coverage
python -m pytest tests/ --cov=src --cov-report=html

# Test Bright Data API directly
python scripts/test_bright_data_api.py

# Compare Bloomberg vs YFinance data
python scripts/compare_sources.py

# Crawl all 59 global indices
python scripts/crawl_indices.py

# Test index crawl (first 2 indices only)
python scripts/crawl_indices.py --test

# Crawl specific index by ID
python scripts/crawl_indices.py --index 25

# Crawl range of indices
python scripts/crawl_indices.py --range 1 10
```

## Architecture

```
src/main.py (CLI - argparse)
    │
    ├── orchestrator/
    │   ├── scheduler.py       APScheduler, 15min interval
    │   ├── hybrid_source.py   Priority: Cache → yfinance → Bright Data
    │   ├── cost_tracker.py    Singleton, JSON persistence
    │   ├── cache_manager.py   SQLite, 15min TTL
    │   └── circuit_breaker.py 3-state: CLOSED/OPEN/HALF_OPEN
    │
    ├── clients/
    │   ├── yfinance_client.py (FREE)
    │   ├── finnhub_ws.py      (FREE, WebSocket)
    │   └── bright_data.py     (PAID, Bearer token + JSON API)
    │
    ├── parsers/
    │   └── bloomberg_parser.py  Priority: __NEXT_DATA__ → JSON-LD → HTML
    │
    ├── normalizer/
    │   ├── schemas.py         Pydantic: MarketQuote, AssetClass enum
    │   └── transformer.py     from_yfinance(), from_bloomberg()
    │
    └── storage/
        ├── csv_writer.py      data/{asset_class}/{symbol}/YYYYMMDD.csv
        └── json_writer.py     data/{asset_class}/{symbol}/YYYYMMDD.jsonl
```

## Key Design Patterns

- **CostTracker**: Thread-safe singleton with JSON persistence (`logs/cost_tracking.json`)
- **CacheManager**: SQLite with 15-min TTL, auto-cleanup of expired entries
- **HybridDataSource**: Async, tries sources in cost order until success
- **CircuitBreaker**: 3-state machine protecting each data source independently
- **BloombergParser**: Extracts data from `__NEXT_DATA__` script tag (`pageProps.quote`)

## Bright Data API

Uses Bearer token authentication with JSON body (not proxy):
```python
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
payload = {"zone": "bloomberg", "url": target_url, "format": "raw"}
# POST to https://api.brightdata.com/request
```

## Bloomberg Parser Field Mapping

Bloomberg HTML uses `__NEXT_DATA__` with these field names in `pageProps.quote`:
- `price`, `priceChange1Day`, `percentChange1Day`
- `highPrice`, `lowPrice`, `openPrice`, `prevClose`
- `highPrice52Week`, `lowPrice52Week`
- `volume` (string with commas: "52,262,300.00")

## Configuration

Copy `.env.example` to `.env` and set `BRIGHT_DATA_TOKEN`. Key settings:
- `TOTAL_BUDGET=5.50` - Total USD budget
- `COST_PER_REQUEST=0.0015` - Per-request cost for Bright Data
- `CACHE_TTL_SECONDS=900` - 15-minute cache TTL
- `ALERT_THRESHOLD=0.80` - Warn at 80% budget usage

## Exception Hierarchy

All exceptions inherit from `BloombergDataError` in `src/utils/exceptions.py`:
- `BudgetExhaustedError` - API budget limit reached
- `CacheError` - Cache read/write failures
- `ParsingError` - Data extraction failures
- `APIError` → `RateLimitError` - HTTP/network errors
- `CircuitBreakerError` - Service protection triggered
- `DataNormalizationError` - Data transformation failures

## Testing

Uses pytest with fixtures in `tests/conftest.py`:
- `mock_cost_tracker` - Mock without affecting real budget
- `clean_cache_manager` - Isolated SQLite instance
- `sample_bloomberg_html` - HTML with JSON-LD data
- `mock_market_quote` - Sample MarketQuote object

## Symbol Formats

- Bloomberg: `AAPL:US`, `EURUSD:CUR`
- yfinance: `AAPL`, `EURUSD=X`, `GC=F` (commodities)
- Conversion handled in `HybridDataSource._convert_symbol_for_*`

## Global Index Crawling

59 global indices from Bloomberg JP, mapped in `data/index_urls.json`:
- Code format: `{COUNTRY}@{INDEX}` (e.g., `IN@BSE30`, `ZA@ALSH`)
- Bloomberg symbol mapping: `IN@BSE30` → `SENSEX:IND`, `ID@JKSE` → `JCI:IND`
- Output: `data/indices/{CODE}/YYYYMMDD.json` (individual files per index)
- Cost: 59 × $0.0015 = $0.0885 per full crawl
