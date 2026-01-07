"""
Bloomberg Global Index Crawler

Fetches 59 global index data from Bloomberg via Bright Data API.
Each index is saved to its own individual file for easy identification.

Usage:
    python scripts/crawl_indices.py                    # Crawl all 59 indices
    python scripts/crawl_indices.py --test             # Test with first 2 indices
    python scripts/crawl_indices.py --index 1         # Crawl specific index by ID
    python scripts/crawl_indices.py --range 1 10      # Crawl range of indices
"""

import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

import aiohttp
from dotenv import load_dotenv

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.parsers.bloomberg_parser import BloombergParser

# Load environment
load_dotenv()


class IndexCrawler:
    """Crawler for Bloomberg global indices via Bright Data API"""

    def __init__(self):
        self.token = os.getenv("BRIGHT_DATA_TOKEN")
        self.zone = os.getenv("BRIGHT_DATA_ZONE", "bloomberg")
        self.endpoint = "https://api.brightdata.com/request"
        self.parser = BloombergParser()
        self.cost_per_request = 0.0015

        # Output directories
        self.output_dir = Path(__file__).parent.parent / "data" / "indices"
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Load index URLs
        self.urls_file = Path(__file__).parent.parent / "data" / "index_urls.json"
        with open(self.urls_file, "r", encoding="utf-8") as f:
            self.index_data = json.load(f)

    async def fetch_html(self, session: aiohttp.ClientSession, url: str) -> Optional[str]:
        """Fetch HTML from Bloomberg via Bright Data API"""
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }
        payload = {
            "zone": self.zone,
            "url": url,
            "format": "raw",
        }

        try:
            async with session.post(
                self.endpoint,
                headers=headers,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=60)
            ) as response:
                if response.status == 200:
                    return await response.text()
                else:
                    error = await response.text()
                    print(f"    ❌ API Error: {response.status} - {error[:100]}")
                    return None
        except Exception as e:
            print(f"    ❌ Request Error: {e}")
            return None

    def save_individual_result(self, index_info: dict, quote_data: dict, html_size: int):
        """Save individual index result to its own file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        date_str = datetime.now().strftime("%Y%m%d")

        # Create directory for this index
        index_code = index_info["code"].replace("@", "_")
        index_dir = self.output_dir / index_code
        index_dir.mkdir(parents=True, exist_ok=True)

        # Prepare result data
        result = {
            "crawl_info": {
                "id": index_info["id"],
                "code": index_info["code"],
                "country": index_info["country"],
                "bloomberg_symbol": index_info["bloomberg_symbol"],
                "url": index_info["url"],
                "crawled_at": datetime.now().isoformat(),
                "html_size_bytes": html_size,
                "cost_usd": self.cost_per_request,
            },
            "quote_data": quote_data,
        }

        # Save JSON file
        json_path = index_dir / f"{date_str}.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False, default=str)

        # Save CSV file (append mode)
        csv_path = index_dir / f"{date_str}.csv"
        csv_exists = csv_path.exists()

        with open(csv_path, "a", encoding="utf-8") as f:
            if not csv_exists:
                # Write header
                headers = [
                    "timestamp", "code", "country", "bloomberg_symbol",
                    "name", "price", "change", "change_percent",
                    "day_high", "day_low", "open_price", "prev_close",
                    "year_high", "year_low", "source"
                ]
                f.write(",".join(headers) + "\n")

            # Write data row
            row = [
                datetime.now().isoformat(),
                index_info["code"],
                index_info["country"],
                index_info["bloomberg_symbol"],
                quote_data.get("name", ""),
                str(quote_data.get("price", "")),
                str(quote_data.get("change", "")),
                str(quote_data.get("change_percent", "")),
                str(quote_data.get("day_high", "")),
                str(quote_data.get("day_low", "")),
                str(quote_data.get("open_price", "")),
                str(quote_data.get("prev_close", "")),
                str(quote_data.get("year_high", "")),
                str(quote_data.get("year_low", "")),
                quote_data.get("source", ""),
            ]
            f.write(",".join(row) + "\n")

        return json_path

    async def crawl_single_index(
        self,
        session: aiohttp.ClientSession,
        index_info: dict
    ) -> dict:
        """Crawl a single index and save results"""
        idx_id = index_info["id"]
        code = index_info["code"]
        country = index_info["country"]
        url = index_info["url"]

        print(f"\n[{idx_id:02d}/59] {code} ({country})")
        print(f"    URL: {url}")

        # Fetch HTML
        html = await self.fetch_html(session, url)

        if not html:
            return {
                "id": idx_id,
                "code": code,
                "status": "failed",
                "error": "Failed to fetch HTML",
            }

        print(f"    ✓ Fetched {len(html):,} bytes")

        # Parse quote data
        quote = self.parser.parse_quote_page(html, url)

        if not quote:
            return {
                "id": idx_id,
                "code": code,
                "status": "failed",
                "error": "Failed to parse HTML",
            }

        # Convert to dict
        quote_data = {
            "ticker": quote.ticker,
            "name": quote.name,
            "price": quote.price,
            "change": quote.change,
            "change_percent": quote.change_percent,
            "volume": quote.volume,
            "market_cap": quote.market_cap,
            "day_high": quote.day_high,
            "day_low": quote.day_low,
            "year_high": quote.year_high,
            "year_low": quote.year_low,
            "open_price": quote.open_price,
            "prev_close": quote.prev_close,
            "currency": quote.currency,
            "source": quote.source,
            "timestamp": quote.timestamp.isoformat(),
        }

        # Save individual result
        saved_path = self.save_individual_result(index_info, quote_data, len(html))

        print(f"    ✓ Parsed: {quote.name}")
        print(f"    ✓ Price: {quote.price} ({quote.change_percent:+.2f}%)" if quote.change_percent else f"    ✓ Price: {quote.price}")
        print(f"    ✓ Saved: {saved_path.name}")

        return {
            "id": idx_id,
            "code": code,
            "status": "success",
            "quote": quote_data,
            "saved_to": str(saved_path),
        }

    async def crawl_indices(
        self,
        index_ids: Optional[list] = None,
        delay_seconds: float = 1.0
    ):
        """Crawl multiple indices with rate limiting"""
        indices = self.index_data["indices"]

        # Filter by IDs if specified
        if index_ids:
            indices = [idx for idx in indices if idx["id"] in index_ids]

        total = len(indices)
        print("=" * 60)
        print(f"Bloomberg Global Index Crawler")
        print("=" * 60)
        print(f"Total indices to crawl: {total}")
        print(f"Estimated cost: ${total * self.cost_per_request:.4f}")
        print(f"Output directory: {self.output_dir}")
        print("=" * 60)

        results = {
            "success": [],
            "failed": [],
        }
        total_cost = 0.0

        async with aiohttp.ClientSession() as session:
            for i, index_info in enumerate(indices):
                result = await self.crawl_single_index(session, index_info)

                if result["status"] == "success":
                    results["success"].append(result)
                    total_cost += self.cost_per_request
                else:
                    results["failed"].append(result)

                # Rate limiting (except for last request)
                if i < len(indices) - 1:
                    await asyncio.sleep(delay_seconds)

        # Print summary
        print("\n" + "=" * 60)
        print("CRAWL SUMMARY")
        print("=" * 60)
        print(f"✓ Success: {len(results['success'])}/{total}")
        print(f"✗ Failed:  {len(results['failed'])}/{total}")
        print(f"$ Cost:    ${total_cost:.4f}")
        print("=" * 60)

        if results["failed"]:
            print("\nFailed indices:")
            for fail in results["failed"]:
                print(f"  - [{fail['id']:02d}] {fail['code']}: {fail.get('error', 'Unknown error')}")

        # Save summary
        summary_path = self.output_dir / f"crawl_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(summary_path, "w", encoding="utf-8") as f:
            json.dump({
                "crawled_at": datetime.now().isoformat(),
                "total_indices": total,
                "success_count": len(results["success"]),
                "failed_count": len(results["failed"]),
                "total_cost_usd": total_cost,
                "failed_indices": results["failed"],
            }, f, indent=2)

        print(f"\nSummary saved to: {summary_path}")

        return results


async def main():
    import argparse

    parser = argparse.ArgumentParser(description="Bloomberg Global Index Crawler")
    parser.add_argument("--test", action="store_true", help="Test mode: crawl first 2 indices only")
    parser.add_argument("--index", type=int, help="Crawl specific index by ID (1-59)")
    parser.add_argument("--range", type=int, nargs=2, metavar=("START", "END"), help="Crawl range of indices")
    parser.add_argument("--delay", type=float, default=1.0, help="Delay between requests in seconds (default: 1.0)")

    args = parser.parse_args()

    crawler = IndexCrawler()

    # Determine which indices to crawl
    index_ids = None

    if args.test:
        index_ids = [1, 2]
        print("🧪 TEST MODE: Crawling first 2 indices only")
    elif args.index:
        index_ids = [args.index]
        print(f"📌 Single index mode: Crawling index #{args.index}")
    elif args.range:
        start, end = args.range
        index_ids = list(range(start, end + 1))
        print(f"📊 Range mode: Crawling indices #{start} to #{end}")

    await crawler.crawl_indices(index_ids=index_ids, delay_seconds=args.delay)


if __name__ == "__main__":
    asyncio.run(main())
