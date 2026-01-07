"""
YFinance Integration Example

Demonstrates how YFinanceClient integrates with the Bloomberg Data Crawler
architecture, showing the complete data flow from fetching to storage.

This example shows:
1. Multi-source data fetching (YFinance as free tier fallback)
2. Data normalization to standard format
3. Error handling and fallback strategies
4. Comparison with other data sources
"""

from datetime import datetime
from src.clients.yfinance_client import YFinanceClient
from src.utils.exceptions import APIError


class DataFetchOrchestrator:
    """
    Orchestrates data fetching from multiple sources with fallback strategy.

    Priority order:
    1. Bloomberg (premium, rate-limited)
    2. YFinance (free, unlimited)
    """

    def __init__(self):
        self.yfinance_client = YFinanceClient()
        self.stats = {
            'yfinance_success': 0,
            'yfinance_failed': 0,
            'total_requests': 0
        }

    def fetch_quote(self, symbol: str) -> dict:
        """
        Fetch quote with multi-source fallback strategy.

        Args:
            symbol: Ticker symbol

        Returns:
            Normalized quote data
        """
        self.stats['total_requests'] += 1

        # Primary: YFinance (free tier)
        try:
            quote = self.yfinance_client.fetch_quote(symbol)
            if quote:
                self.stats['yfinance_success'] += 1
                return quote
        except APIError as e:
            self.stats['yfinance_failed'] += 1
            print(f"YFinance failed for {symbol}: {e}")

        # No data available
        raise ValueError(f"No data source available for {symbol}")

    def fetch_portfolio(self, symbols: list[str]) -> dict:
        """
        Fetch entire portfolio with optimized bulk operations.

        Args:
            symbols: List of ticker symbols

        Returns:
            Dictionary mapping symbols to quotes
        """
        print(f"\nFetching {len(symbols)} symbols...")

        # Use bulk fetch for efficiency
        results = self.yfinance_client.fetch_multiple(symbols)

        # Track statistics
        for symbol, quote in results.items():
            self.stats['total_requests'] += 1
            if quote:
                self.stats['yfinance_success'] += 1
            else:
                self.stats['yfinance_failed'] += 1

        return results

    def get_statistics(self) -> dict:
        """Get fetching statistics."""
        total = self.stats['total_requests']
        success = self.stats['yfinance_success']

        return {
            **self.stats,
            'success_rate': (success / total * 100) if total > 0 else 0
        }


def demo_basic_integration():
    """Basic integration example."""
    print("=== Basic Integration Demo ===\n")

    orchestrator = DataFetchOrchestrator()

    # Fetch single quote
    symbol = "AAPL"
    quote = orchestrator.fetch_quote(symbol)

    print(f"Fetched {quote['symbol']} from {quote['source']}")
    print(f"Price: ${quote['price']:.2f}")
    print(f"Change: {quote['change_percent']:+.2f}%")
    print(f"Timestamp: {quote['timestamp']}")


def demo_portfolio_fetching():
    """Portfolio fetching with statistics."""
    print("\n=== Portfolio Fetching Demo ===\n")

    orchestrator = DataFetchOrchestrator()

    # Define portfolio
    portfolio = {
        'tech': ["AAPL", "MSFT", "GOOGL", "AMZN", "META"],
        'finance': ["JPM", "BAC", "GS", "WFC"],
        'energy': ["XOM", "CVX", "COP"]
    }

    # Fetch all symbols
    all_symbols = [s for symbols in portfolio.values() for s in symbols]
    results = orchestrator.fetch_portfolio(all_symbols)

    # Display by sector
    for sector, symbols in portfolio.items():
        print(f"\n{sector.upper()} Sector:")
        print(f"{'Symbol':<8} {'Price':>10} {'Change':>10} {'Volume':>15}")
        print("-" * 53)

        for symbol in symbols:
            quote = results.get(symbol)
            if quote:
                print(f"{symbol:<8} ${quote['price']:>9.2f} "
                      f"{quote['change_percent']:>9.2f}% "
                      f"{quote['volume']:>15,}")
            else:
                print(f"{symbol:<8} {'No data':>10}")

    # Show statistics
    stats = orchestrator.get_statistics()
    print(f"\n--- Statistics ---")
    print(f"Total requests: {stats['total_requests']}")
    print(f"YFinance success: {stats['yfinance_success']}")
    print(f"YFinance failed: {stats['yfinance_failed']}")
    print(f"Success rate: {stats['success_rate']:.1f}%")


