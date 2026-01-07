"""
Unit tests for Bloomberg HTML parser.

Tests all three extraction strategies and number parsing utilities.
"""

import json
from datetime import datetime

import pytest

from src.parsers.bloomberg_parser import BloombergParser, BloombergQuote


@pytest.fixture
def parser():
    """Create parser instance."""
    return BloombergParser()


class TestNumberParsing:
    """Test number parsing utilities."""

    @pytest.mark.parametrize("input_value,expected", [
        # Basic numbers
        ("123", 123.0),
        ("123.45", 123.45),
        ("-45.67", -45.67),
        # With commas
        ("1,234", 1234.0),
        ("1,234,567.89", 1234567.89),
        # Currency symbols
        ("$123.45", 123.45),
        ("€1,234.56", 1234.56),
        ("£999.99", 999.99),
        ("¥1234", 1234.0),
        ("₹12,345", 12345.0),
        # Percentages
        ("5.2%", 5.2),
        ("-2.5%", -2.5),
        ("0.15%", 0.15),
        # Suffixes
        ("1.5K", 1500.0),
        ("2.3M", 2300000.0),
        ("1.2B", 1200000000.0),
        ("5.5T", 5500000000000.0),
        ("500k", 500000.0),  # lowercase
        # Complex cases
        ("$1.5M", 1500000.0),
        ("-$2.3B", -2300000000.0),
        ("€15.2K", 15200.0),
        # Whitespace
        ("  123.45  ", 123.45),
        ("1 234", 1234.0),
        # Invalid
        ("", None),
        ("N/A", None),
        ("--", None),
        (None, None),
    ])
    def test_parse_number(self, parser, input_value, expected):
        """Test number parsing with various formats."""
        result = parser._parse_number(input_value)
        if expected is None:
            assert result is None
        else:
            assert result == pytest.approx(expected, rel=1e-6)

    @pytest.mark.parametrize("range_str,expected_high,expected_low", [
        ("100 - 105", 105.0, 100.0),
        ("100.5-105.3", 105.3, 100.5),
        ("$50 - $60", 60.0, 50.0),
        ("1.2K - 1.5K", 1500.0, 1200.0),
        ("", None, None),
        ("single", None, None),
    ])
    def test_parse_range(self, parser, range_str, expected_high, expected_low):
        """Test range parsing."""
        high, low = parser._parse_range(range_str)
        if expected_high is None:
            assert high is None and low is None
        else:
            assert high == pytest.approx(expected_high)
            assert low == pytest.approx(expected_low)


class TestJsonLdExtraction:
    """Test JSON-LD extraction strategy."""

    def test_extract_json_ld_simple(self, parser):
        """Test simple JSON-LD extraction."""
        html = """
        <html>
        <script type="application/ld+json">
        {
            "@type": "Corporation",
            "name": "Apple Inc.",
            "tickerSymbol": "AAPL",
            "price": "150.25",
            "priceCurrency": "USD"
        }
        </script>
        </html>
        """

        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "lxml")
        result = parser._extract_json_ld(soup)

        assert result is not None
        assert result["@type"] == "Corporation"
        assert result["name"] == "Apple Inc."
        assert result["tickerSymbol"] == "AAPL"

    def test_extract_json_ld_with_graph(self, parser):
        """Test JSON-LD with @graph array."""
        html = """
        <html>
        <script type="application/ld+json">
        {
            "@context": "https://schema.org",
            "@graph": [
                {
                    "@type": "WebPage",
                    "name": "Bloomberg"
                },
                {
                    "@type": "Organization",
                    "name": "Tesla Inc.",
                    "tickerSymbol": "TSLA",
                    "price": "250.50"
                }
            ]
        }
        </script>
        </html>
        """

        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "lxml")
        result = parser._extract_json_ld(soup)

        assert result is not None
        assert result["@type"] == "Organization"
        assert result["tickerSymbol"] == "TSLA"

    def test_build_quote_from_json_ld(self, parser):
        """Test building quote from JSON-LD data."""
        data = {
            "@type": "Corporation",
            "name": "Microsoft Corporation",
            "tickerSymbol": "MSFT",
            "price": 375.25,
            "priceChange": 5.50,
            "priceChangePercent": 1.49,
            "volume": 25000000,
            "marketCap": 2800000000000,
            "priceCurrency": "USD"
        }

        quote = parser._build_quote_from_json_ld(data, "MSFT")

        assert quote is not None
        assert quote.ticker == "MSFT"
        assert quote.name == "Microsoft Corporation"
        assert quote.price == 375.25
        assert quote.change == 5.50
        assert quote.change_percent == 1.49
        assert quote.volume == 25000000
        assert quote.market_cap == 2800000000000
        assert quote.currency == "USD"
        assert quote.source == "json-ld"


