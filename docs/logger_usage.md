# Logger Utility Documentation

Advanced logging system for Bloomberg Data Crawler with daily rotation, colorized console output, and specialized logger instances.

## Features

- **Dual Output**: File + Console logging with different formatting
- **Daily Rotation**: Log files named `YYYYMMDD_logger_name.log`
- **Size-based Rotation**: 10MB max file size, 5 backup files
- **Colorized Console**: Green/Yellow/Red color coding (via colorlog)
- **Logger Caching**: Efficient reuse of logger instances
- **Specialized Loggers**: Pre-configured for cost, API, and parsing operations

## Quick Start

```python
from src.utils.logger import get_logger

# Get logger for your module
logger = get_logger(__name__)

# Log at different levels
logger.debug("Detailed debugging information")
logger.info("General informational messages")
logger.warning("Warning messages")
logger.error("Error messages")
logger.critical("Critical issues")
```

## Log Levels

| Level | When to Use | Console Color |
|-------|-------------|---------------|
| DEBUG | Detailed debugging info, variable values | White |
| INFO | General progress updates | Green |
| WARNING | Potential issues, deprecations | Yellow |
| ERROR | Error conditions | Red |
| CRITICAL | System failure conditions | Bold Red |

## Log Formats

### File Format (Detailed)
```
%(asctime)s - %(name)s - %(levelname)s - %(message)s
```

Example:
```
2026-01-07 05:31:50 - bloomberg.cost - INFO - Request cost: $0.0015
```

### Console Format (Simplified + Colorized)
```
%(levelname)-8s %(name)s - %(message)s
```

Example:
```
INFO     bloomberg.cost - Request cost: $0.0015
```

## Specialized Loggers

### Cost Logger
Track API costs and budget consumption:

```python
from src.utils.logger import get_cost_logger

cost_logger = get_cost_logger()

cost_logger.info(f"Request cost: ${cost:.4f}")
cost_logger.warning(f"Budget usage: {usage_percent:.1f}%")
```

### API Logger
Track HTTP requests and responses:

```python
from src.utils.logger import get_api_logger

api_logger = get_api_logger()

api_logger.debug(f"GET {url}")
api_logger.info(f"Response: {status_code} - {response_time:.3f}s")
api_logger.error(f"API error: {status_code} from {url}")
```

### Parser Logger
Track data extraction and parsing:

```python
from src.utils.logger import get_parser_logger

parser_logger = get_parser_logger()

parser_logger.info(f"Extracted price: ${price:.2f}")
parser_logger.warning(f"Missing field: {field_name}")
```

## Configuration

Logger configuration is managed through `src/config.py`:

```python
class LoggingConfig:
    LOG_LEVEL: str = "INFO"           # DEBUG, INFO, WARNING, ERROR, CRITICAL
    LOG_DIR: Path = Path("logs")      # Log file directory
    MAX_LOG_SIZE: int = 10 * 1024 * 1024  # 10MB
    BACKUP_COUNT: int = 5             # Number of backup files
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    DATE_FORMAT: str = "%Y-%m-%d %H:%M:%S"
```

Override via environment variables:
```bash
export LOG_LEVEL=DEBUG
export LOG_DIR=/var/log/bloomberg
export MAX_LOG_SIZE=20971520  # 20MB
export BACKUP_COUNT=10
```

## Usage Patterns

### Module-Specific Logging

Each module should create its own logger:

```python
# In src/clients/bright_data_client.py
from src.utils.logger import get_logger

logger = get_logger(__name__)  # Creates 'src.clients.bright_data_client' logger

logger.info("Proxy connection established")
```

This creates hierarchical loggers:
- `bloomberg.clients.bright_data`
- `bloomberg.storage.cache`
- `bloomberg.parsers.bloomberg_parser`

### Exception Logging with Traceback

```python
try:
    result = risky_operation()
except Exception as e:
    logger.error(f"Operation failed: {e}", exc_info=True)
```

The `exc_info=True` parameter includes full traceback in file logs.

### Structured Logging

```python
context = {
    "symbol": "AAPL:US",
    "source": "bloomberg",
    "cache_hit": False,
    "duration_ms": 456,
}

logger.info(
    "Data fetch completed",
    extra=context
)

# Or format manually for better readability
logger.debug(
    f"Request details:\n"
    f"  Symbol: {context['symbol']}\n"
    f"  Source: {context['source']}\n"
    f"  Cached: {context['cache_hit']}\n"
    f"  Duration: {context['duration_ms']}ms"
)
```

### Performance Logging

```python
import time

start_time = time.time()

# ... operation ...

elapsed = time.time() - start_time

logger.info(f"Operation completed in {elapsed*1000:.2f}ms")

if elapsed > 1.0:
    logger.warning(f"Slow operation detected: {elapsed:.2f}s")
```

## File Organization

Log files are organized by date and logger name:

```
logs/
├── 20260107_bloomberg_api.log
├── 20260107_bloomberg_cost.log
├── 20260107_bloomberg_parser.log
├── 20260107_bloomberg_orchestrator.log
├── 20260107_bloomberg_storage_cache.log
└── ...
```

When rotation occurs:
```
logs/
├── 20260107_bloomberg_api.log          # Current
├── 20260107_bloomberg_api.log.1        # Backup 1
├── 20260107_bloomberg_api.log.2        # Backup 2
├── 20260107_bloomberg_api.log.3        # Backup 3
├── 20260107_bloomberg_api.log.4        # Backup 4
└── 20260107_bloomberg_api.log.5        # Backup 5 (oldest)
```

