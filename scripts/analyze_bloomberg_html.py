"""
Bloomberg HTML Structure Analyzer

Analyzes the saved Bloomberg HTML to find the correct data extraction patterns.
"""

import json
import re
from pathlib import Path

from bs4 import BeautifulSoup


def analyze():
    """Analyze the saved Bloomberg HTML"""
    html_path = Path(__file__).parent.parent / "debug_output" / "bloomberg_raw.html"

    if not html_path.exists():
        print(f"ERROR: HTML file not found at {html_path}")
        return

    print("=" * 80)
    print("Bloomberg HTML Structure Analysis")
    print("=" * 80)

    with open(html_path, "r", encoding="utf-8") as f:
        html = f.read()

    soup = BeautifulSoup(html, "lxml")

    # 1. JSON-LD Scripts
    print("\n[1] JSON-LD Scripts (application/ld+json)")
    print("-" * 60)
    json_ld_scripts = soup.find_all("script", type="application/ld+json")
    print(f"Found: {len(json_ld_scripts)} script(s)")

    for i, script in enumerate(json_ld_scripts):
        try:
            data = json.loads(script.string)
            print(f"\n  Script #{i+1}:")
            print(f"    @type: {data.get('@type', 'N/A')}")
            print(f"    All keys: {list(data.keys())}")

            # Print full content (formatted)
            json_str = json.dumps(data, indent=2)
            print(f"\n    Full content:")
            for line in json_str.split("\n")[:30]:
                print(f"      {line}")
            if len(json_str.split("\n")) > 30:
                print("      ... (truncated)")

            # Save to file
            output_dir = Path(__file__).parent.parent / "debug_output"
            with open(output_dir / f"json_ld_{i}.json", "w") as f:
                json.dump(data, f, indent=2)

        except json.JSONDecodeError as e:
            print(f"  Script #{i+1}: JSON parse error - {e}")

    # 2. __NEXT_DATA__
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

            print(f"  Top-level keys: {list(data.keys())}")
            print(f"  props keys: {list(props.keys())}")
            print(f"  pageProps keys: {list(page_props.keys())[:20]}...")

            # Look for quote/price data in pageProps
            print("\n  Searching for quote data in pageProps...")
            search_for_prices(page_props, "pageProps", 0, 5)

            # Save full __NEXT_DATA__
            output_dir = Path(__file__).parent.parent / "debug_output"
            with open(output_dir / "next_data.json", "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            print(f"\n  Saved full __NEXT_DATA__ to: {output_dir / 'next_data.json'}")

        except json.JSONDecodeError as e:
            print(f"JSON parse error: {e}")
    else:
        print("No __NEXT_DATA__ found")

    # 3. CSS class search for price elements
    print("\n[3] HTML Elements with Price-Related Classes")
    print("-" * 60)

    price_patterns = [
        r"price",
        r"last",
        r"quote",
        r"value",
        r"change",
    ]

    for pattern in price_patterns:
        regex = re.compile(pattern, re.I)
        elements = soup.find_all(class_=regex)
        if elements:
            print(f"\n  class~='{pattern}': {len(elements)} element(s)")
            for el in elements[:5]:
                text = el.get_text(strip=True)[:80]
                classes = " ".join(el.get("class", [])[:3])
                print(f"    <{el.name} class='{classes}'> → '{text}'")

    # 4. Data attributes
    print("\n[4] Data Attributes")
    print("-" * 60)

    for attr_pattern in ["data-price", "data-value", "data-component"]:
        elements = soup.find_all(attrs={attr_pattern: True})
        if elements:
            print(f"\n  {attr_pattern}: {len(elements)} element(s)")
            for el in elements[:5]:
                print(f"    {el.name}: {el.get(attr_pattern)}")

    # 5. Look for specific Bloomberg class patterns
    print("\n[5] Bloomberg-Specific Elements")
    print("-" * 60)

    # Title/Name
    title = soup.find("title")
    if title:
        print(f"  Page Title: {title.get_text()}")

    # Look for h1
    h1 = soup.find("h1")
    if h1:
        print(f"  H1: {h1.get_text(strip=True)[:100]}")

    # Meta tags
    meta_desc = soup.find("meta", attrs={"name": "description"})
    if meta_desc:
        print(f"  Meta Description: {meta_desc.get('content', 'N/A')[:100]}")

    # 6. Script tags with inline data
    print("\n[6] Other Script Tags with Data")
    print("-" * 60)

    for script in soup.find_all("script"):
        if script.string and len(script.string) > 100:
            content = script.string[:500]
            # Look for price-like patterns
            if any(term in content.lower() for term in ["price", "lastprice", "change"]):
                script_type = script.get("type", "text/javascript")
                script_id = script.get("id", "N/A")
                print(f"\n  Script (type={script_type}, id={script_id}):")
                print(f"    Preview: {content[:300]}...")


def search_for_prices(obj, path: str, depth: int, max_depth: int):
    """Recursively search for price-related fields"""
    if depth > max_depth:
        return

    if isinstance(obj, dict):
        for key, value in obj.items():
            key_lower = key.lower()
            # Price-related keys
            if any(term in key_lower for term in ["price", "last", "change", "volume", "high", "low", "open", "close", "bid", "ask"]):
                if isinstance(value, (int, float)):
                    print(f"    {path}.{key} = {value}")
                elif isinstance(value, str) and value and len(value) < 50:
                    print(f"    {path}.{key} = '{value}'")
                elif isinstance(value, dict):
                    print(f"    {path}.{key} = dict({list(value.keys())[:5]}...)")

            # Recurse into nested structures
            if isinstance(value, (dict, list)) and depth < max_depth:
                search_for_prices(value, f"{path}.{key}", depth + 1, max_depth)

    elif isinstance(obj, list) and len(obj) > 0:
        search_for_prices(obj[0], f"{path}[0]", depth + 1, max_depth)


if __name__ == "__main__":
    analyze()
