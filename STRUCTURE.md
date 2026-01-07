# Bloomberg Data Crawler - Project Structure

## Directory Layout

```
bloomberg_data/
├── src/                          # Source code
│   ├── __init__.py              # Main package initialization
│   ├── clients/                 # HTTP clients and API wrappers
│   │   └── __init__.py         # BaseClient, BloombergClient, RateLimiter, RetryHandler
│   ├── parsers/                # HTML/JSON parsing logic
│   │   └── __init__.py         # BaseParser, StockParser, ForexParser, CommodityParser, BondParser
│   ├── orchestrator/           # Workflow coordination
│   │   └── __init__.py         # CrawlOrchestrator, TaskScheduler, PipelineManager
│   ├── normalizer/             # Data normalization
│   │   └── __init__.py         # DataNormalizer, SchemaValidator, DataTransformer
│   ├── storage/                # Database operations
│   │   └── __init__.py         # DatabaseManager, Repositories, CacheManager
│   └── utils/                  # Shared utilities
│       └── __init__.py         # Logger, ConfigLoader, DateTimeHelper
├── tests/                       # Test suite
│   ├── __init__.py             # Test package initialization
│   └── fixtures/               # Test data and mocks
│       └── __init__.py         # Fixture utilities
├── data/                        # Data storage
│   ├── stocks/                 # Stock data files
│   ├── forex/                  # Forex data files
│   ├── commodities/            # Commodity data files
│   └── bonds/                  # Bond data files
├── cache/                       # Cache storage
└── logs/                        # Application logs
```

## Module Overview

### src/clients
HTTP communication layer for Bloomberg API interactions.

**Components:**
- `BaseClient`: Abstract base class with common HTTP functionality
- `BloombergClient`: Main client implementation
- `RateLimiter`: Request throttling (respects Bloomberg rate limits)
- `RetryHandler`: Exponential backoff retry logic

### src/parsers
Asset-specific parsing logic for Bloomberg data formats.

**Components:**
- `BaseParser`: Common parsing interface
- `StockParser`: Equity/stock data parsing
- `ForexParser`: Foreign exchange data parsing
- `CommodityParser`: Commodity data parsing
- `BondParser`: Fixed income/bond data parsing
- `ParserFactory`: Parser instance creation

### src/orchestrator
Workflow coordination and scheduling system.

**Components:**
- `CrawlOrchestrator`: Main workflow coordinator
- `TaskScheduler`: Cron-like scheduling
- `PipelineManager`: Pipeline stage management
- `WorkflowConfig`: Configuration management
- `ErrorRecovery`: Error handling strategies

### src/normalizer
Data standardization and transformation layer.

**Components:**
- `DataNormalizer`: Main normalization interface
- `SchemaValidator`: JSON schema validation
- `DataTransformer`: Type conversions
- `UnitConverter`: Currency/unit conversions
- `DataCleaner`: Data quality checks

### src/storage
Data persistence and repository pattern.

**Components:**
- `DatabaseManager`: Connection management
- `Repository`: Generic data access
- Asset-specific repositories (Stock, Forex, Commodity, Bond)
- `CacheManager`: Caching layer

### src/utils
Shared utilities and helpers.

**Components:**
- `Logger`: Structured logging
- `ConfigLoader`: Configuration management
- `DateTimeHelper`: Date/time utilities
- `FileHelper`: File operations
- `ValidationHelper`: Common validations
- `MetricsCollector`: Performance metrics

## Data Flow

```
Bloomberg API
    ↓
[clients] HTTP Request → Response
    ↓
[parsers] Raw HTML/JSON → Structured Data
    ↓
[normalizer] Standardization → Normalized Data
    ↓
[storage] Persistence → Database/Files
    ↑
[orchestrator] Coordinates entire pipeline
```

## Next Steps

1. Implement base classes in each module
2. Add configuration management
3. Set up logging infrastructure
4. Implement client layer with rate limiting
5. Build parsers for each asset type
6. Create storage layer with PostgreSQL
7. Add comprehensive test coverage
