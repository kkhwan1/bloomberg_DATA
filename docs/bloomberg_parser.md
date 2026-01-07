# Bloomberg HTML Parser Documentation

## Overview

The Bloomberg Parser provides robust HTML parsing capabilities for extracting financial quote data from Bloomberg pages using multiple extraction strategies with intelligent fallback.

## Architecture

### Three-Tier Extraction Strategy

The parser implements a priority-based extraction system that attempts three different parsing methods in order:

```
1. JSON-LD (Highest Priority)
   ↓ (if fails)
2. __NEXT_DATA__ (Medium Priority)
   ↓ (if fails)
3. HTML DOM Parsing (Fallback)
```

### Key Components

```python
BloombergParser
├── parse_quote_page()      # Single quote extraction
├── parse_markets_page()    # Multiple quotes extraction
├── _extract_json_ld()      # JSON-LD strategy
├── _extract_next_data()    # __NEXT_DATA__ strategy
├── _parse_html_quote()     # HTML fallback strategy
├── _parse_number()         # Number parsing utility
└── _parse_range()          # Range parsing utility
```

## Data Structure

### BloombergQuote

```python
@dataclass
class BloombergQuote:
    ticker: str                    # Stock ticker symbol
    name: str                      # Company/security name
    price: Optional[float]         # Current price
    change: Optional[float]        # Price change
    change_percent: Optional[float] # % change
    volume: Optional[float]        # Trading volume
    market_cap: Optional[float]    # Market capitalization
    day_high: Optional[float]      # Day high price
    day_low: Optional[float]       # Day low price
    year_high: Optional[float]     # 52-week high
    year_low: Optional[float]      # 52-week low
    open_price: Optional[float]    # Opening price
    prev_close: Optional[float]    # Previous close
    currency: Optional[str]        # Currency code
    source: str                    # Extraction source
    timestamp: datetime            # Parse timestamp
```

## Extraction Strategies

### 1. JSON-LD Strategy

**Priority**: Highest
**Reliability**: Best
**Data Completeness**: Medium

Extracts structured data from `<script type="application/ld+json">` tags.

#### Supported Schemas

- `Corporation`
- `Organization`
- `FinancialProduct`

#### Example HTML

```html
<script type="application/ld+json">
{
    "@type": "Corporation",
    "name": "Apple Inc.",
    "tickerSymbol": "AAPL",
    "price": 175.50,
    "priceCurrency": "USD",
    "volume": 55300000
}
</script>
```

#### Field Mappings

| Standard Field | JSON-LD Fields |
|----------------|----------------|
| price | price, priceValue, currentPrice |
| name | name, legalName, alternateName |
| ticker | tickerSymbol, ticker, symbol |
| currency | priceCurrency, currency |
| volume | volume, tradingVolume |
| market_cap | marketCap, marketCapitalization |

### 2. __NEXT_DATA__ Strategy

**Priority**: Medium
**Reliability**: Good
**Data Completeness**: High

Extracts data from Next.js pages via `<script id="__NEXT_DATA__">` tags.

#### Example HTML

```html
<script id="__NEXT_DATA__" type="application/json">
{
    "props": {
        "pageProps": {
            "quote": {
                "ticker": "AAPL",
                "lastPrice": 175.50,
                "high": 177.00,
                "low": 173.50,
                "volume": 55300000
            }
        }
    }
}
</script>
```

#### Field Mappings

| Standard Field | Next.js Fields |
|----------------|----------------|
| price | lastPrice, price, last |
| name | name, companyName, securityName |
| day_high | high, dayHigh, todayHigh |
| day_low | low, dayLow, todayLow |
| year_high | yearHigh, 52WeekHigh, high52Week |
| year_low | yearLow, 52WeekLow, low52Week |
| open_price | open, openPrice, todayOpen |
| prev_close | previousClose, prevClose, close |

### 3. HTML DOM Parsing