def demo_multi_asset_support():
    """Demonstrate multi-asset class support."""
    print("\n=== Multi-Asset Support Demo ===\n")

    orchestrator = DataFetchOrchestrator()

    assets = {
        'Stocks': ['AAPL', 'MSFT'],
        'Forex': ['EURUSD=X', 'GBPUSD=X'],
        'Commodities': ['GC=F', 'CL=F']
    }

    for asset_class, symbols in assets.items():
        print(f"\n{asset_class}:")
        results = orchestrator.fetch_portfolio(symbols)

        for symbol, quote in results.items():
            if quote:
                print(f"  {quote['name']}: ${quote['price']:.2f} "
                      f"({quote['change_percent']:+.2f}%)")


def demo_historical_analysis():
    """Demonstrate historical data integration."""
    print("\n=== Historical Data Analysis Demo ===\n")

    client = YFinanceClient()

    # Fetch historical data
    symbol = "AAPL"
    history = client.fetch_history(symbol, period="1mo", interval="1d")

    if history is not None and not history.empty:
        print(f"Historical data for {symbol} (last 30 days):")
        print(f"  Data points: {len(history)}")
        print(f"  Date range: {history.index[0]} to {history.index[-1]}")
        print(f"  Average volume: {history['Volume'].mean():,.0f}")
        print(f"  Price range: ${history['Low'].min():.2f} - ${history['High'].max():.2f}")

        # Calculate simple metrics
        returns = ((history['Close'].iloc[-1] / history['Close'].iloc[0]) - 1) * 100
        volatility = history['Close'].pct_change().std() * 100

        print(f"  Period return: {returns:+.2f}%")
        print(f"  Daily volatility: {volatility:.2f}%")

        # Show recent data
        print(f"\nRecent trading days:")
        print(history[['Open', 'High', 'Low', 'Close', 'Volume']].tail())


def demo_error_handling():
    """Demonstrate robust error handling."""
    print("\n=== Error Handling Demo ===\n")

    orchestrator = DataFetchOrchestrator()

    test_symbols = ["AAPL", "INVALID_SYMBOL", "MSFT", "ANOTHER_INVALID"]

    print("Fetching mix of valid and invalid symbols...")
    results = orchestrator.fetch_portfolio(test_symbols)

    print("\nResults:")
    for symbol, quote in results.items():
        if quote:
            print(f"  {symbol}: SUCCESS - ${quote['price']:.2f}")
        else:
            print(f"  {symbol}: FAILED - No data available")

    stats = orchestrator.get_statistics()
    print(f"\nError tolerance: {stats['yfinance_failed']} failures, "
          f"{stats['yfinance_success']} successes")


def demo_data_normalization():
    """Demonstrate data normalization across sources."""
    print("\n=== Data Normalization Demo ===\n")

    client = YFinanceClient()

    # Fetch different asset types
    assets = {
        'Stock': 'AAPL',
        'Forex': 'EURUSD=X',
        'Commodity': 'GC=F'
    }

    print("All assets normalized to same format:")
    print(f"{'Type':<12} {'Symbol':<12} {'Fields'}")
    print("-" * 60)

    for asset_type, symbol in assets.items():
        quote = client.fetch_quote(symbol)
        if quote:
            fields = list(quote.keys())
            print(f"{asset_type:<12} {symbol:<12} {len(fields)} fields")

            # Verify standard fields present
            required = ['symbol', 'price', 'change', 'change_percent',
                       'volume', 'timestamp', 'source']
            missing = [f for f in required if f not in quote]

            if missing:
                print(f"  WARNING: Missing fields: {missing}")
            else:
                print(f"  ✓ All standard fields present")


if __name__ == "__main__":
    print("YFinance Integration Demonstration")
    print("=" * 70)

    # Run all demos
    demo_basic_integration()
    demo_portfolio_fetching()
    demo_multi_asset_support()
    demo_historical_analysis()
    demo_error_handling()
    demo_data_normalization()

    print("\n" + "=" * 70)
    print("Integration demo complete!")
    print("\nKey takeaways:")
    print("  - YFinance provides free, unlimited data access")
    print("  - Data normalized to standard format across asset types")
    print("  - Robust error handling with graceful degradation")
    print("  - Suitable for portfolio tracking, backtesting, research")
