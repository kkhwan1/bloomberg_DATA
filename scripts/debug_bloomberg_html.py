"""
Bloomberg HTML Structure Debug Script

Fetches Bloomberg page via Bright Data and analyzes the HTML structure
to understand why parsing returns N/A values.
"""

import asyncio
import json
import os
import re
import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
from bs4 import BeautifulSoup

# Load environment
load_dotenv()


async def fetch_bloomberg_html():
    """Fetch Bloomberg HTML via Bright Data"""
    import aiohttp

    token = os.getenv("BRIGHT_DATA_TOKEN")
    zone = os.getenv("BRIGHT_DATA_ZONE", "bloomberg")
    host = os.getenv("BRIGHT_DATA_HOST", "brd.superproxy.io")
    port = int(os.getenv("BRIGHT_DATA_PORT", "33335"))

    proxy_url = f"http://brd-customer-hl_4d5603bb-zone-{zone}:{token}@{host}:{port}"

    url = "https://www.bloomberg.com/quote/AAPL:US"

    print(f"[*] Fetching: {url}")
    print(f"[*] Using Bright Data zone: {zone}")

    async with aiohttp.ClientSession() as session:
        async with session.get(
            url,
            proxy=proxy_url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            },
            timeout=aiohttp.ClientTimeout(total=60)
        ) as response:
            html = await response.text()
            print(f"[*] Response: {response.status}, {len(html):,} bytes")
            return html


