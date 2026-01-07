"""
JSON Lines Writer for Market Data Storage.

Provides efficient JSONL-based storage with daily partitioning using orjson
for fast serialization. Optimized for streaming data and analytical queries.
"""

from datetime import datetime
from pathlib import Path
from typing import Any, List, Optional

import orjson

from ..config import CacheConfig
from ..normalizer.schemas import MarketQuote


class JSONWriter:
    """
    JSON Lines writer with daily partitioning and streaming support.

    File Structure:
        data/{asset_class}/{symbol}/YYYYMMDD.jsonl

    Features:
        - One JSON object per line (JSONL format)
        - Fast serialization using orjson
        - Daily partitioning for efficient queries
        - Streaming write support
        - Batch write optimization

    Example:
        >>> writer = JSONWriter()
        >>> quote = MarketQuote(...)
        >>> writer.write(quote)
        True
        >>> quotes = [quote1, quote2, quote3]
        >>> writer.write_batch(quotes)
        3
    """

    def __init__(self, base_dir: Optional[Path] = None):
        """
        Initialize JSON Lines writer.

        Args:
            base_dir: Base directory for data storage (defaults to Config.DATA_DIR)
        """
        self.base_dir = base_dir or CacheConfig.DATA_DIR
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def write(self, quote: MarketQuote) -> bool:
        """
        Write a single quote to JSONL file.

        Automatically creates directory structure and appends JSON object
        as a new line. Uses orjson for fast serialization.

        Args:
            quote: Market quote to write

        Returns:
            bool: True if write was successful, False otherwise

        Example:
            >>> quote = MarketQuote(symbol="AAPL:US", price=175.50, ...)
            >>> writer.write(quote)
            True
        """
        try:
            file_path = self.get_file_path(quote)

            # Ensure parent directory exists
            file_path.parent.mkdir(parents=True, exist_ok=True)

            # Convert quote to dictionary
            data = quote.to_dict()

            # Serialize to JSON using orjson (fast C implementation)
            # orjson.dumps returns bytes, so we need to decode
            json_line = orjson.dumps(
                data,
                option=orjson.OPT_APPEND_NEWLINE | orjson.OPT_UTC_Z
            )

            # Append to file
            with open(file_path, mode="ab") as f:  # Binary append mode
                f.write(json_line)

            return True

        except Exception as e:
            # Log error but don't raise to allow graceful degradation
            print(f"Error writing JSON for {quote.symbol}: {e}")
            return False

    def write_batch(self, quotes: List[MarketQuote]) -> int:
        """
        Write multiple quotes efficiently in batch.

        Groups quotes by file path and writes them together to minimize
        I/O operations. More efficient than individual writes.

        Args:
            quotes: List of market quotes to write

        Returns:
            int: Number of quotes successfully written

        Example:
            >>> quotes = [quote1, quote2, quote3]
            >>> count = writer.write_batch(quotes)
            >>> print(f"Wrote {count} quotes")
            Wrote 3 quotes
        """
        if not quotes:
            return 0

        written_count = 0

        # Group quotes by file path for efficient batch writing
        quotes_by_file: dict[Path, List[MarketQuote]] = {}

        for quote in quotes:
            file_path = self.get_file_path(quote)
            if file_path not in quotes_by_file:
                quotes_by_file[file_path] = []
            quotes_by_file[file_path].append(quote)

        # Write each group to its respective file
        for file_path, file_quotes in quotes_by_file.items():
            try:
                # Ensure parent directory exists
                file_path.parent.mkdir(parents=True, exist_ok=True)

                # Write all quotes for this file
                with open(file_path, mode="ab") as f:  # Binary append mode
                    for quote in file_quotes:
                        data = quote.to_dict()
                        json_line = orjson.dumps(
                            data,
                            option=orjson.OPT_APPEND_NEWLINE | orjson.OPT_UTC_Z
                        )
                        f.write(json_line)
                        written_count += 1

            except Exception as e:
                print(f"Error writing batch to {file_path}: {e}")
                continue

        return written_count

    def get_file_path(self, quote: MarketQuote) -> Path:
        """
        Generate file path for a quote based on partitioning scheme.

        Path format: {base_dir}/{asset_class}/{symbol}/YYYYMMDD.jsonl

        Args:
            quote: Market quote to generate path for

        Returns:
            Path: Full path to JSONL file

        Example:
            >>> quote = MarketQuote(symbol="AAPL:US", asset_class="stocks", ...)
            >>> path = writer.get_file_path(quote)
            >>> print(path)
            data/stocks/AAPL_US/20240115.jsonl
        """
        # Format date as YYYYMMDD
        date_str = quote.timestamp.strftime("%Y%m%d")

        # Sanitize symbol for filesystem (replace : with _)
        safe_symbol = quote.symbol.replace(":", "_").replace("/", "_")

        # Build path: base_dir/asset_class/symbol/YYYYMMDD.jsonl
        file_path = (
            self.base_dir
            / quote.asset_class.value
            / safe_symbol
            / f"{date_str}.jsonl"
        )

        return file_path

    def read_today(self, asset_class: str, symbol: str) -> List[dict]:
        """
        Read today's data for a specific symbol.

        Convenience method for reading current day's JSONL file.
        Parses each line as a separate JSON object.

        Args:
            asset_class: Asset class (e.g., "stocks", "forex")
            symbol: Trading symbol (e.g., "AAPL:US")

        Returns:
            List[dict]: List of quote dictionaries, empty if file doesn't exist

        Example:
            >>> quotes = writer.read_today("stocks", "AAPL:US")
            >>> print(f"Found {len(quotes)} quotes today")
            Found 24 quotes today
        """
        # Get today's date
        today = datetime.utcnow().strftime("%Y%m%d")

        # Sanitize symbol for filesystem
        safe_symbol = symbol.replace(":", "_").replace("/", "_")

        # Build file path
        file_path = self.base_dir / asset_class / safe_symbol / f"{today}.jsonl"

        # Return empty list if file doesn't exist
        if not file_path.exists():
            return []

        # Read JSONL file
        try:
            quotes = []
            with open(file_path, mode="rb") as f:  # Binary read for orjson
                for line in f:
                    if line.strip():  # Skip empty lines
                        data = orjson.loads(line)
                        quotes.append(data)
            return quotes
        except Exception as e:
            print(f"Error reading {file_path}: {e}")
            return []

    def read_file(self, file_path: Path) -> List[dict]:
        """
        Read a specific JSONL file.

        Args:
            file_path: Path to JSONL file

        Returns:
            List[dict]: List of quote dictionaries

        Example:
            >>> path = Path("data/stocks/AAPL_US/20240115.jsonl")
            >>> quotes = writer.read_file(path)
        """
        if not file_path.exists():
            return []

        try:
            quotes = []
            with open(file_path, mode="rb") as f:
                for line in f:
                    if line.strip():
                        data = orjson.loads(line)
                        quotes.append(data)
            return quotes
        except Exception as e:
            print(f"Error reading {file_path}: {e}")
            return []

    def file_exists(self, quote: MarketQuote) -> bool:
        """
        Check if JSONL file exists for a quote's date.

        Args:
            quote: Market quote to check

        Returns:
            bool: True if file exists, False otherwise
        """
        return self.get_file_path(quote).exists()

    def get_all_symbols(self, asset_class: str) -> List[str]:
        """
        Get list of all symbols for an asset class.

        Args:
            asset_class: Asset class to scan (e.g., "stocks")

        Returns:
            List[str]: List of symbol names (filesystem safe format)

        Example:
            >>> symbols = writer.get_all_symbols("stocks")
            >>> print(symbols)
            ['AAPL_US', 'MSFT_US', 'GOOGL_US']
        """
        asset_dir = self.base_dir / asset_class

        if not asset_dir.exists():
            return []

        # Get all directories (each represents a symbol)
        return [d.name for d in asset_dir.iterdir() if d.is_dir()]

    def get_date_range(self, asset_class: str, symbol: str) -> tuple[Optional[str], Optional[str]]:
        """
        Get date range of available data for a symbol.

        Args:
            asset_class: Asset class
            symbol: Trading symbol

        Returns:
            tuple: (earliest_date, latest_date) as YYYYMMDD strings, or (None, None)

        Example:
            >>> start, end = writer.get_date_range("stocks", "AAPL:US")
            >>> print(f"Data from {start} to {end}")
            Data from 20240101 to 20240115
        """
        safe_symbol = symbol.replace(":", "_").replace("/", "_")
        symbol_dir = self.base_dir / asset_class / safe_symbol

        if not symbol_dir.exists():
            return (None, None)

        # Get all JSONL files and extract dates
        jsonl_files = sorted(symbol_dir.glob("*.jsonl"))

        if not jsonl_files:
            return (None, None)

        # Extract dates from filenames (YYYYMMDD.jsonl)
        dates = [f.stem for f in jsonl_files]

        return (dates[0], dates[-1])

    def count_records(self, asset_class: str, symbol: str, date_str: Optional[str] = None) -> int:
        """
        Count number of records for a symbol on a specific date.

        Args:
            asset_class: Asset class
            symbol: Trading symbol
            date_str: Date in YYYYMMDD format (defaults to today)

        Returns:
            int: Number of records, 0 if file doesn't exist

        Example:
            >>> count = writer.count_records("stocks", "AAPL:US", "20240115")
            >>> print(f"Found {count} records")
            Found 24 records
        """
        if date_str is None:
            date_str = datetime.utcnow().strftime("%Y%m%d")

        safe_symbol = symbol.replace(":", "_").replace("/", "_")
        file_path = self.base_dir / asset_class / safe_symbol / f"{date_str}.jsonl"

        if not file_path.exists():
            return 0

        try:
            count = 0
            with open(file_path, mode="rb") as f:
                for line in f:
                    if line.strip():
                        count += 1
            return count
        except Exception as e:
            print(f"Error counting records in {file_path}: {e}")
            return 0

    def __repr__(self) -> str:
        """Developer-friendly representation."""
        return f"JSONWriter(base_dir={self.base_dir})"
