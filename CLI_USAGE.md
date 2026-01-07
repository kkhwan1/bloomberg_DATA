# Bloomberg Data Crawler - CLI Usage Guide

## Quick Start

### Basic Usage

```bash
# Track stocks with 15-minute intervals (default)
python -m src.main AAPL MSFT GOOGL

# One-time data fetch (no scheduling)
python -m src.main AAPL --once

# Custom update interval
python -m src.main AAPL MSFT --interval 30
```

## Installation

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure environment variables:**

   Create a `.env` file in the project root:
   ```env
   # Required
   BRIGHT_DATA_TOKEN=your_bright_data_token_here

   # Optional (with defaults)
   TOTAL_BUDGET=5.50
   COST_PER_REQUEST=0.0015
   UPDATE_INTERVAL_SECONDS=900
   CACHE_TTL_SECONDS=900
   LOG_LEVEL=INFO
   ```

3. **Verify configuration:**
   ```bash
   python -m src.main --budget
   ```

## Command Reference

### Symbol Tracking

#### Track Multiple Symbols
```bash
# Stock symbols (default asset class)
python -m src.main AAPL MSFT GOOGL AMZN TSLA

# With Bloomberg format
python -m src.main AAPL:US MSFT:US GOOGL:US

# Mixed formats work
python -m src.main AAPL MSFT:US GOOGL
```

#### Asset Classes

```bash
# Stocks / Equities
python -m src.main AAPL MSFT --asset-class stocks
python -m src.main AAPL MSFT --asset-class equity

# Forex / Currency Pairs
python -m src.main EURUSD GBPUSD --asset-class forex
python -m src.main EUR/USD GBP/USD --asset-class currency

# Commodities
python -m src.main GC CL --asset-class commodities

# Indices
python -m src.main SPX DJI --asset-class index

# Cryptocurrency
python -m src.main BTCUSD ETHUSD --asset-class crypto
```

### Execution Modes

#### Scheduled Mode (Default)
Continuously collects data at specified intervals.

```bash
# Default: 15-minute intervals
python -m src.main AAPL MSFT GOOGL

# Custom interval: 30 minutes
python -m src.main AAPL MSFT --interval 30

# Custom interval: 5 minutes
python -m src.main AAPL --interval 5
```

**Features:**
- Automatic data collection at specified intervals
- Daily budget reset at midnight
- Hourly cache cleanup
- Graceful shutdown with Ctrl+C

**Output:**
```
======================================================================
  Bloomberg Data Crawler v1.0.0
======================================================================

  📈 Tracking 3 symbols:
     • AAPL
     • MSFT
     • GOOGL

  ⏱️  Update interval: 15 minutes
  💰 Budget: $5.50

  Press Ctrl+C to stop gracefully...

======================================================================
```

#### One-Time Mode
Fetches data once and exits immediately.

```bash
# Fetch single symbol
python -m src.main AAPL --once

# Fetch multiple symbols
python -m src.main AAPL MSFT GOOGL --once

# Force fresh data (skip cache)
python -m src.main AAPL --once --force-fresh
```

**Output:**
```
======================================================================
  MARKET QUOTES
======================================================================

  AAPL       $   182.45  [yfinance]
  MSFT       $   415.23  [yfinance]
  GOOGL      $   141.89  [yfinance]

  Successfully fetched 3/3 quotes

  Total Cost: $0.0000 | Budget Remaining: $5.5000

======================================================================
```

### Status & Monitoring

#### Budget Status
View comprehensive budget and cost statistics.

```bash
python -m src.main --budget
```

**Output:**
```
======================================================================
  BUDGET STATUS REPORT
======================================================================

📊 Budget Overview:
  Total Budget:        $5.50
  Spent:               $0.0045
  Remaining:           $5.4955
  Usage:               0.1%
  Alert Level:         ✅ OK

📈 Request Statistics:
  Total Requests:      3
  Successful:          3 (100.0%)
  Failed:              0
  Remaining Requests:  3663

📅 Daily Averages:
  Days Tracked:        1
  Avg Requests/Day:    3.0
  Avg Cost/Day:        $0.0045

🔮 Prediction:
  Budget exhaustion:   Not predicted (low usage)

💡 Recommendation:
  Budget usage is healthy. Continue normal operations.

======================================================================
```

#### Scheduler Status
View scheduler state and collection metrics (only when scheduler is running).

```bash
python -m src.main --status
```

