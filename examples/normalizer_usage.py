"""
Example usage of the normalizer module.

Demonstrates transforming data from multiple sources into standardized MarketQuote objects.
"""

from datetime import datetime

from src.normalizer import (
    AssetClass,
    DataSource,
    DataTransformer,
    MarketQuote,
    QuoteCollection,
)


def example_bloomberg_transformation():
    """Example: Transform Bloomberg data."""
    print("=== Bloomberg Data Transformation ===\n")

    bloomberg_data = {
        "symbol": "AAPL:US",
        "security_name": "Apple Inc.",
        "last_price": 175.50,
        "timestamp": "2024-01-15T16:00:00Z",
        "change": 2.50,
        "pct_change": 1.45,
        "volume": 52000000,
        "market_cap": 2750000000000,
        "day_high": 176.00,
        "day_low": 172.50,
        "currency": "USD",
        "exchange": "NASDAQ",
    }

    quote = DataTransformer.from_bloomberg(bloomberg_data, AssetClass.STOCKS)

    print(f"Symbol: {quote.symbol}")
    print(f"Name: {quote.name}")
    print(f"Price: ${quote.price:.2f}")
    print(f"Change: {quote.change:+.2f} ({quote.change_percent:+.2f}%)")
    print(f"Volume: {quote.volume:,.0f}")
    print(f"Market Cap: ${quote.market_cap / 1e9:.2f}B")
    print(f"Source: {quote.source.value}")
    print(f"Valid: {quote.is_valid()}")
    print(f"\nDisplay: {quote}\n")


def example_yfinance_transformation():
    """Example: Transform yfinance data."""
    print("=== yfinance Data Transformation ===\n")

    yfinance_data = {
        "symbol": "MSFT",
        "longName": "Microsoft Corporation",
        "currentPrice": 380.25,
        "regularMarketTime": 1705338000,
        "regularMarketChange": 5.75,
        "regularMarketChangePercent": 0.0154,  # Decimal format
        "regularMarketVolume": 28500000,
        "marketCap": 2825000000000,
        "trailingPE": 35.2,
        "dividendYield": 0.0078,  # Decimal format
        "sector": "Technology",
        "industry": "Software—Infrastructure",
    }

    quote = DataTransformer.from_yfinance(yfinance_data, AssetClass.STOCKS)

    print(f"Symbol: {quote.symbol}")
    print(f"Name: {quote.name}")
    print(f"Price: ${quote.price:.2f}")
    print(f"Change: {quote.change:+.2f} ({quote.change_percent:+.2f}%)")
    print(f"P/E Ratio: {quote.pe_ratio:.2f}")
    print(f"Dividend Yield: {quote.dividend_yield:.2f}%")
    print(f"Sector: {quote.sector}")
    print(f"Source: {quote.source.value}")
    print(f"\nDisplay: {quote}\n")


def example_finnhub_transformation():
    """Example: Transform Finnhub data."""
    print("=== Finnhub Data Transformation ===\n")

    finnhub_data = {
        "c": 3250.75,  # current price
        "d": 45.25,  # change
        "dp": 1.41,  # percent change
        "h": 3275.00,  # high
        "l": 3220.50,  # low
        "o": 3230.00,  # open
        "pc": 3205.50,  # previous close
        "t": 1705338000,  # timestamp
    }

    quote = DataTransformer.from_finnhub(
        finnhub_data,
        AssetClass.STOCKS,
        symbol="GOOGL",
        name="Alphabet Inc. Class A",
    )

    print(f"Symbol: {quote.symbol}")
    print(f"Name: {quote.name}")
    print(f"Price: ${quote.price:.2f}")
    print(f"Day Range: ${quote.day_low:.2f} - ${quote.day_high:.2f}")
    print(f"Open: ${quote.open_price:.2f}")
    print(f"Previous Close: ${quote.previous_close:.2f}")
    print(f"Source: {quote.source.value}")
    print(f"\nDisplay: {quote}\n")


def example_forex_data():
    """Example: Forex data with bid/ask."""
    print("=== Forex Data (EUR/USD) ===\n")

    quote = MarketQuote(
        symbol="EUR/USD",
        name="Euro US Dollar",
        price=1.1050,
        timestamp=datetime.utcnow(),
        source=DataSource.BLOOMBERG,
        asset_class=AssetClass.FOREX,
        change=0.0025,
        change_percent=0.23,
        bid=1.1048,
        ask=1.1052,
        currency="USD",
    )

    print(f"Pair: {quote.symbol}")
    print(f"Rate: {quote.price:.4f}")
    print(f"Bid: {quote.bid:.4f}")
    print(f"Ask: {quote.ask:.4f}")
    print(f"Spread: {quote.spread:.4f}")
    print(f"Change: {quote.change:+.4f} ({quote.change_percent:+.2f}%)")
    print()


