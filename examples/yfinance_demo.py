"""
YFinance Client Demo

Demonstrates usage of the YFinanceClient for fetching financial data
from Yahoo Finance.

Run this script to see examples of:
- Fetching single quotes
- Fetching historical data
- Bulk symbol fetching
- Different asset types (stocks, forex, commodities)
"""

from src.clients.yfinance_client import YFinanceClient
from src.utils.exceptions import APIError


def demo_single_quote():
    """Demonstrate fetching a single quote."""
    print("\n=== Single Quote Demo ===")
    client = YFinanceClient()

    try:
        quote = client.fetch_quote("AAPL")
        if quote:
            print(f"\nApple Inc. (AAPL)")
            print(f"Price: ${quote['price']:.2f}")
            print(f"Change: ${quote['change']:.2f} ({quote['change_percent']:.2f}%)")
            print(f"Volume: {quote['volume']:,}")
            print(f"Market Cap: ${quote['market_cap']:,}")
            print(f"Day Range: ${quote['day_low']:.2f} - ${quote['day_high']:.2f}")
            print(f"52-Week Range: ${quote['year_low']:.2f} - ${quote['year_high']:.2f}")
            print(f"Timestamp: {quote['timestamp']}")
        else:
            print("No data available for AAPL")
    except APIError as e:
        print(f"Error fetching quote: {e}")


def demo_historical_data():
    """Demonstrate fetching historical data."""
    print("\n=== Historical Data Demo ===")
    client = YFinanceClient()

    try:
        # Fetch 1 month of daily data
        history = client.fetch_history("MSFT", period="1mo", interval="1d")
        if history is not None and not history.empty:
            print(f"\nMicrosoft (MSFT) - Last 5 Days")
            print(history[['Open', 'High', 'Low', 'Close', 'Volume']].tail())
            print(f"\nTotal data points: {len(history)}")
        else:
            print("No historical data available")
    except APIError as e:
        print(f"Error fetching history: {e}")


def demo_multiple_symbols():
    """Demonstrate fetching multiple symbols in bulk."""
    print("\n=== Multiple Symbols Demo ===")
    client = YFinanceClient()

    symbols = ["AAPL", "MSFT", "GOOGL", "AMZN", "META"]
    results = client.fetch_multiple(symbols)

    print("\nTech Stock Quotes:")
    print(f"{'Symbol':<8} {'Price':>10} {'Change':>10} {'Change %':>10}")
    print("-" * 48)

    for symbol, quote in results.items():
        if quote:
            print(f"{symbol:<8} ${quote['price']:>9.2f} "
                  f"${quote['change']:>9.2f} "
                  f"{quote['change_percent']:>9.2f}%")
        else:
            print(f"{symbol:<8} {'No data':>10}")


def demo_forex():
    """Demonstrate fetching forex pairs."""
    print("\n=== Forex Demo ===")
    client = YFinanceClient()

    forex_pairs = ["EURUSD=X", "GBPUSD=X", "JPYUSD=X"]
    results = client.fetch_multiple(forex_pairs)

    print("\nForex Rates:")
    print(f"{'Pair':<12} {'Rate':>10} {'Change':>10} {'Change %':>10}")
    print("-" * 52)

    for pair, quote in results.items():
        if quote:
            # Clean up pair name for display
            display_name = quote['name'] if quote['name'] != pair else pair
            print(f"{display_name:<12} {quote['price']:>10.4f} "
                  f"{quote['change']:>10.4f} "
                  f"{quote['change_percent']:>9.2f}%")
        else:
            print(f"{pair:<12} {'No data':>10}")


def demo_commodities():
    """Demonstrate fetching commodity futures."""
    print("\n=== Commodities Demo ===")
    client = YFinanceClient()

    commodities = {
        "GC=F": "Gold",
        "CL=F": "Crude Oil",
        "SI=F": "Silver",
        "NG=F": "Natural Gas"
    }

    results = client.fetch_multiple(list(commodities.keys()))

    print("\nCommodity Futures:")
    print(f"{'Commodity':<15} {'Price':>10} {'Change':>10} {'Change %':>10}")
    print("-" * 55)

    for symbol, name in commodities.items():
        quote = results.get(symbol)
        if quote:
            print(f"{name:<15} ${quote['price']:>9.2f} "
                  f"${quote['change']:>9.2f} "
                  f"{quote['change_percent']:>9.2f}%")
        else:
            print(f"{name:<15} {'No data':>10}")


def demo_context_manager():
    """Demonstrate using client as context manager for session reuse."""
    print("\n=== Context Manager Demo ===")

    symbols = ["AAPL", "MSFT", "GOOGL"]

    print("\nUsing persistent session for better performance...")
    with YFinanceClient() as client:
        for symbol in symbols:
            try:
                quote = client.fetch_quote(symbol)
                if quote:
                    print(f"{symbol}: ${quote['price']:.2f} "
                          f"({quote['change_percent']:+.2f}%)")
            except APIError as e:
                print(f"{symbol}: Error - {e}")


def demo_error_handling():
    """Demonstrate error handling."""
    print("\n=== Error Handling Demo ===")
    client = YFinanceClient()

    # Try invalid symbol
    print("\nAttempting to fetch invalid symbol...")
    try:
        quote = client.fetch_quote("INVALID_SYMBOL_12345")
        if quote is None:
            print("No data returned for invalid symbol (handled gracefully)")
        else:
            print(f"Unexpected data: {quote}")
    except APIError as e:
        print(f"APIError caught: {e}")


if __name__ == "__main__":
    print("YFinance Client Demonstration")
    print("=" * 60)

    # Run all demos
    demo_single_quote()
    demo_historical_data()
    demo_multiple_symbols()
    demo_forex()
    demo_commodities()
    demo_context_manager()
    demo_error_handling()

    print("\n" + "=" * 60)
    print("Demo complete!")
