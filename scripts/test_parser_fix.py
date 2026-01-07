"""
Test Bloomberg Parser Fix

Tests the updated parser against saved Bloomberg HTML.
"""

import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.parsers.bloomberg_parser import BloombergParser


def test_parser():
    """Test parser with saved HTML"""
    html_path = Path(__file__).parent.parent / "debug_output" / "bloomberg_raw.html"

    if not html_path.exists():
        print(f"ERROR: HTML file not found at {html_path}")
        return

    print("=" * 60)
    print("Bloomberg Parser Test")
    print("=" * 60)

    with open(html_path, "r", encoding="utf-8") as f:
        html = f.read()

    print(f"Loaded HTML: {len(html):,} bytes")

    # Parse
    parser = BloombergParser()
    url = "https://www.bloomberg.com/quote/AAPL:US"

    quote = parser.parse_quote_page(html, url)

    if quote:
        print("\n✅ Parsing SUCCESS!")
        print("-" * 60)
        print(f"  Ticker:        {quote.ticker}")
        print(f"  Name:          {quote.name}")
        print(f"  Price:         ${quote.price}")
        print(f"  Change:        {quote.change:+.2f}" if quote.change else "  Change:        N/A")
        print(f"  Change %:      {quote.change_percent:+.2f}%" if quote.change_percent else "  Change %:      N/A")
        print(f"  Volume:        {quote.volume:,.0f}" if quote.volume else "  Volume:        N/A")
        print(f"  Day High:      ${quote.day_high}" if quote.day_high else "  Day High:      N/A")
        print(f"  Day Low:       ${quote.day_low}" if quote.day_low else "  Day Low:       N/A")
        print(f"  Open:          ${quote.open_price}" if quote.open_price else "  Open:          N/A")
        print(f"  Prev Close:    ${quote.prev_close}" if quote.prev_close else "  Prev Close:    N/A")
        print(f"  52W High:      ${quote.year_high}" if quote.year_high else "  52W High:      N/A")
        print(f"  52W Low:       ${quote.year_low}" if quote.year_low else "  52W Low:       N/A")
        print(f"  Source:        {quote.source}")
        print(f"  Timestamp:     {quote.timestamp}")
    else:
        print("\n❌ Parsing FAILED!")


if __name__ == "__main__":
    test_parser()
