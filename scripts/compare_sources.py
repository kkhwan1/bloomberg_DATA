"""
Bloomberg vs YFinance Data Comparison

Fetches data from both sources and compares the results.
"""

import asyncio
import os
import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
import aiohttp
import yfinance as yf

from src.parsers.bloomberg_parser import BloombergParser

# Load environment
load_dotenv()


async def fetch_bloomberg_data(symbol: str):
    """Fetch data from Bloomberg via Bright Data"""
    token = os.getenv("BRIGHT_DATA_TOKEN")
    zone = os.getenv("BRIGHT_DATA_ZONE", "bloomberg")
    endpoint = "https://api.brightdata.com/request"

    # Convert symbol format (AAPL -> AAPL:US)
    bloomberg_symbol = f"{symbol}:US"
    url = f"https://www.bloomberg.com/quote/{bloomberg_symbol}"

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
    }

    payload = {
        "zone": zone,
        "url": url,
        "format": "raw",
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(
            endpoint,
            headers=headers,
            json=payload,
            timeout=aiohttp.ClientTimeout(total=60)
        ) as response:
            if response.status != 200:
                error = await response.text()
                raise Exception(f"Bloomberg fetch failed: {response.status} - {error[:200]}")

            html = await response.text()

            # Parse
            parser = BloombergParser()
            quote = parser.parse_quote_page(html, url)
            return quote


def fetch_yfinance_data(symbol: str):
    """Fetch data from YFinance"""
    ticker = yf.Ticker(symbol)
    info = ticker.info

    return {
        "symbol": symbol,
        "name": info.get("longName", info.get("shortName", "")),
        "price": info.get("currentPrice") or info.get("regularMarketPrice"),
        "change": info.get("regularMarketChange"),
        "change_percent": info.get("regularMarketChangePercent"),
        "volume": info.get("regularMarketVolume"),
        "day_high": info.get("dayHigh") or info.get("regularMarketDayHigh"),
        "day_low": info.get("dayLow") or info.get("regularMarketDayLow"),
        "open": info.get("open") or info.get("regularMarketOpen"),
        "prev_close": info.get("previousClose") or info.get("regularMarketPreviousClose"),
        "year_high": info.get("fiftyTwoWeekHigh"),
        "year_low": info.get("fiftyTwoWeekLow"),
        "market_cap": info.get("marketCap"),
        "pe_ratio": info.get("trailingPE"),
    }


def format_value(value, is_price=False, is_percent=False, is_volume=False):
    """Format a value for display"""
    if value is None:
        return "N/A"
    if is_price:
        return f"${value:,.2f}"
    if is_percent:
        return f"{value:+.2f}%"
    if is_volume:
        return f"{value:,.0f}"
    return str(value)


async def compare():
    """Compare Bloomberg and YFinance data"""
    symbol = "AAPL"

    print("=" * 80)
    print(f"Bloomberg vs YFinance Data Comparison: {symbol}")
    print("=" * 80)

    # Fetch from both sources
    print("\n[1] Fetching from YFinance...")
    try:
        yf_data = fetch_yfinance_data(symbol)
        print("    ✅ YFinance SUCCESS")
    except Exception as e:
        print(f"    ❌ YFinance FAILED: {e}")
        yf_data = None

    print("\n[2] Fetching from Bloomberg (Bright Data)...")
    try:
        bb_data = await fetch_bloomberg_data(symbol)
        print("    ✅ Bloomberg SUCCESS")
        print(f"    Cost: $0.0015")
    except Exception as e:
        print(f"    ❌ Bloomberg FAILED: {e}")
        bb_data = None

    # Compare results
    if yf_data and bb_data:
        print("\n" + "=" * 80)
        print("COMPARISON RESULTS")
        print("=" * 80)

        fields = [
            ("Name", "name", "name", False, False, False),
            ("Price", "price", "price", True, False, False),
            ("Change", "change", "change", True, False, False),
            ("Change %", "change_percent", "change_percent", False, True, False),
            ("Volume", "volume", "volume", False, False, True),
            ("Day High", "day_high", "day_high", True, False, False),
            ("Day Low", "day_low", "day_low", True, False, False),
            ("Open", "open", "open_price", True, False, False),
            ("Prev Close", "prev_close", "prev_close", True, False, False),
            ("52W High", "year_high", "year_high", True, False, False),
            ("52W Low", "year_low", "year_low", True, False, False),
        ]

        print(f"\n{'Field':<15} {'YFinance':<25} {'Bloomberg':<25} {'Match':<10}")
        print("-" * 80)

        for field_name, yf_key, bb_key, is_price, is_percent, is_volume in fields:
            yf_val = yf_data.get(yf_key)
            bb_val = getattr(bb_data, bb_key, None)

            yf_str = format_value(yf_val, is_price, is_percent, is_volume)
            bb_str = format_value(bb_val, is_price, is_percent, is_volume)

            # Check if values match (within tolerance for floats)
            match = "N/A"
            if yf_val is not None and bb_val is not None:
                if isinstance(yf_val, (int, float)) and isinstance(bb_val, (int, float)):
                    diff = abs(yf_val - bb_val)
                    if diff < 0.01:
                        match = "✅ Match"
                    elif diff < 1.0:
                        match = f"~{diff:.2f}"
                    else:
                        match = f"Δ{diff:,.2f}"
                elif yf_val == bb_val:
                    match = "✅ Match"
                else:
                    match = "≠"

            print(f"{field_name:<15} {yf_str:<25} {bb_str:<25} {match:<10}")

        print("\n" + "-" * 80)
        print(f"Bloomberg Source: {bb_data.source}")
        print(f"Bloomberg Timestamp: {bb_data.timestamp}")

    elif yf_data:
        print("\n[Only YFinance data available]")
        print(f"  Price: ${yf_data['price']}")
        print(f"  Volume: {yf_data['volume']:,}")

    elif bb_data:
        print("\n[Only Bloomberg data available]")
        print(f"  Price: ${bb_data.price}")
        print(f"  Volume: {bb_data.volume:,}")

    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"  YFinance:  {'Available' if yf_data else 'Failed'} (FREE)")
    print(f"  Bloomberg: {'Available' if bb_data else 'Failed'} ($0.0015/request)")

    if yf_data and bb_data:
        print("\n  💡 Bloomberg provides more accurate/real-time data")
        print("     but costs money. YFinance is free but may have delays.")


async def main():
    await compare()


if __name__ == "__main__":
    asyncio.run(main())