def analyze_html_structure(html: str):
    """Analyze the HTML structure for quote data"""
    soup = BeautifulSoup(html, "lxml")

    print("\n" + "="*80)
    print("BLOOMBERG HTML ANALYSIS")
    print("="*80)

    # 1. Check JSON-LD scripts
    print("\n[1] JSON-LD Scripts (application/ld+json)")
    print("-" * 60)
    json_ld_scripts = soup.find_all("script", type="application/ld+json")
    print(f"Found: {len(json_ld_scripts)} JSON-LD script(s)")

    for i, script in enumerate(json_ld_scripts):
        try:
            data = json.loads(script.string)
            print(f"\n  Script #{i+1} Structure:")
            if isinstance(data, dict):
                print(f"    @type: {data.get('@type', 'N/A')}")
                print(f"    Keys: {list(data.keys())[:10]}...")

                # Check for @graph
                if "@graph" in data:
                    print(f"    @graph items: {len(data['@graph'])}")
                    for j, item in enumerate(data["@graph"][:3]):
                        print(f"      Item {j}: @type={item.get('@type')}, keys={list(item.keys())[:5]}")

                # Look for price-related keys
                price_keys = [k for k in data.keys() if 'price' in k.lower()]
                if price_keys:
                    print(f"    Price-related keys: {price_keys}")
                    for pk in price_keys:
                        print(f"      {pk}: {data[pk]}")

            print(f"\n    Full JSON-LD content (truncated):")
            json_str = json.dumps(data, indent=2)
            print(json_str[:2000] + ("..." if len(json_str) > 2000 else ""))

        except json.JSONDecodeError as e:
            print(f"  Script #{i+1}: JSON parse error - {e}")

    # 2. Check __NEXT_DATA__
    print("\n[2] __NEXT_DATA__ Script")
    print("-" * 60)
    next_data_script = soup.find("script", id="__NEXT_DATA__")

    if next_data_script and next_data_script.string:
        try:
            data = json.loads(next_data_script.string)
            print("Found __NEXT_DATA__!")

            # Navigate structure
            props = data.get("props", {})
            page_props = props.get("pageProps", {})

            print(f"  props keys: {list(props.keys())}")
            print(f"  pageProps keys: {list(page_props.keys())[:15]}...")

            # Look for quote data
            for key in ["quote", "security", "data", "initialState"]:
                if key in page_props:
                    print(f"\n  Found '{key}' in pageProps:")
                    quote_data = page_props[key]
                    if isinstance(quote_data, dict):
                        print(f"    Keys: {list(quote_data.keys())[:15]}")
                        # Look for price
                        for pk in ["price", "lastPrice", "last", "priceValue"]:
                            if pk in quote_data:
                                print(f"    {pk}: {quote_data[pk]}")

            # Deep search for price-like values
            print("\n  Deep search for price fields:")
            find_price_fields(page_props, "pageProps", depth=0, max_depth=4)

        except json.JSONDecodeError as e:
            print(f"JSON parse error: {e}")
    else:
        print("No __NEXT_DATA__ found")

    # 3. Check HTML elements with price classes
    print("\n[3] HTML Elements with Price/Quote Classes")
    print("-" * 60)

    # Price elements
    price_patterns = [
        re.compile(r"price", re.I),
        re.compile(r"last", re.I),
        re.compile(r"value", re.I),
        re.compile(r"quote", re.I),
    ]

    for pattern in price_patterns:
        elements = soup.find_all(class_=pattern)
        if elements:
            print(f"\n  class~={pattern.pattern}: {len(elements)} elements")
            for el in elements[:5]:
                text = el.get_text(strip=True)[:100]
                classes = el.get("class", [])
                print(f"    <{el.name} class={classes[:3]}>: {text}")

    # Data attributes
    print("\n[4] Elements with data-* attributes")
    print("-" * 60)

    for attr in ["data-price", "data-value", "data-last", "data-change"]:
        elements = soup.find_all(attrs={attr: True})
        if elements:
            print(f"  {attr}: {len(elements)} elements")
            for el in elements[:3]:
                print(f"    {el.name}: {el.get(attr)}")

    # 5. Look for specific Bloomberg patterns
    print("\n[5] Bloomberg-specific patterns")
    print("-" * 60)

    # Security name
    name_elem = soup.find(["h1", "h2"], class_=re.compile(r"name|title|security", re.I))
    if name_elem:
        print(f"  Security Name: {name_elem.get_text(strip=True)[:50]}")

    # Look for specific Bloomberg class patterns
    bloomberg_classes = ["quote-header", "price-section", "security-summary"]
    for cls in bloomberg_classes:
        elem = soup.find(class_=re.compile(cls, re.I))
        if elem:
            print(f"  Found class '{cls}':")
            print(f"    Content: {elem.get_text(strip=True)[:200]}")

    # 6. Save raw HTML for manual inspection
    print("\n[6] Saving HTML for manual inspection...")
    print("-" * 60)
    output_path = Path(__file__).parent.parent / "debug_output"
    output_path.mkdir(exist_ok=True)

    # Save full HTML
    html_path = output_path / "bloomberg_raw.html"
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"  Saved raw HTML to: {html_path}")

    # Save JSON-LD
    for i, script in enumerate(json_ld_scripts):
        try:
            data = json.loads(script.string)
            json_path = output_path / f"json_ld_{i}.json"
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            print(f"  Saved JSON-LD #{i} to: {json_path}")
        except:
            pass

    # Save __NEXT_DATA__
    if next_data_script and next_data_script.string:
        try:
            data = json.loads(next_data_script.string)
            json_path = output_path / "next_data.json"
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            print(f"  Saved __NEXT_DATA__ to: {json_path}")
        except:
            pass


def find_price_fields(obj, path: str, depth: int, max_depth: int):
    """Recursively search for price-related fields"""
    if depth > max_depth:
        return

    if isinstance(obj, dict):
        for key, value in obj.items():
            key_lower = key.lower()
            if any(term in key_lower for term in ["price", "last", "change", "volume", "high", "low", "open", "close"]):
                if isinstance(value, (int, float, str)) and value:
                    print(f"    {path}.{key}: {value}")

            if isinstance(value, (dict, list)) and depth < max_depth:
                find_price_fields(value, f"{path}.{key}", depth + 1, max_depth)

    elif isinstance(obj, list) and len(obj) > 0 and depth < max_depth:
        find_price_fields(obj[0], f"{path}[0]", depth + 1, max_depth)


async def main():
    print("Bloomberg HTML Debug Script")
    print("=" * 80)

    # Check environment
    token = os.getenv("BRIGHT_DATA_TOKEN")
    if not token:
        print("ERROR: BRIGHT_DATA_TOKEN not set in .env")
        return

    print(f"Token: {token[:8]}...{token[-4:]}")

    # Fetch HTML
    try:
        html = await fetch_bloomberg_html()

        # Analyze
        analyze_html_structure(html)

        print("\n" + "="*80)
        print("Analysis complete! Check debug_output/ folder for saved files.")
        print("="*80)

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