def example_quote_collection():
    """Example: Managing quote collections."""
    print("=== Quote Collection ===\n")

    collection = QuoteCollection(source=DataSource.BLOOMBERG)

    # Add multiple quotes
    quotes_data = [
        ("AAPL:US", "Apple Inc.", 175.50, 2.50),
        ("MSFT:US", "Microsoft Corp.", 380.25, 5.75),
        ("GOOGL:US", "Alphabet Inc.", 3250.75, 45.25),
        ("AMZN:US", "Amazon.com Inc.", 151.25, 3.15),
        ("TSLA:US", "Tesla Inc.", 238.50, -5.25),
    ]

    for symbol, name, price, change in quotes_data:
        quote = MarketQuote(
            symbol=symbol,
            name=name,
            price=price,
            timestamp=datetime.utcnow(),
            source=DataSource.BLOOMBERG,
            asset_class=AssetClass.STOCKS,
            change=change,
            previous_close=price - change,
        )
        collection.add_quote(quote)

    print(f"Total quotes: {collection.total_count}")
    print(f"Valid quotes: {collection.valid_count}")
    print("\nQuotes:")

    for quote in collection.quotes:
        print(f"  {quote}")

    # Retrieve specific quote
    print("\nLookup TSLA:")
    tsla = collection.get_by_symbol("TSLA:US")
    if tsla:
        print(f"  {tsla.get_display_name()}: ${tsla.price:.2f}")

    # Export to DataFrame
    print("\nDataFrame preview:")
    df = collection.to_dataframe()
    print(df[["symbol", "name", "price", "change", "change_percent"]].to_string())
    print()


def example_serialization():
    """Example: Serialization formats."""
    print("=== Serialization Examples ===\n")

    quote = MarketQuote(
        symbol="AAPL:US",
        name="Apple Inc.",
        price=175.50,
        timestamp=datetime(2024, 1, 15, 16, 0, 0),
        source=DataSource.BLOOMBERG,
        asset_class=AssetClass.STOCKS,
        change=2.50,
        change_percent=1.45,
        volume=52000000,
    )

    # JSON serialization
    print("JSON format:")
    print(quote.to_json(indent=2))
    print()

    # CSV row format
    print("CSV row:")
    csv_row = quote.to_csv_row()
    print(f"  Symbol: {csv_row['symbol']}")
    print(f"  Price: {csv_row['price']}")
    print(f"  Change: {csv_row['change']}")
    print()

    # Dictionary format
    print("Dictionary format:")
    quote_dict = quote.to_dict()
    print(f"  Keys: {list(quote_dict.keys())[:10]}...")
    print()


def example_validation():
    """Example: Data validation."""
    print("=== Data Validation ===\n")

    # Valid quote
    valid_quote = MarketQuote(
        symbol="AAPL:US",
        name="Apple Inc.",
        price=175.50,
        timestamp=datetime.utcnow(),
        source=DataSource.BLOOMBERG,
        asset_class=AssetClass.STOCKS,
        confidence_score=0.95,
    )

    print(f"Valid quote: {valid_quote.is_valid()}")
    print(f"Fresh data: {valid_quote.is_fresh(max_age_seconds=900)}")
    print(f"Data age: {valid_quote.calculate_data_age()} seconds")
    print()

    # Try invalid data (will raise validation error)
    print("Attempting to create invalid quote (negative price)...")
    try:
        invalid_quote = MarketQuote(
            symbol="TEST",
            name="Test",
            price=-10.0,  # Invalid
            timestamp=datetime.utcnow(),
            source=DataSource.CACHE,
            asset_class=AssetClass.STOCKS,
        )
    except ValueError as e:
        print(f"  Validation error: {e}")
    print()


def example_number_normalization():
    """Example: Number normalization."""
    print("=== Number Normalization ===\n")

    test_values = [
        "175.50",
        "$1,750.50",
        "52K",
        "2.75M",
        "2.75B",
        "1.45%",
        "€175.50",
        "N/A",
        None,
        175.50,
    ]

    for value in test_values:
        normalized = DataTransformer.normalize_number(value)
        print(f"  {str(value):20s} -> {normalized}")
    print()


def main():
    """Run all examples."""
    print("=" * 60)
    print("Bloomberg Data Normalizer - Usage Examples")
    print("=" * 60)
    print()

    example_bloomberg_transformation()
    example_yfinance_transformation()
    example_finnhub_transformation()
    example_forex_data()
    example_quote_collection()
    example_serialization()
    example_validation()
    example_number_normalization()

    print("=" * 60)
    print("Examples completed successfully!")
    print("=" * 60)


if __name__ == "__main__":
    main()
