"""
Bloomberg Parser Usage Examples

Demonstrates the three extraction strategies and number parsing utilities.
"""

from src.parsers.bloomberg_parser import BloombergParser


def example_json_ld():
    """Example: Parsing quote page with JSON-LD structured data."""
    html = """
    <html>
    <head>
        <script type="application/ld+json">
        {
            "@type": "Corporation",
            "name": "Apple Inc.",
            "tickerSymbol": "AAPL",
            "price": 175.50,
            "priceChange": 2.25,
            "priceChangePercent": 1.30,
            "volume": 55300000,
            "marketCap": 2750000000000,
            "priceCurrency": "USD"
        }
        </script>
    </head>
    </html>
    """

    parser = BloombergParser()
    quote = parser.parse_quote_page(html, "https://bloomberg.com/quote/AAPL:US")

    if quote:
        print(f"Source: {quote.source}")
        print(f"Ticker: {quote.ticker}")
        print(f"Name: {quote.name}")
        print(f"Price: ${quote.price}")
        print(f"Change: {quote.change} ({quote.change_percent}%)")
        print(f"Volume: {quote.volume:,.0f}")
        print(f"Market Cap: ${quote.market_cap:,.0f}")
        print(f"Currency: {quote.currency}")


def example_next_data():
    """Example: Parsing quote page with __NEXT_DATA__."""
    html = """
    <html>
    <script id="__NEXT_DATA__" type="application/json">
    {
        "props": {
            "pageProps": {
                "quote": {
                    "ticker": "TSLA",
                    "name": "Tesla Inc.",
                    "lastPrice": 245.50,
                    "change": 5.75,
                    "changePercent": 2.40,
                    "volume": 120500000,
                    "marketCap": 780000000000,
                    "high": 248.00,
                    "low": 242.00,
                    "open": 243.00,
                    "previousClose": 239.75,
                    "yearHigh": 280.00,
                    "yearLow": 150.00,
                    "currency": "USD"
                }
            }
        }
    }
    </script>
    </html>
    """

    parser = BloombergParser()
    quote = parser.parse_quote_page(html, "https://bloomberg.com/quote/TSLA:US")

    if quote:
        print(f"\nSource: {quote.source}")
        print(f"Ticker: {quote.ticker}")
        print(f"Price: ${quote.price}")
        print(f"Day Range: ${quote.day_low} - ${quote.day_high}")
        print(f"52-Week Range: ${quote.year_low} - ${quote.year_high}")
        print(f"Open: ${quote.open_price}")
        print(f"Previous Close: ${quote.prev_close}")


def example_html_fallback():
    """Example: Parsing quote page with HTML tables (fallback)."""
    html = """
    <html>
    <body>
        <h1 class="security-name">NVIDIA Corporation</h1>
        <div class="price-value">$485.50</div>
        <span class="price-change">+12.35 (2.61%)</span>
        <table>
            <tr><td>Open</td><td>$475.00</td></tr>
            <tr><td>Previous Close</td><td>$473.15</td></tr>
            <tr><td>Volume</td><td>45.2M</td></tr>
            <tr><td>Market Cap</td><td>$1.2T</td></tr>
            <tr><td>Day Range</td><td>$472.00 - $487.50</td></tr>
            <tr><td>52 Week Range</td><td>$380.00 - $502.00</td></tr>
        </table>
    </body>
    </html>
    """

    parser = BloombergParser()
    quote = parser.parse_quote_page(html, "https://bloomberg.com/quote/NVDA:US")

    if quote:
        print(f"\nSource: {quote.source}")
        print(f"Ticker: {quote.ticker}")
        print(f"Name: {quote.name}")
        print(f"Price: ${quote.price}")
        print(f"Volume: {quote.volume:,.0f}")
        print(f"Market Cap: ${quote.market_cap:,.0f}")


def example_markets_page():
    """Example: Parsing markets page with multiple quotes."""
    html = """
    <html>
    <table>
        <thead>
            <tr>
                <th>Symbol</th>
                <th>Name</th>
                <th>Price</th>
                <th>Change</th>
                <th>% Change</th>
                <th>Volume</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td>AAPL</td>
                <td>Apple Inc.</td>
                <td>$175.50</td>
                <td>+2.25</td>
                <td>1.30%</td>
                <td>55.3M</td>
            </tr>
            <tr>
                <td>MSFT</td>
                <td>Microsoft</td>
                <td>$380.00</td>
                <td>-3.50</td>
                <td>-0.91%</td>
                <td>22.1M</td>
            </tr>
            <tr>
                <td>GOOGL</td>
                <td>Alphabet</td>
                <td>$140.50</td>
                <td>+1.75</td>
                <td>1.26%</td>
                <td>28.5M</td>
            </tr>
        </tbody>
    </table>
    </html>
    """

    parser = BloombergParser()
    quotes = parser.parse_markets_page(html, "https://bloomberg.com/markets")

    print(f"\nParsed {len(quotes)} quotes from markets page:")
    print(f"{'Ticker':<10} {'Price':<12} {'Change':<12} {'Volume':<15}")
    print("-" * 50)
    for quote in quotes:
        change_str = f"{quote.change:+.2f}" if quote.change else "N/A"
        volume_str = f"{quote.volume:,.0f}" if quote.volume else "N/A"
        print(f"{quote.ticker:<10} ${quote.price:<11.2f} {change_str:<12} {volume_str:<15}")


def example_number_parsing():
    """Example: Number parsing utilities."""
    parser = BloombergParser()

    test_values = [
        "$1,234.56",       # Currency with commas
        "2.5M",            # Million suffix
        "1.2B",            # Billion suffix
        "5.5%",            # Percentage
        "€15.2K",          # Euro with K suffix
        "-$2.3B",          # Negative billion
        "100 - 105",       # Range
    ]

    print("\nNumber Parsing Examples:")
    print(f"{'Input':<20} {'Parsed Value':<20}")
    print("-" * 40)

    for value in test_values[:-1]:  # Skip range for this demo
        parsed = parser._parse_number(value)
        if parsed:
            print(f"{value:<20} {parsed:,.2f}")

    # Parse range
    range_str = test_values[-1]
    high, low = parser._parse_range(range_str)
    print(f"{range_str:<20} High: {high}, Low: {low}")


if __name__ == "__main__":
    print("=" * 60)
    print("Bloomberg Parser Examples")
    print("=" * 60)

    example_json_ld()
    example_next_data()
    example_html_fallback()
    example_markets_page()
    example_number_parsing()