## Best Practices

### 1. Use Appropriate Log Levels

```python
# Good
logger.debug(f"Variable x = {x}")  # Development debugging
logger.info(f"Processing {symbol}")  # Normal operations
logger.warning(f"Cache miss for {symbol}")  # Potential issues
logger.error(f"Failed to parse {url}")  # Errors
logger.critical(f"Database connection lost")  # System failures

# Bad
logger.info(f"Variable x = {x}")  # Too verbose
logger.error(f"Cache miss")  # Not an error
```

### 2. Include Context

```python
# Good
logger.error(f"Failed to fetch {symbol}: {error}")
logger.warning(f"Slow response from {url}: {response_time:.2f}s")

# Bad
logger.error("Fetch failed")
logger.warning("Slow response")
```

### 3. Use Lazy Formatting

```python
# Good - Formatting only happens if log level is enabled
logger.debug("Processing %s with %d items", symbol, count)

# Less efficient - Formatting always happens
logger.debug(f"Processing {symbol} with {count} items")
```

### 4. Don't Log Sensitive Data

```python
# Bad
logger.info(f"API token: {token}")
logger.debug(f"Password: {password}")

# Good
logger.info(f"API token: {token[:8]}...")
logger.debug("Authentication successful")
```

### 5. Use Specialized Loggers for Domain Logic

```python
# Good
cost_logger.info(f"Total cost: ${total:.2f}")
api_logger.debug(f"GET {url}")
parser_logger.warning(f"Missing field: {field}")

# Less organized
logger.info(f"Total cost: ${total:.2f}")
logger.debug(f"GET {url}")
logger.warning(f"Missing field: {field}")
```

## Testing

The logger system includes comprehensive tests:

```bash
# Run all logger tests
pytest tests/test_logger.py -v

# Run with coverage
pytest tests/test_logger.py --cov=src.utils.logger --cov-report=term-missing
```

Test coverage includes:
- Logger configuration
- File and console handlers
- Log rotation
- Specialized loggers
- Exception handling
- Concurrent access

## Troubleshooting

### No Color Output

If console output is not colorized:
```bash
pip install colorlog
```

Fallback to standard formatting if colorlog is unavailable.

### Permission Errors

Ensure log directory is writable:
```bash
mkdir -p logs
chmod 755 logs
```

### Duplicate Log Messages

If you see duplicate messages, check for multiple handler registration:
```python
# The logger system prevents this automatically
# But if you manually modify logger handlers, you may see duplicates
```

### Log Files Not Rotating

Check file size limits in configuration:
```python
# Current setting
LoggingConfig.MAX_LOG_SIZE = 10 * 1024 * 1024  # 10MB

# For testing rotation, use smaller size
LoggingConfig.MAX_LOG_SIZE = 1024  # 1KB
```

## API Reference

### setup_logger(name, level=None)
Create and configure a logger instance.

**Parameters:**
- `name` (str): Logger name (typically `__name__`)
- `level` (int, optional): Custom log level (defaults to config setting)

**Returns:** `logging.Logger`

### get_logger(name)
Retrieve cached logger or create new one. **Recommended method.**

**Parameters:**
- `name` (str): Logger name

**Returns:** `logging.Logger`

### get_cost_logger()
Get specialized logger for cost tracking.

**Returns:** `logging.Logger` with name `bloomberg.cost`

### get_api_logger()
Get specialized logger for API operations.

**Returns:** `logging.Logger` with name `bloomberg.api`

### get_parser_logger()
Get specialized logger for parsing operations.

**Returns:** `logging.Logger` with name `bloomberg.parser`

### LoggerConfig
Configuration manager for logger settings.

**Methods:**
- `get_daily_log_filename(logger_name)`: Generate YYYYMMDD-prefixed filename
- `get_log_file_path(logger_name)`: Get full path to log file

## Integration Examples

### With Cache Manager

```python
from src.utils.logger import get_logger

logger = get_logger(__name__)

class CacheManager:
    def get(self, key):
        logger.debug(f"Cache lookup: {key}")
        if key in self.cache:
            logger.info(f"Cache hit: {key}")
            return self.cache[key]
        logger.warning(f"Cache miss: {key}")
        return None
```

### With API Client

```python
from src.utils.logger import get_api_logger

api_logger = get_api_logger()

class APIClient:
    def fetch(self, url):
        api_logger.debug(f"GET {url}")
        start = time.time()

        response = requests.get(url)
        elapsed = time.time() - start

        api_logger.info(f"Response: {response.status_code} - {elapsed:.3f}s")
        return response
```

### With Cost Tracker

```python
from src.utils.logger import get_cost_logger

cost_logger = get_cost_logger()

class CostTracker:
    def record_request(self, cost):
        self.total_cost += cost
        cost_logger.info(
            f"Request: ${cost:.4f}, Total: ${self.total_cost:.2f}"
        )

        if self.total_cost / self.budget > 0.8:
            cost_logger.warning(
                f"Budget alert: {(self.total_cost/self.budget)*100:.1f}%"
            )
```

## See Also

- [Configuration Guide](../src/config.py) - Logger configuration options
- [Testing Guide](../tests/test_logger.py) - Logger test suite
- [Examples](../examples/logger_usage_example.py) - Usage examples