class TestNextDataExtraction:
    """Test __NEXT_DATA__ extraction strategy."""

    def test_extract_next_data(self, parser):
        """Test __NEXT_DATA__ extraction."""
        html = """
        <html>
        <script id="__NEXT_DATA__" type="application/json">
        {
            "props": {
                "pageProps": {
                    "quote": {
                        "ticker": "GOOGL",
                        "name": "Alphabet Inc.",
                        "lastPrice": 140.50,
                        "change": -2.30,
                        "changePercent": -1.61
                    }
                }
            }
        }
        </script>
        </html>
        """

        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "lxml")
        result = parser._extract_next_data(soup)

        assert result is not None
        assert result["ticker"] == "GOOGL"
        assert result["name"] == "Alphabet Inc."

    def test_build_quote_from_next_data(self, parser):
        """Test building quote from __NEXT_DATA__."""
        data = {
            "ticker": "AMZN",
            "name": "Amazon.com Inc.",
            "lastPrice": 155.75,
            "change": 3.25,
            "changePercent": 2.13,
            "volume": 50000000,
            "marketCap": 1600000000000,
            "high": 157.00,
            "low": 153.50,
            "open": 154.00,
            "previousClose": 152.50,
            "yearHigh": 180.00,
            "yearLow": 120.00,
            "currency": "USD"
        }

        quote = parser._build_quote_from_next_data(data, "AMZN")

        assert quote is not None
        assert quote.ticker == "AMZN"
        assert quote.price == 155.75
        assert quote.change == 3.25
        assert quote.day_high == 157.00
        assert quote.day_low == 153.50
        assert quote.year_high == 180.00
        assert quote.year_low == 120.00
        assert quote.open_price == 154.00
        assert quote.prev_close == 152.50
        assert quote.source == "next-data"


class TestHtmlParsing:
    """Test HTML fallback parsing."""

    def test_parse_html_quote(self, parser):
        """Test HTML quote parsing."""
        html = """
        <html>
        <body>
            <h1 class="security-name">NVIDIA Corporation</h1>
            <div class="price-value">$485.50</div>
            <span class="price-change">+12.35 (2.61%)</span>
            <table>
                <tr><td>Open</td><td>$475.00</td></tr>
                <tr><td>Previous Close</td><td>$473.15</td></tr>
                <tr><td>Volume</td><td>45.2M</td></tr>
                <tr><td>Market Cap</td><td>$1.2T</td></tr>
                <tr><td>Day Range</td><td>$472.00 - $487.50</td></tr>
                <tr><td>52 Week Range</td><td>$380.00 - $502.00</td></tr>
            </table>
        </body>
        </html>
        """

        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "lxml")
        quote = parser._parse_html_quote(soup, "NVDA")

        assert quote is not None
        assert quote.ticker == "NVDA"
        assert quote.name == "NVIDIA Corporation"
        assert quote.price == 485.50
        assert quote.open_price == 475.00
        assert quote.prev_close == 473.15
        assert quote.volume == 45200000
        assert quote.market_cap == 1200000000000
        assert quote.day_high == 487.50
        assert quote.day_low == 472.00
        assert quote.year_high == 502.00
        assert quote.year_low == 380.00
        assert quote.source == "html"

    def test_parse_html_tables(self, parser):
        """Test HTML table parsing."""
        html = """
        <html>
        <table>
            <thead>
                <tr>
                    <th>Symbol</th>
                    <th>Name</th>
                    <th>Price</th>
                    <th>Change</th>
                    <th>% Change</th>
                    <th>Volume</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td>AAPL</td>
                    <td>Apple Inc.</td>
                    <td>$175.50</td>
                    <td>+2.25</td>
                    <td>1.30%</td>
                    <td>55.3M</td>
                </tr>
                <tr>
                    <td>MSFT</td>
                    <td>Microsoft</td>
                    <td>$380.00</td>
                    <td>-3.50</td>
                    <td>-0.91%</td>
                    <td>22.1M</td>
                </tr>
            </tbody>
        </table>
        </html>
        """

        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "lxml")
        results = parser._parse_html_tables(soup)

        assert len(results) == 2
        assert results[0]["Symbol"] == "AAPL"
        assert results[0]["Price"] == "$175.50"
        assert results[1]["Symbol"] == "MSFT"

    def test_build_quote_from_table_row(self, parser):
        """Test building quote from table row."""
        row = {
            "Symbol": "TSLA",
            "Name": "Tesla Inc.",
            "Price": "$245.50",
            "Change": "+5.75",
            "% Change": "2.40%",
            "Volume": "120.5M"
        }

        quote = parser._build_quote_from_table_row(row)

        assert quote is not None
        assert quote.ticker == "TSLA"
        assert quote.name == "Tesla Inc."
        assert quote.price == 245.50
        assert quote.change == 5.75
        assert quote.change_percent == 2.40
        assert quote.volume == 120500000