**Output:**
```
======================================================================
  SCHEDULER STATUS REPORT
======================================================================

📍 Scheduler State:
  Status:              🟢 RUNNING
  Symbols Tracked:     3
  Update Interval:     15 minutes
  Total Collections:   5

📊 Collection Metrics:
  Total Collections:   5
  Successful:          5 (100.0%)
  Failed:              0
  Total Quotes:        15

⏰ Last Activity:
  Last Collection:     2026-01-07 14:45:00
  Last Budget Reset:   2026-01-07 00:00:00
  Last Cache Cleanup:  2026-01-07 14:00:00

📅 Scheduled Jobs:
  Market Data Collection    → 2026-01-07 15:00:00
  Daily Budget Reset        → 2026-01-08 00:00:00
  Cache Cleanup             → 2026-01-07 15:00:00

💾 Data Source Statistics:
  Cache Hit Rate:      73.3%
  Cache Entries:       15
  Cache Size:          42.3 KB

======================================================================
```

### Advanced Options

#### Logging Control

```bash
# Debug logging (verbose)
python -m src.main AAPL --log-level DEBUG

# Warning level (quiet)
python -m src.main AAPL --log-level WARNING

# Error only (minimal)
python -m src.main AAPL --log-level ERROR
```

#### Force Fresh Data

```bash
# Skip cache, force new API requests
python -m src.main AAPL --once --force-fresh

# Useful for:
# - Testing API connectivity
# - Getting latest data immediately
# - Cache validation
```

**Warning:** This increases API costs as it bypasses cache optimization.

### Help & Version

```bash
# Display help
python -m src.main --help

# Show version
python -m src.main --version
```

## Graceful Shutdown

When running in scheduled mode, press **Ctrl+C** to stop gracefully.

The crawler will:
1. Stop scheduled jobs
2. Complete in-progress data collection
3. Save all data to cache
4. Display shutdown summary

**Shutdown Summary:**
```
🛑 Shutting down gracefully...

======================================================================
  SHUTDOWN SUMMARY
======================================================================

  Total Collections:   12
  Quotes Collected:    36
  Success Rate:        100.0%

  Total Cost:          $0.0180
  Budget Remaining:    $5.4820

======================================================================
```

## Usage Examples

### Example 1: Monitor Tech Stocks
```bash
python -m src.main AAPL MSFT GOOGL AMZN TSLA --interval 15
```
Tracks 5 tech stocks with 15-minute updates.

### Example 2: Forex Trading
```bash
python -m src.main EURUSD GBPUSD USDJPY --asset-class forex --interval 5
```
Monitors 3 currency pairs with 5-minute updates.

### Example 3: Quick Price Check
```bash
python -m src.main AAPL MSFT --once
```
Fetches current prices once and exits.

### Example 4: High-Frequency Monitoring
```bash
python -m src.main AAPL --interval 1 --log-level WARNING
```
Updates every minute with minimal console output.

### Example 5: Daily Budget Check
```bash
# Morning: Check budget status
python -m src.main --budget

# Run crawler
python -m src.main AAPL MSFT GOOGL --interval 30

# Evening: Check final status
python -m src.main --budget
```

## Data Sources & Cost

The crawler uses a **3-tier priority system** to optimize costs:

| Priority | Source | Cost | TTL |
|----------|--------|------|-----|
| 1️⃣ | Cache | $0.00 | 15 min |
| 2️⃣ | YFinance | $0.00 | Real-time |
| 3️⃣ | Bright Data (Bloomberg) | $0.0015 | Real-time |

**Cost Optimization:**
- Cache hits: **Free** (0 cost)
- YFinance hits: **Free** (0 cost)
- Bright Data hits: **$0.0015 per request**

**Example Cost Calculation:**
```
5 symbols × 4 updates/hour × 24 hours × $0.0015 = $0.72/day
```

But with **cache optimization**:
```
5 symbols × 4 updates/hour × 24 hours × $0.0015 × 0.15 (cache miss rate)
= $0.11/day (85% cost savings!)
```

## Budget Management

### Budget Alerts

| Threshold | Alert Level | Action |
|-----------|-------------|--------|
| 50% | ⚠️ WARNING | Monitor usage carefully |
| 80% | 🔶 CRITICAL | Consider reducing frequency |
| 95% | 🚨 DANGER | Requests will be blocked soon |
| 100% | ❌ EXHAUSTED | No more requests allowed |

### Budget Reset

```bash
# Automatic: Daily at midnight
# Manual: Not exposed via CLI (use Python API)
```

### Monitoring Budget

```bash
# Check current budget status
python -m src.main --budget

# View prediction
# Shows estimated days until budget exhaustion
```

## Logs & Data

### Log Files
```
logs/
  ├── YYYYMMDD_bloomberg_crawler.log     # Daily rotating logs
  ├── YYYYMMDD_bloomberg_cost.log        # Cost tracking
  ├── YYYYMMDD_bloomberg_api.log         # API calls
  └── YYYYMMDD_bloomberg_parser.log      # Parsing operations
```

