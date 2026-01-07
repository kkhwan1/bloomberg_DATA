"""
Direct Bright Data API Test

Tests the new Bright Data API directly using the bearer token approach.
"""

import asyncio
import os
import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
import aiohttp

# Load environment
load_dotenv()


async def test_api_direct():
    """Test Bright Data API directly"""
    token = os.getenv("BRIGHT_DATA_TOKEN")
    zone = os.getenv("BRIGHT_DATA_ZONE", "bloomberg")

    print("=" * 60)
    print("Bright Data API Direct Test")
    print("=" * 60)
    print(f"Token: {token[:8]}...{token[-4:]}")
    print(f"Zone: {zone}")

    # API endpoint
    endpoint = "https://api.brightdata.com/request"

    # Test URLs
    test_urls = [
        ("Test URL", "https://geo.brdtest.com/welcome.txt?product=unlocker&method=api"),
        ("Bloomberg AAPL", "https://www.bloomberg.com/quote/AAPL:US"),
    ]

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
    }

    async with aiohttp.ClientSession() as session:
        for name, url in test_urls:
            print(f"\n[*] Testing: {name}")
            print(f"    URL: {url}")

            payload = {
                "zone": zone,
                "url": url,
                "format": "raw",
            }

            try:
                async with session.post(
                    endpoint,
                    headers=headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=60)
                ) as response:
                    content = await response.text()

                    print(f"    Status: {response.status}")
                    print(f"    Content-Type: {response.headers.get('Content-Type', 'N/A')}")
                    print(f"    Size: {len(content):,} bytes")

                    if response.status == 200:
                        print(f"    SUCCESS!")
                        # For test URL, show full content
                        if "brdtest" in url:
                            print(f"    Content: {content[:200]}")
                        # For Bloomberg, save HTML
                        elif "bloomberg" in url:
                            # Save HTML for analysis
                            output_path = Path(__file__).parent.parent / "debug_output"
                            output_path.mkdir(exist_ok=True)
                            html_path = output_path / "bloomberg_raw.html"
                            with open(html_path, "w", encoding="utf-8") as f:
                                f.write(content)
                            print(f"    Saved HTML to: {html_path}")

                            # Quick preview
                            print(f"    Preview: {content[:500]}...")
                    else:
                        print(f"    FAILED!")
                        print(f"    Response: {content[:500]}")

            except Exception as e:
                print(f"    ERROR: {e}")


async def main():
    await test_api_direct()


if __name__ == "__main__":
    asyncio.run(main())