class TestCardParsing:
    """Test card-based layout parsing."""

    def test_extract_card_data(self, parser):
        """Test extracting data from quote card."""
        html = """
        <div class="quote-card">
            <span class="ticker-symbol">META</span>
            <h3 class="company-name">Meta Platforms Inc.</h3>
            <div class="current-price">$385.50</div>
            <span class="price-change">+8.25 (2.19%)</span>
        </div>
        """

        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "lxml")
        card = soup.find("div", class_="quote-card")
        data = parser._extract_card_data(card)

        assert data is not None
        assert data["ticker"] == "META"
        assert data["name"] == "Meta Platforms Inc."
        assert data["price"] == "$385.50"

    def test_build_quote_from_card(self, parser):
        """Test building quote from card data."""
        data = {
            "ticker": "NFLX",
            "name": "Netflix Inc.",
            "price": "$525.00",
            "change": "+15.50 (3.04%)"
        }

        quote = parser._build_quote_from_card(data)

        assert quote is not None
        assert quote.ticker == "NFLX"
        assert quote.name == "Netflix Inc."
        assert quote.price == 525.00
        assert quote.change == 15.50
        assert quote.change_percent == 3.04


class TestUrlParsing:
    """Test URL parsing utilities."""

    @pytest.mark.parametrize("url,expected_ticker", [
        ("https://www.bloomberg.com/quote/AAPL:US", "AAPL"),
        ("https://www.bloomberg.com/markets/stocks/MSFT", "MSFT"),
        ("https://www.bloomberg.com/quote/TSLA:NASDAQ", "TSLA"),
        ("https://bloomberg.com/GOOGL", "GOOGL"),
        ("https://bloomberg.com/invalid-url", ""),
        ("", ""),
    ])
    def test_extract_ticker_from_url(self, parser, url, expected_ticker):
        """Test ticker extraction from URLs."""
        result = parser._extract_ticker_from_url(url)
        assert result == expected_ticker


class TestIntegration:
    """Integration tests with complete HTML pages."""

    def test_parse_quote_page_json_ld_priority(self, parser):
        """Test that JSON-LD takes priority over other methods."""
        html = """
        <html>
        <head>
            <script type="application/ld+json">
            {
                "@type": "Corporation",
                "name": "Apple Inc.",
                "tickerSymbol": "AAPL",
                "price": 175.50,
                "priceCurrency": "USD"
            }
            </script>
        </head>
        <body>
            <h1>Wrong Name</h1>
            <div class="price">$999.99</div>
        </body>
        </html>
        """

        quote = parser.parse_quote_page(html, "https://bloomberg.com/quote/AAPL:US")

        assert quote is not None
        assert quote.source == "json-ld"
        assert quote.name == "Apple Inc."
        assert quote.price == 175.50

    def test_parse_quote_page_fallback_to_html(self, parser):
        """Test fallback to HTML when structured data unavailable."""
        html = """
        <html>
        <body>
            <h1 class="security-name">Tesla Inc.</h1>
            <div class="price-value">$245.50</div>
            <table>
                <tr><td>Volume</td><td>120.5M</td></tr>
            </table>
        </body>
        </html>
        """

        quote = parser.parse_quote_page(html, "https://bloomberg.com/quote/TSLA:US")

        assert quote is not None
        assert quote.source == "html"
        assert quote.ticker == "TSLA"
        assert quote.price == 245.50

    def test_parse_markets_page(self, parser):
        """Test parsing markets page with multiple quotes."""
        html = """
        <html>
        <table>
            <tr>
                <th>Symbol</th>
                <th>Price</th>
                <th>Change</th>
            </tr>
            <tr>
                <td>AAPL</td>
                <td>$175.50</td>
                <td>+2.25</td>
            </tr>
            <tr>
                <td>MSFT</td>
                <td>$380.00</td>
                <td>-3.50</td>
            </tr>
        </table>
        </html>
        """

        quotes = parser.parse_markets_page(html, "https://bloomberg.com/markets")

        assert len(quotes) >= 2
        tickers = [q.ticker for q in quotes]
        assert "AAPL" in tickers
        assert "MSFT" in tickers


class TestFieldMapping:
    """Test field mapping functionality."""

    def test_find_field_value_exact_match(self, parser):
        """Test exact key matching."""
        data = {"price": 100.0, "name": "Test"}
        result = parser._find_field_value(data, ["price", "value"])
        assert result == 100.0

    def test_find_field_value_case_insensitive(self, parser):
        """Test case-insensitive matching."""
        data = {"Price": 100.0, "Name": "Test"}
        result = parser._find_field_value(data, ["price", "value"])
        assert result == 100.0

    def test_find_field_value_fallback(self, parser):
        """Test fallback to alternative keys."""
        data = {"lastPrice": 100.0}
        result = parser._find_field_value(data, ["price", "lastPrice"])
        assert result == 100.0

    def test_find_field_value_not_found(self, parser):
        """Test when field not found."""
        data = {"other": 100.0}
        result = parser._find_field_value(data, ["price", "value"])
        assert result is None