**Priority**: Lowest (Fallback)
**Reliability**: Variable
**Data Completeness**: Depends on page structure

Parses HTML structure directly using class names and table data.

#### Detection Patterns

```python
# Name extraction
class_regex = r"name|title|security"

# Price extraction
class_regex = r"price|last|value"

# Change extraction
class_regex = r"change|diff"
```

#### Table Field Mappings

| Standard Field | Table Labels |
|----------------|--------------|
| volume | Volume, Total Volume, Trading Volume |
| market_cap | Market Cap, Market Capitalization, Mkt Cap |
| open | Open, Opening Price, Today's Open |
| prev_close | Previous Close, Prev Close, Yesterday's Close |
| day_range | Day Range, Today's Range, Intraday Range |
| 52_week_range | 52 Week Range, 52-Week Range, Year Range |

## Number Parsing Utilities

### _parse_number()

Handles various numeric formats:

#### Supported Formats

| Format | Example | Parsed Value |
|--------|---------|--------------|
| Basic | "123.45" | 123.45 |
| Commas | "1,234.56" | 1234.56 |
| Currency | "$1,234.56" | 1234.56 |
| Percentage | "5.2%" | 5.2 |
| K suffix | "1.5K" | 1500 |
| M suffix | "2.3M" | 2300000 |
| B suffix | "1.2B" | 1200000000 |
| T suffix | "5.5T" | 5500000000000 |
| Negative | "-$2.3B" | -2300000000 |

#### Supported Currencies

- $ (Dollar)
- € (Euro)
- £ (Pound)
- ¥ (Yen)
- ₹ (Rupee)

#### Implementation

```python
parser = BloombergParser()

# Basic parsing
parser._parse_number("$1,234.56")  # → 1234.56

# Suffix parsing
parser._parse_number("2.5M")       # → 2500000.0

# Percentage parsing
parser._parse_number("5.2%")       # → 5.2

# Negative values
parser._parse_number("-$2.3B")     # → -2300000000.0
```

### _parse_range()

Parses price ranges from strings.

#### Format

```
"LOW - HIGH"
```

#### Examples

```python
parser._parse_range("100 - 105")       # → (105.0, 100.0)
parser._parse_range("$50 - $60")       # → (60.0, 50.0)
parser._parse_range("1.2K - 1.5K")     # → (1500.0, 1200.0)
```

## API Reference

### parse_quote_page()

Parse individual Bloomberg quote page.

**Signature**:
```python
def parse_quote_page(
    html: str,
    url: str
) -> Optional[BloombergQuote]
```

**Parameters**:
- `html` (str): Raw HTML content
- `url` (str): Source URL for ticker extraction

**Returns**:
- `BloombergQuote` object or `None` if parsing fails

**Example**:
```python
parser = BloombergParser()
html = fetch_page("https://bloomberg.com/quote/AAPL:US")
quote = parser.parse_quote_page(html, url)

if quote:
    print(f"{quote.ticker}: ${quote.price}")
```

### parse_markets_page()

Parse Bloomberg markets page with multiple quotes.

**Signature**:
```python
def parse_markets_page(
    html: str,
    url: str
) -> List[BloombergQuote]
```

**Parameters**:
- `html` (str): Raw HTML content
- `url` (str): Source URL

**Returns**:
- List of `BloombergQuote` objects (empty list if parsing fails)

**Example**:
```python
parser = BloombergParser()
html = fetch_page("https://bloomberg.com/markets")
quotes = parser.parse_markets_page(html, url)

for quote in quotes:
    print(f"{quote.ticker}: ${quote.price}")
```

## Usage Examples

### Basic Quote Parsing

```python
from src.parsers.bloomberg_parser import BloombergParser

parser = BloombergParser()

# Parse single quote
html = """
<html>
<script type="application/ld+json">
{
    "@type": "Corporation",
    "tickerSymbol": "AAPL",
    "name": "Apple Inc.",
    "price": 175.50
}
</script>
</html>
"""

quote = parser.parse_quote_page(html, "https://bloomberg.com/quote/AAPL:US")
print(f"{quote.name}: ${quote.price}")
```

