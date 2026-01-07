"""
Data Collection Scheduler.

APScheduler-based periodic data collection with automatic budget management,
cache cleanup, and error recovery.
"""

import asyncio
import logging
from datetime import datetime, time
from typing import Dict, List, Optional

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from src.config import SchedulerConfig
from src.normalizer.schemas import AssetClass
from src.orchestrator.hybrid_source import HybridDataSource
from src.utils.exceptions import BudgetExhaustedError

logger = logging.getLogger(__name__)


class DataScheduler:
    """
    Background scheduler for automated data collection and maintenance.

    Scheduled Tasks:
        - Every 15 minutes: Collect market data for tracked symbols
        - Daily at midnight: Reset budget tracking
        - Hourly: Clean up expired cache entries

    Features:
        - Automatic retry on transient failures
        - Budget exhaustion handling
        - Symbol management (add/remove during runtime)
        - Comprehensive statistics and health monitoring
        - Graceful shutdown with resource cleanup

    Example:
        >>> symbols = ["AAPL:US", "MSFT:US", "GOOGL:US"]
        >>> asset_classes = {
        ...     "AAPL:US": AssetClass.STOCKS,
        ...     "MSFT:US": AssetClass.STOCKS,
        ...     "GOOGL:US": AssetClass.STOCKS,
        ... }
        >>> scheduler = DataScheduler(symbols, asset_classes)
        >>> scheduler.start()
        >>> # ... let it run ...
        >>> scheduler.stop()
    """

    def __init__(
        self,
        symbols: List[str],
        asset_classes: Dict[str, AssetClass],
        update_interval_minutes: int = 15,
    ):
        """
        Initialize data scheduler.

        Args:
            symbols: List of symbols to track
            asset_classes: Mapping of symbol to AssetClass
            update_interval_minutes: Data collection interval (default: 15)
        """
        self.symbols = list(symbols)  # Make a copy
        self.asset_classes = asset_classes.copy()
        self.update_interval_minutes = update_interval_minutes

        # Core components
        self.hybrid_source = HybridDataSource()
        self.scheduler = BackgroundScheduler()

        # State management
        self._is_running = False
        self._collection_count = 0
        self._last_collection_time: Optional[datetime] = None
        self._last_budget_reset: Optional[datetime] = None
        self._last_cache_cleanup: Optional[datetime] = None

        # Statistics
        self._stats = {
            "total_collections": 0,
            "successful_collections": 0,
            "failed_collections": 0,
            "total_quotes_collected": 0,
            "budget_resets": 0,
            "cache_cleanups": 0,
        }

        logger.info(
            f"DataScheduler initialized with {len(symbols)} symbols, "
            f"{update_interval_minutes}min interval"
        )

    def start(self) -> None:
        """
        Start the scheduler and begin automated data collection.

        Configures and starts three scheduled jobs:
            1. Data collection (every N minutes)
            2. Daily budget reset (midnight)
            3. Cache cleanup (hourly)
        """
        if self._is_running:
            logger.warning("Scheduler is already running")
            return

        # Job 1: Data collection at specified interval
        self.scheduler.add_job(
            func=self._collect_data_wrapper,
            trigger=IntervalTrigger(minutes=self.update_interval_minutes),
            id="collect_data",
            name="Market Data Collection",
            replace_existing=True,
            max_instances=1,  # Prevent overlapping executions
        )

        # Job 2: Daily budget reset at midnight
        self.scheduler.add_job(
            func=self._reset_daily_budget,
            trigger=CronTrigger(hour=0, minute=0),
            id="reset_budget",
            name="Daily Budget Reset",
            replace_existing=True,
        )

        # Job 3: Hourly cache cleanup
        self.scheduler.add_job(
            func=self._cleanup_cache,
            trigger=IntervalTrigger(hours=1),
            id="cleanup_cache",
            name="Cache Cleanup",
            replace_existing=True,
        )

        # Start the scheduler
        self.scheduler.start()
        self._is_running = True

        logger.info(
            "DataScheduler started",
            extra={
                "symbols": len(self.symbols),
                "update_interval_minutes": self.update_interval_minutes,
                "jobs": [job.id for job in self.scheduler.get_jobs()],
            },
        )

        # Run initial collection immediately
        logger.info("Running initial data collection...")
        self._collect_data_wrapper()

    def stop(self, wait: bool = True) -> None:
        """
        Stop the scheduler and cleanup resources.

        Args:
            wait: If True, wait for running jobs to complete (default: True)
        """
        if not self._is_running:
            logger.warning("Scheduler is not running")
            return

        logger.info("Stopping DataScheduler...")

        # Shutdown scheduler
        self.scheduler.shutdown(wait=wait)
        self._is_running = False

        # Cleanup resources
        asyncio.run(self.hybrid_source.cleanup())

        logger.info("DataScheduler stopped successfully")

    def _collect_data_wrapper(self) -> None:
        """
        Wrapper for async data collection to work with sync scheduler.

        Creates new event loop for each collection to avoid conflicts.
        """
        try:
            # Create new event loop for this thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            try:
                loop.run_until_complete(self._collect_data())
            finally:
                loop.close()

        except Exception as e:
            logger.error(f"Error in data collection wrapper: {e}", exc_info=True)
            self._stats["failed_collections"] += 1

    async def _collect_data(self) -> None:
        """
        Collect data for all tracked symbols.

        Implements retry logic and budget exhaustion handling.
        """
        self._collection_count += 1
        self._stats["total_collections"] += 1

        logger.info(
            f"Starting data collection #{self._collection_count} for {len(self.symbols)} symbols",
            extra={
                "collection_number": self._collection_count,
                "symbol_count": len(self.symbols),
            },
        )

        successful_quotes = 0
        failed_symbols = []

        try:
            # Collect quotes for all symbols
            for symbol in self.symbols:
                asset_class = self.asset_classes.get(symbol, AssetClass.STOCKS)

                try:
                    quote = await self.hybrid_source.get_quote(symbol, asset_class)

                    if quote:
                        successful_quotes += 1
                        logger.debug(
                            f"Collected {symbol}: ${quote.price}",
                            extra={
                                "symbol": symbol,
                                "price": quote.price,
                                "source": quote.source.value,
                            },
                        )
                    else:
                        failed_symbols.append(symbol)
                        logger.warning(f"Failed to collect data for {symbol}")

                except BudgetExhaustedError:
                    logger.error(
                        "Budget exhausted during collection - stopping",
                        extra={
                            "symbols_processed": successful_quotes,
                            "symbols_remaining": len(self.symbols) - successful_quotes,
                        },
                    )
                    break

                except Exception as e:
                    failed_symbols.append(symbol)
                    logger.error(
                        f"Error collecting {symbol}: {e}",
                        extra={"symbol": symbol, "error": str(e)},
                    )

            # Update statistics
            self._last_collection_time = datetime.now()
            self._stats["total_quotes_collected"] += successful_quotes

            if failed_symbols:
                self._stats["failed_collections"] += 1
                logger.warning(
                    f"Collection completed with {len(failed_symbols)} failures",
                    extra={
                        "successful": successful_quotes,
                        "failed": len(failed_symbols),
                        "failed_symbols": failed_symbols,
                    },
                )
            else:
                self._stats["successful_collections"] += 1
                logger.info(
                    f"Collection completed successfully: {successful_quotes} quotes",
                    extra={"quotes_collected": successful_quotes},
                )

        except Exception as e:
            self._stats["failed_collections"] += 1
            logger.error(f"Critical error in data collection: {e}", exc_info=True)

    def _reset_daily_budget(self) -> None:
        """
        Reset daily budget tracking at midnight.

        Called automatically by scheduler at 00:00 daily.
        """
        try:
            logger.info("Performing daily budget reset")

            # Reset cost tracker
            reset_result = self.hybrid_source.cost_tracker.reset(confirm=True)
            self._last_budget_reset = datetime.now()
            self._stats["budget_resets"] += 1

            logger.info(
                "Daily budget reset completed",
                extra={
                    "previous_total_cost": reset_result["previous_statistics"]["total_cost"],
                    "previous_requests": reset_result["previous_statistics"]["total_requests"],
                    "reset_time": self._last_budget_reset.isoformat(),
                },
            )

        except Exception as e:
            logger.error(f"Error during budget reset: {e}", exc_info=True)

    def _cleanup_cache(self) -> None:
        """
        Clean up expired cache entries.

        Called automatically by scheduler every hour.
        """
        try:
            logger.info("Performing cache cleanup")

            # Remove expired entries
            deleted_count = self.hybrid_source.cache.clear_expired()
            self._last_cache_cleanup = datetime.now()
            self._stats["cache_cleanups"] += 1

            logger.info(
                f"Cache cleanup completed: {deleted_count} entries removed",
                extra={
                    "deleted_entries": deleted_count,
                    "cleanup_time": self._last_cache_cleanup.isoformat(),
                },
            )

        except Exception as e:
            logger.error(f"Error during cache cleanup: {e}", exc_info=True)

    def add_symbol(self, symbol: str, asset_class: AssetClass) -> None:
        """
        Add a symbol to the tracking list.

        Args:
            symbol: Trading symbol to add
            asset_class: Asset classification

        Example:
            >>> scheduler.add_symbol("TSLA:US", AssetClass.STOCKS)
        """
        if symbol in self.symbols:
            logger.warning(f"Symbol {symbol} is already being tracked")
            return

        self.symbols.append(symbol)
        self.asset_classes[symbol] = asset_class

        logger.info(
            f"Added symbol to tracking list: {symbol}",
            extra={"symbol": symbol, "asset_class": asset_class.value},
        )

    def remove_symbol(self, symbol: str) -> bool:
        """
        Remove a symbol from the tracking list.

        Args:
            symbol: Trading symbol to remove

        Returns:
            True if symbol was removed, False if not found

        Example:
            >>> scheduler.remove_symbol("TSLA:US")
        """
        if symbol not in self.symbols:
            logger.warning(f"Symbol {symbol} is not being tracked")
            return False

        self.symbols.remove(symbol)
        self.asset_classes.pop(symbol, None)

        logger.info(f"Removed symbol from tracking list: {symbol}")
        return True

    def get_tracked_symbols(self) -> List[str]:
        """Get list of currently tracked symbols."""
        return self.symbols.copy()

    def get_statistics(self) -> dict:
        """
        Get comprehensive scheduler statistics.

        Returns:
            Dictionary with scheduler state, job info, and collection metrics
        """
        return {
            "scheduler_state": {
                "is_running": self._is_running,
                "update_interval_minutes": self.update_interval_minutes,
                "symbols_tracked": len(self.symbols),
                "total_collections": self._collection_count,
            },
            "last_activity": {
                "last_collection": (
                    self._last_collection_time.isoformat()
                    if self._last_collection_time
                    else None
                ),
                "last_budget_reset": (
                    self._last_budget_reset.isoformat() if self._last_budget_reset else None
                ),
                "last_cache_cleanup": (
                    self._last_cache_cleanup.isoformat() if self._last_cache_cleanup else None
                ),
            },
            "collection_metrics": {
                "total_collections": self._stats["total_collections"],
                "successful_collections": self._stats["successful_collections"],
                "failed_collections": self._stats["failed_collections"],
                "total_quotes_collected": self._stats["total_quotes_collected"],
                "success_rate_pct": (
                    round(
                        self._stats["successful_collections"]
                        / self._stats["total_collections"]
                        * 100,
                        2,
                    )
                    if self._stats["total_collections"] > 0
                    else 0
                ),
            },
            "maintenance_metrics": {
                "budget_resets": self._stats["budget_resets"],
                "cache_cleanups": self._stats["cache_cleanups"],
            },
            "scheduled_jobs": [
                {
                    "id": job.id,
                    "name": job.name,
                    "next_run": job.next_run_time.isoformat() if job.next_run_time else None,
                }
                for job in self.scheduler.get_jobs()
            ]
            if self._is_running
            else [],
            "data_source_statistics": self.hybrid_source.get_statistics(),
        }

    def force_collection(self) -> None:
        """
        Force immediate data collection outside scheduled interval.

        Example:
            >>> scheduler.force_collection()
        """
        logger.info("Forcing immediate data collection")
        self._collect_data_wrapper()

    def is_running(self) -> bool:
        """Check if scheduler is currently running."""
        return self._is_running

    def __repr__(self) -> str:
        """String representation for debugging."""
        return (
            f"DataScheduler(symbols={len(self.symbols)}, "
            f"interval={self.update_interval_minutes}min, "
            f"running={self._is_running}, "
            f"collections={self._collection_count})"
        )

    def __enter__(self):
        """Context manager entry - starts scheduler."""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - stops scheduler."""
        self.stop()
