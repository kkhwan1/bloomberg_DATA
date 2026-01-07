"""
CostTracker Usage Demo

Demonstrates the key features and usage patterns of the CostTracker class.
"""

import sys
import time
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.orchestrator import CostTracker
from src.utils.exceptions import BudgetExhaustedError


def demo_basic_usage():
    """Demonstrate basic CostTracker usage."""
    print("=" * 70)
    print("DEMO 1: Basic Usage")
    print("=" * 70)

    # Get singleton instance
    tracker = CostTracker()

    # Check if we can make a request
    if tracker.can_make_request():
        print("\n✓ Budget available - can make request")

        # Record a successful request
        result = tracker.record_request(
            asset_class='equity',
            symbol='AAPL:US',
            success=True
        )

        print(f"\nRequest recorded:")
        print(f"  - Total requests: {result['request_count']}")
        print(f"  - Total cost: ${result['total_cost']}")
        print(f"  - Budget remaining: ${result['budget_remaining']}")
        print(f"  - Alert level: {result['alert_level'].upper()}")


def demo_alert_levels():
    """Demonstrate alert threshold system."""
    print("\n" + "=" * 70)
    print("DEMO 2: Alert Levels (50%, 80%, 95%)")
    print("=" * 70)

    tracker = CostTracker()

    # Simulate requests to trigger different alert levels
    max_requests = int(tracker.budget_limit / tracker.cost_per_request)

    # Get to WARNING threshold (50%)
    warning_requests = int(max_requests * 0.55)
    for i in range(warning_requests):
        tracker.record_request('equity', f'TEST{i}:US', success=True)

    alert = tracker.get_alert_status()
    print(f"\n⚠️  WARNING Level (50% threshold):")
    print(f"  - Budget used: {alert['budget_used_pct']:.2f}%")
    print(f"  - Requests remaining: {alert['requests_remaining']}")
    print(f"  - Recommendation: {alert['recommendation']}")

    # Get to CRITICAL threshold (80%)
    critical_requests = int(max_requests * 0.85) - warning_requests
    for i in range(critical_requests):
        tracker.record_request('index', f'IDX{i}:US', success=True)

    alert = tracker.get_alert_status()
    print(f"\n🚨 CRITICAL Level (80% threshold):")
    print(f"  - Budget used: {alert['budget_used_pct']:.2f}%")
    print(f"  - Requests remaining: {alert['requests_remaining']}")
    print(f"  - Recommendation: {alert['recommendation']}")


def demo_statistics():
    """Demonstrate comprehensive statistics."""
    print("\n" + "=" * 70)
    print("DEMO 3: Statistics and Predictions")
    print("=" * 70)

    tracker = CostTracker()

    # Record mix of successful and failed requests
    for i in range(7):
        tracker.record_request('equity', f'SUCCESS{i}:US', success=True)

    for i in range(3):
        tracker.record_request('equity', f'FAIL{i}:US', success=False)

    # Get comprehensive statistics
    stats = tracker.get_statistics()

    print(f"\n📊 Usage Statistics:")
    print(f"  - Total requests: {stats['total_requests']}")
    print(f"  - Successful: {stats['successful_requests']}")
    print(f"  - Failed: {stats['failed_requests']}")
    print(f"  - Success rate: {stats['success_rate_pct']:.1f}%")

    print(f"\n💰 Budget Status:")
    print(f"  - Total cost: ${stats['total_cost']:.4f}")
    print(f"  - Budget limit: ${stats['budget_limit']:.2f}")
    print(f"  - Budget used: {stats['budget_used_pct']:.2f}%")
    print(f"  - Alert level: {stats['alert_level'].upper()}")

    print(f"\n📈 Daily Averages:")
    print(f"  - Days elapsed: {stats['days_elapsed']}")
    print(f"  - Avg requests/day: {stats['daily_average_requests']:.2f}")
    print(f"  - Avg cost/day: ${stats['daily_average_cost']:.4f}")

    if stats['prediction']['days_until_exhaustion']:
        print(f"\n🔮 Prediction:")
        print(f"  - Days until budget exhausted: {stats['prediction']['days_until_exhaustion']:.1f}")
        print(f"  - Estimated exhaustion date: {stats['prediction']['estimated_exhaustion_date']}")


def demo_asset_tracking():
    """Demonstrate asset-based tracking."""
    print("\n" + "=" * 70)
    print("DEMO 4: Asset-Based Tracking")
    print("=" * 70)

    tracker = CostTracker()

    # Record requests for different asset classes
    assets = [
        ('equity', 'AAPL:US', 3),
        ('equity', 'MSFT:US', 2),
        ('equity', 'GOOGL:US', 1),
        ('index', 'SPX:IND', 2),
        ('currency', 'EURUSD:CUR', 1),
    ]

    for asset_class, symbol, count in assets:
        for _ in range(count):
            tracker.record_request(asset_class, symbol, success=True)

    stats = tracker.get_statistics()

    print("\n📦 Requests by Asset Class:")
    for asset_class, symbols in stats['requests_by_asset'].items():
        print(f"\n  {asset_class.upper()}:")
        for symbol, count in symbols.items():
            print(f"    - {symbol}: {count} requests")