### Cache Database
```
data/
  └── bloomberg_cache.db                 # SQLite cache database
```

### Cost Tracking
```
logs/
  └── cost_tracking.json                 # Persistent cost data
```

## Error Handling

### Configuration Errors
```bash
$ python -m src.main AAPL

❌ Configuration Error

Please fix the following issues:
  • BRIGHT_DATA_TOKEN is not configured

Create a .env file with required settings:
  BRIGHT_DATA_TOKEN=your_token_here
  TOTAL_BUDGET=5.50
```

**Solution:** Create `.env` file with required settings.

### Budget Exhausted
```
🚨 Budget exhausted - cannot make more requests

Budget Status:
  Total: $5.50
  Used: $5.50
  Remaining: $0.00
```

**Solution:** Wait for daily reset or increase `TOTAL_BUDGET` in `.env`.

### Network Errors
```
⚠️ YFinance circuit breaker is open for AAPL
⚠️ Bright Data failed for MSFT: HTTP 503
```

**Solution:** Wait for circuit breaker recovery (auto-retry after cooldown).

## Best Practices

### 1. Start with Conservative Settings
```bash
# Use longer intervals initially
python -m src.main AAPL MSFT --interval 30
```

### 2. Monitor Budget Regularly
```bash
# Check budget before long runs
python -m src.main --budget

# Run crawler
python -m src.main AAPL MSFT GOOGL

# Check budget after
python -m src.main --budget
```

### 3. Use Cache Effectively
```bash
# Don't use --force-fresh unless necessary
# Default caching saves 85%+ costs
python -m src.main AAPL --once  # Good
python -m src.main AAPL --once --force-fresh  # Expensive
```

### 4. Optimize Symbol Count
```bash
# More symbols = higher cost
# Start small and scale up
python -m src.main AAPL MSFT  # $0.15/day
python -m src.main AAPL MSFT GOOGL AMZN TSLA  # $0.36/day
```

### 5. Use One-Time Mode for Testing
```bash
# Test configuration without scheduling
python -m src.main AAPL --once --log-level DEBUG
```

## Troubleshooting

### Issue: No data retrieved

**Symptoms:**
```
❌ No quotes retrieved
```

**Solutions:**
1. Check internet connectivity
2. Verify symbol format (try both `AAPL` and `AAPL:US`)
3. Check Bright Data credentials
4. View debug logs: `--log-level DEBUG`

### Issue: High costs

**Symptoms:**
```
🔶 CRITICAL: Budget is 80% consumed
```

**Solutions:**
1. Increase update interval: `--interval 60`
2. Reduce symbol count
3. Verify cache is working: `python -m src.main --status`
4. Check cache hit rate (should be >70%)

### Issue: Scheduler won't stop

**Symptoms:**
Ctrl+C doesn't stop the scheduler

**Solutions:**
1. Press Ctrl+C again (may take 2-3 seconds)
2. If stuck, use `Ctrl+Z` to background, then `kill %1`
3. Check logs for errors

## Environment Variables Reference

```env
# === Required ===
BRIGHT_DATA_TOKEN=your_token_here

# === Optional Budget Settings ===
TOTAL_BUDGET=5.50                    # Total budget in USD
COST_PER_REQUEST=0.0015              # Cost per Bright Data request
SAFETY_MARGIN=0.10                   # Reserve 10% of budget
ALERT_THRESHOLD=0.80                 # Alert at 80% usage

# === Optional Timing Settings ===
UPDATE_INTERVAL_SECONDS=900          # 15 minutes
CACHE_TTL_SECONDS=900                # 15 minutes
MAX_RETRIES=3
RETRY_DELAY_SECONDS=5

# === Optional Logging Settings ===
LOG_LEVEL=INFO                       # DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_DIR=logs
LOG_FILE=bloomberg_crawler.log
MAX_LOG_SIZE=10485760                # 10MB
BACKUP_COUNT=5

# === Optional API Settings ===
FINNHUB_API_KEY=your_key             # Fallback API
ALPHA_VANTAGE_API_KEY=your_key       # Alternative API
REQUEST_TIMEOUT=30

# === Optional Bright Data Settings ===
BRIGHT_DATA_ZONE=bloomberg
BRIGHT_DATA_HOST=brd.superproxy.io
BRIGHT_DATA_PORT=33335
```

## Support

For issues or questions:
1. Check logs in `logs/` directory
2. Review error messages in console output
3. Test with `--log-level DEBUG` for detailed diagnostics
4. Verify `.env` configuration
