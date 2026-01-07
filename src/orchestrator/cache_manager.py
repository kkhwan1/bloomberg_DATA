"""
Cache management for Bloomberg Data Crawler.

SQLite-based caching system with automatic expiration, statistics tracking,
and efficient data retrieval for reducing API calls.
"""

import json
import logging
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from src.config import CacheConfig
from src.utils.exceptions import CacheError

logger = logging.getLogger(__name__)


class CacheManager:
    """
    SQLite-based cache manager with TTL and statistics tracking.

    Features:
    - 15-minute TTL for cached data
    - Automatic expiration cleanup
    - Cache hit/miss statistics
    - Thread-safe operations
    - Efficient key-based lookups

    Attributes:
        db_path: Path to SQLite database file
        ttl_seconds: Time-to-live for cache entries
        _connection: Active database connection (None if closed)
    """

    def __init__(
        self,
        db_path: Optional[Path] = None,
        ttl_seconds: Optional[int] = None
    ):
        """
        Initialize cache manager.

        Args:
            db_path: Path to SQLite database (defaults to CacheConfig.DB_PATH)
            ttl_seconds: Cache TTL in seconds (defaults to CacheConfig.TTL_SECONDS)
        """
        self.db_path = db_path or CacheConfig.DB_PATH
        self.ttl_seconds = ttl_seconds or CacheConfig.TTL_SECONDS
        self._connection: Optional[sqlite3.Connection] = None

        # Ensure parent directory exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Initialize database schema
        self._initialize_database()

        logger.info(
            f"CacheManager initialized: db={self.db_path}, ttl={self.ttl_seconds}s"
        )

    def _initialize_database(self) -> None:
        """Create database schema if it doesn't exist."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            # Create cache table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS cache (
                    cache_key TEXT PRIMARY KEY,
                    asset_class TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    data TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    hit_count INTEGER DEFAULT 0,
                    last_accessed TEXT
                )
            """)

            # Create indexes for efficient queries
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_asset_symbol
                ON cache(asset_class, symbol)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_expires_at
                ON cache(expires_at)
            """)

            logger.debug("Database schema initialized successfully")

        except sqlite3.Error as e:
            raise CacheError(
                f"Failed to initialize database: {e}",
                operation="initialize",
                db_path=str(self.db_path)
            )

    def _get_connection(self) -> sqlite3.Connection:
        """
        Get database connection with proper configuration.

        Returns:
            Configured SQLite connection
        """
        if self._connection is None:
            self._connection = sqlite3.connect(
                str(self.db_path),
                check_same_thread=False,  # Allow multi-threaded access
                isolation_level=None  # Autocommit mode for better concurrency
            )
            # Enable row factory for dict-like access
            self._connection.row_factory = sqlite3.Row

        return self._connection

    def _make_cache_key(self, asset_class: str, symbol: str) -> str:
        """
        Generate standardized cache key.

        Args:
            asset_class: Asset class (stocks, bonds, commodities, etc.)
            symbol: Asset symbol (AAPL, MSFT, etc.)

        Returns:
            Formatted cache key (e.g., "stocks:AAPL")
        """
        return f"{asset_class.lower()}:{symbol.upper()}"

    def get(self, asset_class: str, symbol: str) -> Optional[dict]:
        """
        Retrieve data from cache if valid.

        Args:
            asset_class: Asset class identifier
            symbol: Asset symbol

        Returns:
            Cached data dict if found and not expired, None otherwise

        Raises:
            CacheError: If cache read operation fails
        """
        cache_key = self._make_cache_key(asset_class, symbol)

        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            now = datetime.now(timezone.utc).isoformat()

            # Query for valid (non-expired) cache entry
            cursor.execute("""
                SELECT data, hit_count
                FROM cache
                WHERE cache_key = ?
                AND expires_at > ?
            """, (cache_key, now))

            row = cursor.fetchone()

            if row is None:
                logger.debug(f"Cache miss: {cache_key}")
                return None

            # Update hit statistics
            cursor.execute("""
                UPDATE cache
                SET hit_count = hit_count + 1,
                    last_accessed = ?
                WHERE cache_key = ?
            """, (now, cache_key))

            # Parse JSON data
            data = json.loads(row['data'])
            logger.debug(
                f"Cache hit: {cache_key} (hits={row['hit_count'] + 1})"
            )

            return data

        except (sqlite3.Error, json.JSONDecodeError) as e:
            raise CacheError(
                f"Failed to read from cache: {e}",
                operation="read",
                cache_key=cache_key
            )

    def set(self, asset_class: str, symbol: str, data: dict) -> bool:
        """
        Store data in cache with TTL.

        Args:
            asset_class: Asset class identifier
            symbol: Asset symbol
            data: Data dictionary to cache

        Returns:
            True if successfully cached, False otherwise

        Raises:
            CacheError: If cache write operation fails
        """
        cache_key = self._make_cache_key(asset_class, symbol)

        try:
            # Calculate timestamps
            created_at = datetime.now(timezone.utc)
            expires_at = created_at + timedelta(seconds=self.ttl_seconds)

            # Serialize data to JSON
            data_json = json.dumps(data, ensure_ascii=False)

            conn = self._get_connection()
            cursor = conn.cursor()

            # Insert or replace cache entry
            cursor.execute("""
                INSERT OR REPLACE INTO cache (
                    cache_key, asset_class, symbol, data,
                    created_at, expires_at, hit_count, last_accessed
                ) VALUES (?, ?, ?, ?, ?, ?, 0, NULL)
            """, (
                cache_key,
                asset_class.lower(),
                symbol.upper(),
                data_json,
                created_at.isoformat(),
                expires_at.isoformat()
            ))

            logger.debug(
                f"Cached: {cache_key} (expires: {expires_at.isoformat()})"
            )
            return True

        except (sqlite3.Error, json.JSONEncodeError, TypeError) as e:
            raise CacheError(
                f"Failed to write to cache: {e}",
                operation="write",
                cache_key=cache_key
            )

    def invalidate(self, asset_class: str, symbol: str) -> bool:
        """
        Invalidate (delete) specific cache entry.

        Args:
            asset_class: Asset class identifier
            symbol: Asset symbol

        Returns:
            True if entry was deleted, False if not found

        Raises:
            CacheError: If cache delete operation fails
        """
        cache_key = self._make_cache_key(asset_class, symbol)

        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                DELETE FROM cache
                WHERE cache_key = ?
            """, (cache_key,))

            deleted_count = cursor.rowcount

            if deleted_count > 0:
                logger.info(f"Invalidated cache: {cache_key}")
                return True
            else:
                logger.debug(f"Cache entry not found: {cache_key}")
                return False

        except sqlite3.Error as e:
            raise CacheError(
                f"Failed to invalidate cache: {e}",
                operation="delete",
                cache_key=cache_key
            )

    def clear_expired(self) -> int:
        """
        Remove all expired cache entries.

        Returns:
            Number of entries removed

        Raises:
            CacheError: If cleanup operation fails
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            now = datetime.now(timezone.utc).isoformat()

            cursor.execute("""
                DELETE FROM cache
                WHERE expires_at <= ?
            """, (now,))

            deleted_count = cursor.rowcount

            if deleted_count > 0:
                logger.info(f"Cleared {deleted_count} expired cache entries")
            else:
                logger.debug("No expired cache entries to clear")

            return deleted_count

        except sqlite3.Error as e:
            raise CacheError(
                f"Failed to clear expired entries: {e}",
                operation="clear_expired"
            )

    def get_statistics(self) -> dict:
        """
        Get comprehensive cache statistics.

        Returns:
            Dictionary containing:
            - total_entries: Total number of cache entries
            - expired_entries: Number of expired entries
            - valid_entries: Number of valid (non-expired) entries
            - total_hits: Sum of all hit counts
            - average_hits: Average hits per entry
            - most_accessed: List of top 5 most accessed entries
            - cache_size_bytes: Approximate database size
            - ttl_seconds: Configured TTL

        Raises:
            CacheError: If statistics query fails
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            now = datetime.now(timezone.utc).isoformat()

            # Get total entries
            cursor.execute("SELECT COUNT(*) as count FROM cache")
            total_entries = cursor.fetchone()['count']

            # Get expired entries count
            cursor.execute("""
                SELECT COUNT(*) as count FROM cache
                WHERE expires_at <= ?
            """, (now,))
            expired_entries = cursor.fetchone()['count']

            # Get hit statistics
            cursor.execute("""
                SELECT
                    SUM(hit_count) as total_hits,
                    AVG(hit_count) as avg_hits
                FROM cache
            """)
            hit_stats = cursor.fetchone()
            total_hits = hit_stats['total_hits'] or 0
            avg_hits = round(hit_stats['avg_hits'] or 0.0, 2)

            # Get most accessed entries
            cursor.execute("""
                SELECT cache_key, hit_count, last_accessed
                FROM cache
                WHERE expires_at > ?
                ORDER BY hit_count DESC
                LIMIT 5
            """, (now,))

            most_accessed = [
                {
                    'cache_key': row['cache_key'],
                    'hit_count': row['hit_count'],
                    'last_accessed': row['last_accessed']
                }
                for row in cursor.fetchall()
            ]

            # Get database file size
            cache_size_bytes = self.db_path.stat().st_size if self.db_path.exists() else 0

            return {
                'total_entries': total_entries,
                'expired_entries': expired_entries,
                'valid_entries': total_entries - expired_entries,
                'total_hits': total_hits,
                'average_hits': avg_hits,
                'most_accessed': most_accessed,
                'cache_size_bytes': cache_size_bytes,
                'cache_size_mb': round(cache_size_bytes / (1024 * 1024), 2),
                'ttl_seconds': self.ttl_seconds,
                'db_path': str(self.db_path)
            }

        except sqlite3.Error as e:
            raise CacheError(
                f"Failed to retrieve statistics: {e}",
                operation="statistics"
            )

    def clear_all(self, confirm: bool = True) -> int:
        """
        Delete all cache entries (use with caution).

        Args:
            confirm: Safety flag requiring explicit confirmation

        Returns:
            Number of entries deleted

        Raises:
            CacheError: If clear operation fails or not confirmed
        """
        if not confirm:
            raise CacheError(
                "clear_all requires explicit confirmation (confirm=True)",
                operation="clear_all"
            )

        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            # Get count before deletion
            cursor.execute("SELECT COUNT(*) as count FROM cache")
            total_entries = cursor.fetchone()['count']

            # Delete all entries
            cursor.execute("DELETE FROM cache")

            # Vacuum to reclaim space
            cursor.execute("VACUUM")

            logger.warning(f"Cleared ALL {total_entries} cache entries")
            return total_entries

        except sqlite3.Error as e:
            raise CacheError(
                f"Failed to clear all cache entries: {e}",
                operation="clear_all"
            )

    def close(self) -> None:
        """Close database connection gracefully."""
        if self._connection:
            try:
                self._connection.close()
                self._connection = None
                logger.debug("Cache database connection closed")
            except sqlite3.Error as e:
                logger.error(f"Error closing database connection: {e}")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit with cleanup."""
        self.close()

    def __del__(self):
        """Cleanup on object destruction."""
        self.close()

    def __repr__(self) -> str:
        """String representation for debugging."""
        return (
            f"CacheManager(db_path={self.db_path}, "
            f"ttl_seconds={self.ttl_seconds})"
        )