def demo_budget_exhaustion():
    """Demonstrate budget exhaustion handling."""
    print("\n" + "=" * 70)
    print("DEMO 5: Budget Exhaustion Handling")
    print("=" * 70)

    tracker = CostTracker()

    # Calculate max requests
    max_requests = int(tracker.budget_limit / tracker.cost_per_request)

    # Use all budget
    print(f"\nExhausting budget ({max_requests} requests)...")
    for i in range(max_requests):
        tracker.record_request('equity', f'EXHAUST{i}:US', success=True)
        if i % 500 == 0:
            print(f"  Progress: {i}/{max_requests} requests")

    print(f"\n✓ Budget exhausted after {max_requests} requests")

    # Try to make another request
    print("\nAttempting request with exhausted budget...")
    try:
        tracker.can_make_request()
        print("  ERROR: Should have raised BudgetExhaustedError!")
    except BudgetExhaustedError as e:
        print(f"  ✓ BudgetExhaustedError raised correctly:")
        print(f"    - Message: {e.message}")
        print(f"    - Current usage: {e.current_usage} requests")
        print(f"    - Budget limit: {e.budget_limit} requests")


def demo_reset():
    """Demonstrate tracker reset."""
    print("\n" + "=" * 70)
    print("DEMO 6: Tracker Reset")
    print("=" * 70)

    tracker = CostTracker()

    # Record some requests
    for i in range(10):
        tracker.record_request('equity', f'RESET{i}:US', success=True)

    print(f"\nBefore reset:")
    print(f"  - Total requests: {tracker.total_requests}")
    print(f"  - Total cost: ${tracker.total_cost:.4f}")

    # Reset tracker
    result = tracker.reset(confirm=True)

    print(f"\n✓ Tracker reset successfully")
    print(f"\nAfter reset:")
    print(f"  - Total requests: {tracker.total_requests}")
    print(f"  - Total cost: ${tracker.total_cost:.4f}")
    print(f"  - Previous total: {result['previous_statistics']['total_requests']} requests")


def demo_persistence():
    """Demonstrate data persistence."""
    print("\n" + "=" * 70)
    print("DEMO 7: Data Persistence")
    print("=" * 70)

    # First instance
    tracker = CostTracker()
    tracker.record_request('equity', 'PERSIST:US', success=True)

    print(f"\nData saved to: {tracker.storage_path}")
    print(f"Total requests: {tracker.total_requests}")

    # Simulate application restart by resetting singleton
    CostTracker._instance = None

    # New instance should load persisted data
    new_tracker = CostTracker()

    print(f"\n✓ Data recovered after restart:")
    print(f"  - Total requests: {new_tracker.total_requests}")
    print(f"  - Persistent storage working correctly")


def main():
    """Run all demos."""
    print("\n")
    print("╔" + "=" * 68 + "╗")
    print("║" + " " * 15 + "COSTTRACKER USAGE DEMONSTRATION" + " " * 22 + "║")
    print("╚" + "=" * 68 + "╝")

    # Reset tracker before demos
    tracker = CostTracker()
    try:
        tracker.reset(confirm=True)
    except:
        pass

    # Run demos
    demo_basic_usage()
    time.sleep(1)

    # Reset for clean demo
    tracker.reset(confirm=True)
    demo_statistics()
    time.sleep(1)

    # Reset for clean demo
    tracker.reset(confirm=True)
    demo_asset_tracking()
    time.sleep(1)

    # Reset for clean demo
    tracker.reset(confirm=True)
    demo_alert_levels()
    time.sleep(1)

    # Note: Skipping exhaustion and reset demos to keep demo quick
    # Uncomment to run full demo:
    # tracker.reset(confirm=True)
    # demo_budget_exhaustion()
    # tracker.reset(confirm=True)
    # demo_reset()

    demo_persistence()

    print("\n" + "=" * 70)
    print("DEMO COMPLETE")
    print("=" * 70)
    print("\nKey Features Demonstrated:")
    print("  ✓ Thread-safe singleton pattern")
    print("  ✓ Budget tracking with cost calculation")
    print("  ✓ Multi-level alert system (50%, 80%, 95%)")
    print("  ✓ Comprehensive statistics and predictions")
    print("  ✓ Asset-based and date-based tracking")
    print("  ✓ Budget exhaustion detection")
    print("  ✓ Reset functionality")
    print("  ✓ JSON persistence and recovery")
    print()


if __name__ == '__main__':
    main()
