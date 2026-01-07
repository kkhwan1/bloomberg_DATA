"""
Bloomberg HTML Parser

Multi-strategy HTML parsing for Bloomberg quote data with fallback support.

Parsing Strategies (Priority Order):
    1. JSON-LD: <script type="application/ld+json">
    2. __NEXT_DATA__: <script id="__NEXT_DATA__">
    3. HTML Tables: Fallback DOM parsing

Author: Bloomberg Data Crawler
"""

import json
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional
from urllib.parse import urlparse

from bs4 import BeautifulSoup


@dataclass
class BloombergQuote:
    """Bloomberg quote data structure"""

    ticker: str
    name: str
    price: Optional[float]
    change: Optional[float]
    change_percent: Optional[float]
    volume: Optional[float]
    market_cap: Optional[float]
    day_high: Optional[float]
    day_low: Optional[float]
    year_high: Optional[float]
    year_low: Optional[float]
    open_price: Optional[float]
    prev_close: Optional[float]
    currency: Optional[str]
    source: str  # json-ld, next-data, html
    timestamp: datetime


class BloombergParser:
    """
    Bloomberg HTML parser with multi-strategy extraction.

    Supports:
        - JSON-LD structured data
        - Next.js data extraction
        - HTML table parsing (fallback)
        - Robust number parsing (K/M/B/T, %, currency symbols)
    """

    # Field mapping for different data sources
    FIELD_MAPPING = {
        # JSON-LD mappings
        "json-ld": {
            "price": ["price", "priceValue", "currentPrice"],
            "name": ["name", "legalName", "alternateName"],
            "ticker": ["tickerSymbol", "ticker", "symbol"],
            "currency": ["priceCurrency", "currency"],
            "volume": ["volume", "tradingVolume"],
            "market_cap": ["marketCap", "marketCapitalization"],
            "change": ["priceChange", "change"],
            "change_percent": ["priceChangePercent", "changePercent"],
        },
        # __NEXT_DATA__ mappings - Bloomberg specific field names
        "next-data": {
            "price": ["price", "lastPrice", "last"],
            "name": ["name", "companyName", "securityName", "longName"],
            "ticker": ["ticker", "symbol", "id", "tickerSymbol"],
            "currency": ["currency", "priceCurrency", "isoCurrencyCode"],
            "volume": ["volume", "totalVolume", "averageVolume30Day"],
            "market_cap": ["marketCap", "mktCap", "marketCapitalization"],
            "day_high": ["highPrice", "high", "dayHigh", "todayHigh"],
            "day_low": ["lowPrice", "low", "dayLow", "todayLow"],
            "year_high": ["highPrice52Week", "yearHigh", "52WeekHigh", "high52Week"],
            "year_low": ["lowPrice52Week", "yearLow", "52WeekLow", "low52Week"],
            "open_price": ["openPrice", "open", "todayOpen"],
            "prev_close": ["prevClose", "previousClose", "previousClosingPriceOneTradingDayAgo", "close"],
            "change": ["priceChange1Day", "change", "netChange", "priceChange"],
            "change_percent": ["percentChange1Day", "changePercent", "pctChange", "percentChange"],
        },
        # HTML table mappings
        "html": {
            "day_range": ["Day Range", "Today's Range", "Intraday Range"],
            "52_week_range": ["52 Week Range", "52-Week Range", "Year Range"],
            "open": ["Open", "Opening Price", "Today's Open"],
            "prev_close": ["Previous Close", "Prev Close", "Yesterday's Close"],
            "volume": ["Volume", "Total Volume", "Trading Volume"],
            "market_cap": ["Market Cap", "Market Capitalization", "Mkt Cap"],
        }
    }

    def __init__(self, parser: str = "lxml"):
        """
        Initialize Bloomberg parser.

        Args:
            parser: BeautifulSoup parser backend (lxml, html.parser)
        """
        self.parser = parser

    def parse_quote_page(self, html: str, url: str) -> Optional[BloombergQuote]:
        """
        Parse individual Bloomberg quote page.

        Args:
            html: Raw HTML content
            url: Source URL for ticker extraction

        Returns:
            BloombergQuote object or None if parsing fails
        """
        soup = BeautifulSoup(html, self.parser)
        ticker = self._extract_ticker_from_url(url)

        # Extract company name from JSON-LD (Corporation type) for use later
        company_name = self._extract_company_name_from_json_ld(soup)

        # Strategy 1: Try __NEXT_DATA__ first (most reliable for Bloomberg)
        next_data = self._extract_next_data(soup)
        if next_data:
            quote = self._build_quote_from_next_data(next_data, ticker, company_name)
            if quote and quote.price is not None:
                return quote

        # Strategy 2: Try JSON-LD
        json_ld_data = self._extract_json_ld(soup)
        if json_ld_data:
            quote = self._build_quote_from_json_ld(json_ld_data, ticker)
            if quote and quote.price is not None:
                return quote

        # Strategy 3: Fallback to HTML parsing
        html_data = self._parse_html_quote(soup, ticker)
        if html_data:
            return html_data

        return None

    def _extract_company_name_from_json_ld(self, soup: BeautifulSoup) -> str:
        """Extract company name from JSON-LD Corporation schema."""
        scripts = soup.find_all("script", type="application/ld+json")

        for script in scripts:
            try:
                data = json.loads(script.string)
                if isinstance(data, dict) and data.get("@type") == "Corporation":
                    return data.get("name", "")
            except (json.JSONDecodeError, AttributeError):
                continue

        return ""

    def parse_markets_page(self, html: str, url: str) -> List[BloombergQuote]:
        """
        Parse Bloomberg markets page with multiple quotes.

        Args:
            html: Raw HTML content
            url: Source URL

        Returns:
            List of BloombergQuote objects
        """
        soup = BeautifulSoup(html, self.parser)
        quotes = []

        # Try extracting table data
        table_data = self._parse_html_tables(soup)
        for row in table_data:
            quote = self._build_quote_from_table_row(row)
            if quote:
                quotes.append(quote)

        # Try extracting card-based layouts
        cards = soup.find_all(["div", "article"], class_=re.compile(r"quote|market|stock", re.I))
        for card in cards:
            card_data = self._extract_card_data(card)
            if card_data:
                quote = self._build_quote_from_card(card_data)
                if quote:
                    quotes.append(quote)

        return quotes

    # ========== JSON-LD Extraction ==========

    def _extract_json_ld(self, soup: BeautifulSoup) -> Optional[Dict]:
        """
        Extract JSON-LD structured data.

        Args:
            soup: BeautifulSoup object

        Returns:
            Parsed JSON-LD data or None
        """
        scripts = soup.find_all("script", type="application/ld+json")

        for script in scripts:
            try:
                data = json.loads(script.string)

                # Bloomberg may use @graph array
                if isinstance(data, dict) and "@graph" in data:
                    for item in data["@graph"]:
                        if item.get("@type") in ["Corporation", "Organization", "FinancialProduct"]:
                            return item

                # Direct JSON-LD object
                if isinstance(data, dict) and "@type" in data:
                    return data

            except (json.JSONDecodeError, AttributeError):
                continue

        return None

    def _build_quote_from_json_ld(self, data: Dict, ticker: str) -> Optional[BloombergQuote]:
        """
        Build BloombergQuote from JSON-LD data.

        Args:
            data: Parsed JSON-LD dictionary
            ticker: Stock ticker symbol

        Returns:
            BloombergQuote or None
        """
        try:
            # Extract fields using mapping
            fields = {}
            for field, keys in self.FIELD_MAPPING["json-ld"].items():
                fields[field] = self._find_field_value(data, keys)

            # Parse numbers
            price = self._parse_number(fields.get("price"))
            change = self._parse_number(fields.get("change"))
            change_percent = self._parse_number(fields.get("change_percent"))
            volume = self._parse_number(fields.get("volume"))
            market_cap = self._parse_number(fields.get("market_cap"))

            return BloombergQuote(
                ticker=ticker or fields.get("ticker", "UNKNOWN"),
                name=fields.get("name", ""),
                price=price,
                change=change,
                change_percent=change_percent,
                volume=volume,
                market_cap=market_cap,
                day_high=None,
                day_low=None,
                year_high=None,
                year_low=None,
                open_price=None,
                prev_close=None,
                currency=fields.get("currency", "USD"),
                source="json-ld",
                timestamp=datetime.now()
            )
        except Exception:
            return None

    # ========== __NEXT_DATA__ Extraction ==========

    def _extract_next_data(self, soup: BeautifulSoup) -> Optional[Dict]:
        """
        Extract Next.js __NEXT_DATA__ from script tag.

        Args:
            soup: BeautifulSoup object

        Returns:
            Parsed Next.js data or None
        """
        script = soup.find("script", id="__NEXT_DATA__")

        if script and script.string:
            try:
                data = json.loads(script.string)

                # Navigate to props data
                props = data.get("props", {})
                page_props = props.get("pageProps", {})

                # Bloomberg quote page structure: pageProps.quote contains all data
                if "quote" in page_props:
                    quote_data = page_props["quote"]
                    # Also extract company name from JSON-LD if not in quote
                    if isinstance(quote_data, dict) and not quote_data.get("name"):
                        # Try to get name from pageData or other sources
                        if "pageData" in page_props:
                            page_data = page_props["pageData"]
                            if isinstance(page_data, dict):
                                quote_data["name"] = page_data.get("name", "")
                    return quote_data

                elif "security" in page_props:
                    return page_props["security"]
                elif "data" in page_props:
                    return page_props["data"]

                return page_props if page_props else None

            except json.JSONDecodeError:
                return None

        return None

    def _build_quote_from_next_data(
        self, data: Dict, ticker: str, company_name: str = ""
    ) -> Optional[BloombergQuote]:
        """
        Build BloombergQuote from __NEXT_DATA__.

        Args:
            data: Parsed Next.js data dictionary
            ticker: Stock ticker symbol
            company_name: Company name from JSON-LD (optional)

        Returns:
            BloombergQuote or None
        """
        try:
            # Extract fields using mapping
            fields = {}
            for field, keys in self.FIELD_MAPPING["next-data"].items():
                fields[field] = self._find_field_value(data, keys)

            # Parse all numeric fields
            price = self._parse_number(fields.get("price"))
            change = self._parse_number(fields.get("change"))
            change_percent = self._parse_number(fields.get("change_percent"))
            volume = self._parse_number(fields.get("volume"))
            market_cap = self._parse_number(fields.get("market_cap"))
            day_high = self._parse_number(fields.get("day_high"))
            day_low = self._parse_number(fields.get("day_low"))
            year_high = self._parse_number(fields.get("year_high"))
            year_low = self._parse_number(fields.get("year_low"))
            open_price = self._parse_number(fields.get("open_price"))
            prev_close = self._parse_number(fields.get("prev_close"))

            # Use company_name from JSON-LD if available, otherwise from data
            name = company_name or fields.get("name", "")

            return BloombergQuote(
                ticker=ticker or fields.get("ticker", "UNKNOWN"),
                name=name,
                price=price,
                change=change,
                change_percent=change_percent,
                volume=volume,
                market_cap=market_cap,
                day_high=day_high,
                day_low=day_low,
                year_high=year_high,
                year_low=year_low,
                open_price=open_price,
                prev_close=prev_close,
                currency=fields.get("currency", "USD"),
                source="next-data",
                timestamp=datetime.now()
            )
        except Exception:
            return None

    # ========== HTML Table Parsing ==========

    def _parse_html_quote(self, soup: BeautifulSoup, ticker: str) -> Optional[BloombergQuote]:
        """
        Parse quote from HTML structure (fallback).

        Args:
            soup: BeautifulSoup object
            ticker: Stock ticker symbol

        Returns:
            BloombergQuote or None
        """
        try:
            # Extract name
            name = ""
            name_elem = soup.find(["h1", "h2"], class_=re.compile(r"name|title|security", re.I))
            if name_elem:
                name = name_elem.get_text(strip=True)

            # Extract price
            price = None
            price_elem = soup.find(["span", "div"], class_=re.compile(r"price|last|value", re.I))
            if price_elem:
                price = self._parse_number(price_elem.get_text(strip=True))

            # Extract change and change %
            change = None
            change_percent = None
            change_elem = soup.find(["span", "div"], class_=re.compile(r"change|diff", re.I))
            if change_elem:
                change_text = change_elem.get_text(strip=True)
                if "%" in change_text:
                    change_percent = self._parse_number(change_text)
                else:
                    change = self._parse_number(change_text)

            # Parse data table for additional fields
            table_data = {}
            tables = soup.find_all("table")
            for table in tables:
                rows = table.find_all("tr")
                for row in rows:
                    cells = row.find_all(["td", "th"])
                    if len(cells) >= 2:
                        label = cells[0].get_text(strip=True)
                        value = cells[1].get_text(strip=True)
                        table_data[label] = value

            # Extract fields from table
            volume = self._extract_field_from_table(table_data, self.FIELD_MAPPING["html"]["volume"])
            market_cap = self._extract_field_from_table(table_data, self.FIELD_MAPPING["html"]["market_cap"])
            open_price = self._extract_field_from_table(table_data, self.FIELD_MAPPING["html"]["open"])
            prev_close = self._extract_field_from_table(table_data, self.FIELD_MAPPING["html"]["prev_close"])

            # Parse day range (extract raw string value)
            day_high, day_low = None, None
            day_range_str = self._extract_raw_field_from_table(table_data, self.FIELD_MAPPING["html"]["day_range"])
            if day_range_str:
                day_high, day_low = self._parse_range(day_range_str)

            # Parse 52-week range (extract raw string value)
            year_high, year_low = None, None
            year_range_str = self._extract_raw_field_from_table(table_data, self.FIELD_MAPPING["html"]["52_week_range"])
            if year_range_str:
                year_high, year_low = self._parse_range(year_range_str)

            return BloombergQuote(
                ticker=ticker,
                name=name,
                price=price,
                change=change,
                change_percent=change_percent,
                volume=volume,
                market_cap=market_cap,
                day_high=day_high,
                day_low=day_low,
                year_high=year_high,
                year_low=year_low,
                open_price=open_price,
                prev_close=prev_close,
                currency="USD",
                source="html",
                timestamp=datetime.now()
            )
        except Exception:
            return None

    def _parse_html_tables(self, soup: BeautifulSoup) -> List[Dict]:
        """
        Extract all quote data from HTML tables.

        Args:
            soup: BeautifulSoup object

        Returns:
            List of dictionaries with table row data
        """
        results = []
        tables = soup.find_all("table")

        for table in tables:
            rows = table.find_all("tr")
            headers = []

            # Find headers
            header_row = table.find("thead") or table.find("tr")
            if header_row:
                headers = [th.get_text(strip=True) for th in header_row.find_all(["th", "td"])]

            # Parse data rows
            for row in rows[1:] if headers else rows:
                cells = row.find_all(["td", "th"])
                if len(cells) >= 2:
                    row_data = {}
                    for i, cell in enumerate(cells):
                        header = headers[i] if i < len(headers) else f"col_{i}"
                        row_data[header] = cell.get_text(strip=True)
                    results.append(row_data)

        return results

    def _build_quote_from_table_row(self, row: Dict) -> Optional[BloombergQuote]:
        """
        Build BloombergQuote from table row data.

        Args:
            row: Dictionary with table row data

        Returns:
            BloombergQuote or None
        """
        try:
            # Extract ticker and name
            ticker = row.get("Symbol", row.get("Ticker", "UNKNOWN"))
            name = row.get("Name", row.get("Security", ""))

            # Parse numeric fields
            price = self._parse_number(row.get("Price", row.get("Last", "")))
            change = self._parse_number(row.get("Change", ""))
            change_percent = self._parse_number(row.get("% Change", row.get("Change %", "")))
            volume = self._parse_number(row.get("Volume", ""))

            if not ticker or not price:
                return None

            return BloombergQuote(
                ticker=ticker,
                name=name,
                price=price,
                change=change,
                change_percent=change_percent,
                volume=volume,
                market_cap=None,
                day_high=None,
                day_low=None,
                year_high=None,
                year_low=None,
                open_price=None,
                prev_close=None,
                currency="USD",
                source="html",
                timestamp=datetime.now()
            )
        except Exception:
            return None

    # ========== Card-based Layout Parsing ==========

    def _extract_card_data(self, card: BeautifulSoup) -> Optional[Dict]:
        """
        Extract data from card-based quote layout.

        Args:
            card: BeautifulSoup element for quote card

        Returns:
            Dictionary with extracted data or None
        """
        try:
            data = {}

            # Extract ticker
            ticker_elem = card.find(["span", "div"], class_=re.compile(r"ticker|symbol", re.I))
            if ticker_elem:
                data["ticker"] = ticker_elem.get_text(strip=True)

            # Extract name
            name_elem = card.find(["h3", "h4", "span"], class_=re.compile(r"name|title", re.I))
            if name_elem:
                data["name"] = name_elem.get_text(strip=True)

            # Extract price
            price_elem = card.find(["span", "div"], class_=re.compile(r"price|last", re.I))
            if price_elem:
                data["price"] = price_elem.get_text(strip=True)

            # Extract change
            change_elem = card.find(["span", "div"], class_=re.compile(r"change", re.I))
            if change_elem:
                data["change"] = change_elem.get_text(strip=True)

            return data if data else None
        except Exception:
            return None

    def _build_quote_from_card(self, data: Dict) -> Optional[BloombergQuote]:
        """
        Build BloombergQuote from card data.

        Args:
            data: Dictionary with card data

        Returns:
            BloombergQuote or None
        """
        try:
            ticker = data.get("ticker", "UNKNOWN")
            name = data.get("name", "")
            price = self._parse_number(data.get("price", ""))

            if not ticker or not price:
                return None

            # Parse change field - may contain both change and change_percent
            change = None
            change_percent = None
            change_str = data.get("change", "")

            if change_str:
                # Split on parentheses to separate change and percent
                # Example: "+15.50 (3.04%)" -> ["+15.50 ", "3.04%)"]
                parts = change_str.split("(")
                if len(parts) == 2:
                    # Has both change and percent
                    change = self._parse_number(parts[0].strip())
                    change_percent = self._parse_number(parts[1].replace(")", "").strip())
                elif "%" in change_str:
                    # Only percentage
                    change_percent = self._parse_number(change_str)
                else:
                    # Only change value
                    change = self._parse_number(change_str)

            return BloombergQuote(
                ticker=ticker,
                name=name,
                price=price,
                change=change,
                change_percent=change_percent,
                volume=None,
                market_cap=None,
                day_high=None,
                day_low=None,
                year_high=None,
                year_low=None,
                open_price=None,
                prev_close=None,
                currency="USD",
                source="html",
                timestamp=datetime.now()
            )
        except Exception:
            return None

    # ========== Utility Methods ==========

    def _parse_number(self, value) -> Optional[float]:
        """
        Parse numeric value with support for:
            - K/M/B/T suffixes (1.5K = 1500)
            - Percentage symbols (5.2% = 5.2)
            - Currency symbols ($1,234.56 = 1234.56)
            - Commas and whitespace
            - Negative values

        Args:
            value: String or numeric representation of number

        Returns:
            Parsed float or None
        """
        if value is None:
            return None

        # Already a number
        if isinstance(value, (int, float)):
            return float(value)

        if not isinstance(value, str):
            return None

        # Clean the string
        value = value.strip()

        # Remove currency symbols and common prefixes
        value = re.sub(r'[$€£¥₹,\s]', '', value)

        # Handle percentage
        is_percentage = "%" in value
        value = value.replace("%", "")

        # Handle suffix multipliers
        multipliers = {
            "K": 1_000,
            "M": 1_000_000,
            "B": 1_000_000_000,
            "T": 1_000_000_000_000,
        }

        multiplier = 1
        for suffix, mult in multipliers.items():
            if value.upper().endswith(suffix):
                multiplier = mult
                value = value[:-1]
                break

        # Parse the number
        try:
            number = float(value) * multiplier
            return number
        except (ValueError, TypeError):
            return None

    def _parse_range(self, range_str: str) -> tuple[Optional[float], Optional[float]]:
        """
        Parse range string (e.g., "100.5 - 105.3").

        Args:
            range_str: Range string

        Returns:
            Tuple of (high, low) or (None, None)
        """
        if not range_str:
            return None, None

        # Split by common delimiters
        parts = re.split(r'[-–—]', range_str)

        if len(parts) == 2:
            low = self._parse_number(parts[0].strip())
            high = self._parse_number(parts[1].strip())
            return high, low

        return None, None

    def _find_field_value(self, data: Dict, keys: List[str]) -> Optional[str]:
        """
        Find field value from data using multiple possible keys.

        Args:
            data: Dictionary to search
            keys: List of possible keys

        Returns:
            Field value or None
        """
        for key in keys:
            # Direct key match
            if key in data:
                return data[key]

            # Case-insensitive search
            for data_key in data.keys():
                if data_key.lower() == key.lower():
                    return data[data_key]

        return None

    def _extract_field_from_table(self, table_data: Dict, keys: List[str]) -> Optional[float]:
        """
        Extract and parse numeric field from table data.

        Args:
            table_data: Dictionary with table label-value pairs
            keys: List of possible label names

        Returns:
            Parsed numeric value or None
        """
        for key in keys:
            for label, value in table_data.items():
                if key.lower() in label.lower():
                    return self._parse_number(value)
        return None

    def _extract_raw_field_from_table(self, table_data: Dict, keys: List[str]) -> Optional[str]:
        """
        Extract raw string field from table data (without parsing).

        Args:
            table_data: Dictionary with table label-value pairs
            keys: List of possible label names

        Returns:
            Raw string value or None
        """
        for key in keys:
            for label, value in table_data.items():
                if key.lower() in label.lower():
                    return value
        return None

    def _extract_ticker_from_url(self, url: str) -> str:
        """
        Extract ticker symbol from Bloomberg URL.

        Args:
            url: Bloomberg URL

        Returns:
            Ticker symbol or empty string
        """
        try:
            parsed = urlparse(url)
            path_parts = parsed.path.strip("/").split("/")

            # Common Bloomberg URL patterns:
            # /quote/{TICKER}:US
            # /markets/stocks/{TICKER}
            for part in path_parts:
                # Remove country suffix
                ticker = part.split(":")[0]
                # Check if it looks like a ticker (uppercase, 1-5 chars)
                if ticker.isupper() and 1 <= len(ticker) <= 5:
                    return ticker

            return ""
        except Exception:
            return ""