### Markets Page Parsing

```python
# Parse multiple quotes from table
html = """
<table>
    <tr><th>Symbol</th><th>Price</th><th>Change</th></tr>
    <tr><td>AAPL</td><td>$175.50</td><td>+2.25</td></tr>
    <tr><td>MSFT</td><td>$380.00</td><td>-3.50</td></tr>
</table>
"""

quotes = parser.parse_markets_page(html, "https://bloomberg.com/markets")
for quote in quotes:
    print(f"{quote.ticker}: ${quote.price} ({quote.change:+.2f})")
```

### Number Parsing

```python
parser = BloombergParser()

# Parse various formats
values = ["$1,234.56", "2.5M", "5.5%", "€15.2K"]
for val in values:
    result = parser._parse_number(val)
    print(f"{val} → {result}")
```

## Error Handling

The parser is designed to be resilient:

1. **Graceful Degradation**: If one strategy fails, it automatically falls back to the next
2. **None Returns**: Invalid or unparseable data returns `None` instead of raising exceptions
3. **Optional Fields**: Most fields are optional to accommodate incomplete data
4. **Type Safety**: All parsing functions include type checking

### Handling Parse Failures

```python
quote = parser.parse_quote_page(html, url)

if quote is None:
    # Parsing completely failed
    logger.warning(f"Failed to parse quote from {url}")
    return

# Check individual fields
if quote.price is None:
    logger.warning(f"Price unavailable for {quote.ticker}")

if quote.volume is None:
    logger.debug(f"Volume data not found for {quote.ticker}")
```

## Performance Considerations

### Strategy Priority Rationale

1. **JSON-LD First**: Fastest parsing, structured data, no DOM traversal
2. **__NEXT_DATA__ Second**: Single JSON parse, predictable structure
3. **HTML Last**: Requires DOM traversal, regex matching, less reliable

### Optimization Tips

```python
# Reuse parser instance
parser = BloombergParser()

# Batch processing
quotes = []
for html, url in page_data:
    quote = parser.parse_quote_page(html, url)
    if quote:
        quotes.append(quote)
```

## Testing

Comprehensive test suite covers:

- Number parsing (28 test cases)
- Range parsing (6 test cases)
- JSON-LD extraction (3 test cases)
- __NEXT_DATA__ extraction (2 test cases)
- HTML parsing (3 test cases)
- Card parsing (2 test cases)
- URL parsing (6 test cases)
- Integration tests (3 test cases)
- Field mapping (4 test cases)

Run tests:

```bash
pytest tests/test_bloomberg_parser.py -v
```

## Future Enhancements

Potential improvements:

1. **WebSocket Support**: Real-time quote updates
2. **Multi-currency**: Enhanced currency conversion
3. **Historical Data**: Parse historical price tables
4. **Charts**: Extract chart data points
5. **News Integration**: Parse related news articles
6. **Analyst Ratings**: Extract analyst recommendations
7. **Financial Metrics**: PE ratio, EPS, dividend yield
8. **Options Data**: Parse options chain information

## Troubleshooting

### Common Issues

**Issue**: `quote.source == "html"` but expected structured data

**Solution**: Bloomberg may have changed their page structure. Check for:
- JSON-LD script tag presence
- __NEXT_DATA__ script tag presence
- Correct parser backend (use `lxml`)

**Issue**: Number parsing returns `None`

**Solution**: Check for unsupported formats:
- Non-ASCII characters
- Unusual number formats
- Missing values (N/A, --, etc.)

**Issue**: Missing fields in quote

**Solution**: Bloomberg pages vary by security type:
- Some fields only available for stocks
- Forex quotes have different structure
- Bonds have unique fields

## License

Part of Bloomberg Data Crawler project.
