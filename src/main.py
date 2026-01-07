"""
Bloomberg Data Crawler - CLI Entry Point.

Command-line interface for managing automated Bloomberg market data collection
with budget tracking, scheduling, and cost optimization.

Usage:
    # Basic execution (15-minute interval scheduling)
    python -m src.main AAPL MSFT GOOGL

    # One-time execution
    python -m src.main AAPL --once

    # Asset class specification
    python -m src.main AAPL MSFT --asset-class stocks
    python -m src.main EURUSD GBPUSD --asset-class forex

    # Custom interval
    python -m src.main AAPL --interval 30

    # Status and budget monitoring
    python -m src.main --status
    python -m src.main --budget

Example:
    >>> python -m src.main AAPL:US MSFT:US GOOGL:US --interval 15
    [2026-01-07 14:30:00] INFO - Starting Bloomberg Data Crawler
    [2026-01-07 14:30:00] INFO - Tracking 3 symbols with 15-minute interval
    [2026-01-07 14:30:01] INFO - Scheduler started successfully
    Press Ctrl+C to stop gracefully...
"""

import argparse
import asyncio
import signal
import sys
from datetime import datetime
from typing import Dict, List, NoReturn

from src.config import AppConfig, BrightDataConfig
from src.normalizer.schemas import AssetClass
from src.orchestrator.scheduler import DataScheduler
from src.orchestrator.hybrid_source import HybridDataSource
from src.orchestrator.cost_tracker import CostTracker
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class BloombergCrawlerCLI:
    """
    Command-line interface for Bloomberg Data Crawler.

    Features:
        - Symbol management with asset class support
        - Scheduled data collection (default: 15-minute intervals)
        - One-time execution mode
        - Budget monitoring and status reporting
        - Graceful shutdown handling
    """

    def __init__(self):
        """Initialize CLI with argument parser and signal handlers."""
        self.parser = self._create_parser()
        self.scheduler = None
        self.args = None

        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _create_parser(self) -> argparse.ArgumentParser:
        """
        Create and configure argument parser.

        Returns:
            Configured ArgumentParser instance
        """
        parser = argparse.ArgumentParser(
            prog="Bloomberg Data Crawler",
            description=(
                "Automated Bloomberg market data collection with cost optimization "
                "and budget management."
            ),
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
Examples:
  # Track stocks with default 15-minute interval
  python -m src.main AAPL MSFT GOOGL

  # One-time data fetch
  python -m src.main AAPL --once

  # Forex pairs with custom interval
  python -m src.main EURUSD GBPUSD --asset-class forex --interval 30

  # Check system status
  python -m src.main --status

  # View budget usage
  python -m src.main --budget

Configuration:
  Set environment variables in .env file:
    - BRIGHT_DATA_TOKEN: Bright Data API token (required)
    - TOTAL_BUDGET: Maximum spending in USD (default: 5.50)
    - UPDATE_INTERVAL_SECONDS: Collection interval (default: 900)
            """,
        )

        # Positional arguments
        parser.add_argument(
            "symbols",
            nargs="*",
            help="Trading symbols to track (e.g., AAPL MSFT GOOGL:US)",
            metavar="SYMBOL",
        )

        # Asset class
        parser.add_argument(
            "--asset-class",
            type=str,
            choices=["stocks", "equity", "forex", "currency", "commodities", "index", "crypto"],
            default="stocks",
            help="Asset class for all symbols (default: stocks)",
        )

        # Execution mode
        mode_group = parser.add_mutually_exclusive_group()
        mode_group.add_argument(
            "--once",
            action="store_true",
            help="Run once and exit (no scheduling)",
        )
        mode_group.add_argument(
            "--interval",
            type=int,
            default=15,
            metavar="MINUTES",
            help="Update interval in minutes (default: 15)",
        )

        # Status commands
        status_group = parser.add_mutually_exclusive_group()
        status_group.add_argument(
            "--status",
            action="store_true",
            help="Display scheduler status and statistics",
        )
        status_group.add_argument(
            "--budget",
            action="store_true",
            help="Display budget usage and cost statistics",
        )

        # Advanced options
        parser.add_argument(
            "--force-fresh",
            action="store_true",
            help="Skip cache and force fresh data retrieval",
        )
        parser.add_argument(
            "--log-level",
            type=str,
            choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
            help="Override default log level",
        )
        parser.add_argument(
            "--version",
            action="version",
            version=f"%(prog)s {AppConfig.VERSION}",
        )

        return parser

    def _parse_asset_class(self, asset_class_str: str) -> AssetClass:
        """
        Convert string asset class to AssetClass enum.

        Args:
            asset_class_str: Asset class string from CLI

        Returns:
            AssetClass enum value
        """
        mapping = {
            "stocks": AssetClass.STOCKS,
            "equity": AssetClass.STOCKS,
            "forex": AssetClass.FOREX,
            "currency": AssetClass.FOREX,
            "commodities": AssetClass.COMMODITIES,
            "index": AssetClass.INDICES,
            "indices": AssetClass.INDICES,
            "crypto": AssetClass.CRYPTO,
            "bonds": AssetClass.BONDS,
            "etf": AssetClass.ETF,
        }
        return mapping.get(asset_class_str.lower(), AssetClass.STOCKS)

    def _validate_configuration(self) -> None:
        """
        Validate application configuration.

        Raises:
            SystemExit: If configuration is invalid
        """
        is_valid, errors = AppConfig.validate()

        if not is_valid:
            logger.error("Configuration validation failed:")
            for error in errors:
                logger.error(f"  - {error}")

            print("\n❌ Configuration Error\n", file=sys.stderr)
            print("Please fix the following issues:\n", file=sys.stderr)
            for error in errors:
                print(f"  • {error}", file=sys.stderr)

            print("\nCreate a .env file with required settings:", file=sys.stderr)
            print("  BRIGHT_DATA_TOKEN=your_token_here", file=sys.stderr)
            print("  TOTAL_BUDGET=5.50", file=sys.stderr)

            sys.exit(1)

        logger.info("Configuration validated successfully")

    def _display_budget_status(self) -> None:
        """Display comprehensive budget usage statistics."""
        tracker = CostTracker()
        stats = tracker.get_statistics()
        alert = tracker.get_alert_status()

        # Header
        print("\n" + "=" * 70)
        print("  BUDGET STATUS REPORT")
        print("=" * 70)

        # Budget overview
        print(f"\n📊 Budget Overview:")
        print(f"  Total Budget:        ${stats['budget_limit']:.2f}")
        print(f"  Spent:               ${stats['total_cost']:.4f}")
        print(f"  Remaining:           ${stats['budget_remaining']:.4f}")
        print(f"  Usage:               {stats['budget_used_pct']:.1f}%")

        # Alert level with color
        alert_symbols = {
            "ok": "✅",
            "warning": "⚠️",
            "critical": "🔶",
            "danger": "🚨",
        }
        symbol = alert_symbols.get(alert["alert_level"], "❓")
        print(f"  Alert Level:         {symbol} {alert['alert_level'].upper()}")

        # Request statistics
        print(f"\n📈 Request Statistics:")
        print(f"  Total Requests:      {stats['total_requests']}")
        print(f"  Successful:          {stats['successful_requests']} ({stats['success_rate_pct']:.1f}%)")
        print(f"  Failed:              {stats['failed_requests']}")
        print(f"  Remaining Requests:  {alert['requests_remaining']}")

        # Daily averages
        print(f"\n📅 Daily Averages:")
        print(f"  Days Tracked:        {stats['days_elapsed']}")
        print(f"  Avg Requests/Day:    {stats['daily_average_requests']:.1f}")
        print(f"  Avg Cost/Day:        ${stats['daily_average_cost']:.4f}")

        # Prediction
        if stats['prediction']['days_until_exhaustion']:
            print(f"\n🔮 Prediction:")
            print(f"  Days Until Exhaustion:   {stats['prediction']['days_until_exhaustion']:.1f}")
            print(f"  Estimated Exhaustion:    {stats['prediction']['estimated_exhaustion_date']}")
        else:
            print(f"\n🔮 Prediction:")
            print(f"  Budget exhaustion:       Not predicted (low usage)")

        # Recommendation
        print(f"\n💡 Recommendation:")
        print(f"  {alert['recommendation']}")

        print("\n" + "=" * 70 + "\n")

    def _display_scheduler_status(self) -> None:
        """Display scheduler status and statistics."""
        if not self.scheduler or not self.scheduler.is_running():
            print("\n❌ Scheduler is not running\n")
            return

        stats = self.scheduler.get_statistics()

        # Header
        print("\n" + "=" * 70)
        print("  SCHEDULER STATUS REPORT")
        print("=" * 70)

        # Scheduler state
        state = stats["scheduler_state"]
        print(f"\n📍 Scheduler State:")
        print(f"  Status:              {'🟢 RUNNING' if state['is_running'] else '🔴 STOPPED'}")
        print(f"  Symbols Tracked:     {state['symbols_tracked']}")
        print(f"  Update Interval:     {state['update_interval_minutes']} minutes")
        print(f"  Total Collections:   {state['total_collections']}")

        # Collection metrics
        metrics = stats["collection_metrics"]
        print(f"\n📊 Collection Metrics:")
        print(f"  Total Collections:   {metrics['total_collections']}")
        print(f"  Successful:          {metrics['successful_collections']} ({metrics['success_rate_pct']:.1f}%)")
        print(f"  Failed:              {metrics['failed_collections']}")
        print(f"  Total Quotes:        {metrics['total_quotes_collected']}")

        # Last activity
        activity = stats["last_activity"]
        print(f"\n⏰ Last Activity:")
        if activity["last_collection"]:
            dt = datetime.fromisoformat(activity["last_collection"])
            print(f"  Last Collection:     {dt.strftime('%Y-%m-%d %H:%M:%S')}")
        if activity["last_budget_reset"]:
            dt = datetime.fromisoformat(activity["last_budget_reset"])
            print(f"  Last Budget Reset:   {dt.strftime('%Y-%m-%d %H:%M:%S')}")
        if activity["last_cache_cleanup"]:
            dt = datetime.fromisoformat(activity["last_cache_cleanup"])
            print(f"  Last Cache Cleanup:  {dt.strftime('%Y-%m-%d %H:%M:%S')}")

        # Scheduled jobs
        if stats["scheduled_jobs"]:
            print(f"\n📅 Scheduled Jobs:")
            for job in stats["scheduled_jobs"]:
                next_run = datetime.fromisoformat(job["next_run"]) if job["next_run"] else None
                next_run_str = next_run.strftime('%Y-%m-%d %H:%M:%S') if next_run else "N/A"
                print(f"  {job['name']:25} → {next_run_str}")

        # Data source statistics
        ds_stats = stats["data_source_statistics"]
        cache = ds_stats["cache_statistics"]
        print(f"\n💾 Data Source Statistics:")
        print(f"  Cache Hit Rate:      {cache['hit_rate_pct']:.1f}%")
        print(f"  Cache Entries:       {cache['entry_count']}")
        print(f"  Cache Size:          {cache['size_bytes'] / 1024:.1f} KB")

        print("\n" + "=" * 70 + "\n")

    async def _run_once(self, symbols: List[str], asset_class: AssetClass) -> None:
        """
        Execute one-time data collection without scheduling.

        Args:
            symbols: List of symbols to fetch
            asset_class: Asset classification
        """
        logger.info(f"One-time execution mode: fetching {len(symbols)} symbols")

        source = HybridDataSource()

        try:
            quotes = await source.get_quotes(symbols, asset_class)

            # Display results
            print("\n" + "=" * 70)
            print("  MARKET QUOTES")
            print("=" * 70 + "\n")

            if quotes:
                for quote in quotes:
                    print(f"  {quote.symbol:10} ${quote.price:>10.2f}  [{quote.source.value}]")
                print(f"\n  Successfully fetched {len(quotes)}/{len(symbols)} quotes\n")
            else:
                print("  ❌ No quotes retrieved\n")

            # Display cost summary
            tracker = CostTracker()
            stats = tracker.get_statistics()
            print(f"  Total Cost: ${stats['total_cost']:.4f} | Budget Remaining: ${stats['budget_remaining']:.4f}\n")
            print("=" * 70 + "\n")

        except Exception as e:
            logger.error(f"Error during one-time execution: {e}", exc_info=True)
            sys.exit(1)

        finally:
            await source.cleanup()

    def _run_scheduled(self, symbols: List[str], asset_classes: Dict[str, AssetClass]) -> None:
        """
        Run scheduled data collection.

        Args:
            symbols: List of symbols to track
            asset_classes: Mapping of symbol to AssetClass
        """
        logger.info(
            f"Starting scheduler: {len(symbols)} symbols, {self.args.interval}min interval"
        )

        self.scheduler = DataScheduler(
            symbols=symbols,
            asset_classes=asset_classes,
            update_interval_minutes=self.args.interval,
        )

        try:
            # Start scheduler
            self.scheduler.start()

            # Display startup info
            print("\n" + "=" * 70)
            print(f"  {AppConfig.APP_NAME} v{AppConfig.VERSION}")
            print("=" * 70)
            print(f"\n  📈 Tracking {len(symbols)} symbols:")
            for symbol in symbols:
                print(f"     • {symbol}")
            print(f"\n  ⏱️  Update interval: {self.args.interval} minutes")
            print(f"  💰 Budget: ${CostConfig.TOTAL_BUDGET:.2f}")
            print(f"\n  Press Ctrl+C to stop gracefully...\n")
            print("=" * 70 + "\n")

            # Keep running until interrupted
            while self.scheduler.is_running():
                signal.pause()  # Wait for signal

        except KeyboardInterrupt:
            logger.info("Received interrupt signal - shutting down gracefully")
            self._shutdown()

        except Exception as e:
            logger.error(f"Scheduler error: {e}", exc_info=True)
            self._shutdown()
            sys.exit(1)

    def _shutdown(self) -> None:
        """Graceful shutdown of scheduler and resources."""
        if self.scheduler and self.scheduler.is_running():
            print("\n\n🛑 Shutting down gracefully...\n")
            logger.info("Stopping scheduler...")

            self.scheduler.stop(wait=True)

            # Display final statistics
            stats = self.scheduler.get_statistics()
            print("=" * 70)
            print("  SHUTDOWN SUMMARY")
            print("=" * 70)
            print(f"\n  Total Collections:   {stats['collection_metrics']['total_collections']}")
            print(f"  Quotes Collected:    {stats['collection_metrics']['total_quotes_collected']}")
            print(f"  Success Rate:        {stats['collection_metrics']['success_rate_pct']:.1f}%")

            tracker = CostTracker()
            cost_stats = tracker.get_statistics()
            print(f"\n  Total Cost:          ${cost_stats['total_cost']:.4f}")
            print(f"  Budget Remaining:    ${cost_stats['budget_remaining']:.4f}")
            print("\n" + "=" * 70 + "\n")

            logger.info("Shutdown complete")

    def _signal_handler(self, signum: int, frame) -> None:
        """
        Handle interrupt signals for graceful shutdown.

        Args:
            signum: Signal number
            frame: Current stack frame
        """
        logger.info(f"Received signal {signum}")
        self._shutdown()
        sys.exit(0)

    def run(self) -> NoReturn:
        """
        Main entry point for CLI execution.

        Parses arguments, validates configuration, and executes requested command.
        """
        self.args = self.parser.parse_args()

        # Override log level if specified
        if self.args.log_level:
            import logging
            logging.getLogger().setLevel(getattr(logging, self.args.log_level))

        # Display banner
        print(f"\n{AppConfig.APP_NAME} v{AppConfig.VERSION}")
        print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

        # Validate configuration
        self._validate_configuration()

        # Handle status commands
        if self.args.budget:
            self._display_budget_status()
            sys.exit(0)

        if self.args.status:
            self._display_scheduler_status()
            sys.exit(0)

        # Validate symbols provided
        if not self.args.symbols:
            self.parser.error("No symbols provided. Use --help for usage information.")

        # Parse asset class
        asset_class = self._parse_asset_class(self.args.asset_class)

        # Create asset class mapping for all symbols
        symbols = self.args.symbols
        asset_classes = {symbol: asset_class for symbol in symbols}

        logger.info(
            f"Starting with {len(symbols)} symbols",
            extra={
                "symbols": symbols,
                "asset_class": asset_class.value,
                "mode": "once" if self.args.once else "scheduled",
            },
        )

        # Execute based on mode
        if self.args.once:
            asyncio.run(self._run_once(symbols, asset_class))
        else:
            self._run_scheduled(symbols, asset_classes)

        sys.exit(0)


def main() -> NoReturn:
    """
    Application entry point.

    Creates and runs CLI instance.
    """
    try:
        cli = BloombergCrawlerCLI()
        cli.run()
    except Exception as e:
        logger.critical(f"Fatal error: {e}", exc_info=True)
        print(f"\n❌ Fatal Error: {e}\n", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
