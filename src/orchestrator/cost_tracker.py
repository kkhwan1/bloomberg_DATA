"""
Cost Tracker for Bloomberg Data Crawler.

Thread-safe singleton implementation for tracking API request costs,
managing budgets, and providing usage statistics with persistent storage.
"""

import json
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from src.config import CostConfig, LoggingConfig
from src.utils.exceptions import BudgetExhaustedError


class CostTracker:
    """
    Thread-safe singleton cost tracker for managing API request budgets.

    Features:
        - Singleton pattern with thread-safe initialization
        - Budget tracking with configurable thresholds (50%, 80%, 95%)
        - Persistent storage in JSON format
        - Date-based and asset-based request tracking
        - Budget exhaustion prediction based on daily averages
        - Real-time cost calculation and validation

    Attributes:
        _instance: Singleton instance
        _lock: Thread lock for singleton initialization
        _request_lock: Thread lock for request recording
        budget_limit: Maximum allowed spending (USD)
        cost_per_request: Cost of each API request (USD)
        storage_path: Path to JSON persistence file

    Alert Thresholds:
        - 50%: WARNING - Budget half consumed
        - 80%: CRITICAL - Budget mostly consumed
        - 95%: DANGER - Budget nearly exhausted
    """

    _instance: Optional['CostTracker'] = None
    _lock: threading.Lock = threading.Lock()

    def __new__(cls):
        """Thread-safe singleton implementation."""
        if cls._instance is None:
            with cls._lock:
                # Double-check locking pattern
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize cost tracker with configuration and load persisted data."""
        # Prevent re-initialization
        if hasattr(self, '_initialized'):
            return

        self._initialized = True
        self._request_lock = threading.Lock()

        # Budget configuration
        self.budget_limit = CostConfig.TOTAL_BUDGET
        self.cost_per_request = CostConfig.COST_PER_REQUEST

        # Alert thresholds
        self.warning_threshold = 0.50  # 50%
        self.critical_threshold = 0.80  # 80%
        self.danger_threshold = 0.95   # 95%

        # Storage configuration
        LoggingConfig.ensure_log_directory()
        self.storage_path = LoggingConfig.LOG_DIR / "cost_tracking.json"

        # In-memory tracking data
        self.total_requests = 0
        self.total_cost = 0.0
        self.successful_requests = 0
        self.failed_requests = 0
        self.start_date = datetime.now().isoformat()

        # Detailed tracking
        self.requests_by_date: dict[str, int] = {}
        self.requests_by_asset: dict[str, dict[str, int]] = {}
        self.daily_costs: dict[str, float] = {}

        # Load persisted data
        self._load_data()

    def _load_data(self) -> None:
        """Load tracking data from JSON file."""
        if not self.storage_path.exists():
            return

        try:
            with open(self.storage_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            self.total_requests = data.get('total_requests', 0)
            self.total_cost = data.get('total_cost', 0.0)
            self.successful_requests = data.get('successful_requests', 0)
            self.failed_requests = data.get('failed_requests', 0)
            self.start_date = data.get('start_date', datetime.now().isoformat())
            self.requests_by_date = data.get('requests_by_date', {})
            self.requests_by_asset = data.get('requests_by_asset', {})
            self.daily_costs = data.get('daily_costs', {})

        except (json.JSONDecodeError, IOError) as e:
            # If load fails, start fresh but log the error
            print(f"Warning: Could not load cost tracking data: {e}")

    def _save_data(self) -> None:
        """Persist tracking data to JSON file."""
        data = {
            'total_requests': self.total_requests,
            'total_cost': self.total_cost,
            'successful_requests': self.successful_requests,
            'failed_requests': self.failed_requests,
            'start_date': self.start_date,
            'requests_by_date': self.requests_by_date,
            'requests_by_asset': self.requests_by_asset,
            'daily_costs': self.daily_costs,
            'budget_limit': self.budget_limit,
            'cost_per_request': self.cost_per_request,
            'last_updated': datetime.now().isoformat()
        }

        try:
            with open(self.storage_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except IOError as e:
            print(f"Warning: Could not save cost tracking data: {e}")

    def can_make_request(self) -> bool:
        """
        Check if a new request can be made within budget.

        Returns:
            True if request can be made, False if budget exhausted

        Raises:
            BudgetExhaustedError: If budget is completely exhausted
        """
        projected_cost = self.total_cost + self.cost_per_request

        if projected_cost > self.budget_limit:
            raise BudgetExhaustedError(
                message="Budget exhausted - cannot make more requests",
                current_usage=self.total_requests,
                budget_limit=int(self.budget_limit / self.cost_per_request),
                reset_time="Manual reset required"
            )

        return True

    def record_request(
        self,
        asset_class: str,
        symbol: str,
        success: bool = True
    ) -> dict:
        """
        Record an API request and update all tracking metrics.

        Args:
            asset_class: Type of asset (e.g., 'equity', 'index', 'currency')
            symbol: Asset symbol (e.g., 'AAPL:US')
            success: Whether the request succeeded

        Returns:
            Dictionary with updated statistics and alert information

        Example:
            >>> tracker = CostTracker()
            >>> result = tracker.record_request('equity', 'AAPL:US', success=True)
            >>> print(result['alert_level'])
            'ok'
        """
        with self._request_lock:
            # Update counters
            self.total_requests += 1
            self.total_cost += self.cost_per_request

            if success:
                self.successful_requests += 1
            else:
                self.failed_requests += 1

            # Update date-based tracking
            today = datetime.now().strftime('%Y-%m-%d')
            self.requests_by_date[today] = self.requests_by_date.get(today, 0) + 1
            self.daily_costs[today] = self.daily_costs.get(today, 0.0) + self.cost_per_request

            # Update asset-based tracking
            if asset_class not in self.requests_by_asset:
                self.requests_by_asset[asset_class] = {}

            asset_data = self.requests_by_asset[asset_class]
            asset_data[symbol] = asset_data.get(symbol, 0) + 1

            # Calculate alert level
            usage_ratio = self.total_cost / self.budget_limit
            alert_level = self._get_alert_level(usage_ratio)

            # Persist data
            self._save_data()

            # Return statistics
            return {
                'request_count': self.total_requests,
                'total_cost': round(self.total_cost, 4),
                'budget_remaining': round(self.budget_limit - self.total_cost, 4),
                'budget_used_pct': round(usage_ratio * 100, 2),
                'alert_level': alert_level,
                'success': success,
                'asset_class': asset_class,
                'symbol': symbol,
                'timestamp': datetime.now().isoformat()
            }

    def _get_alert_level(self, usage_ratio: float) -> str:
        """
        Determine alert level based on budget usage.

        Args:
            usage_ratio: Ratio of used budget (0.0 to 1.0)

        Returns:
            Alert level: 'ok', 'warning', 'critical', or 'danger'
        """
        if usage_ratio >= self.danger_threshold:
            return 'danger'
        elif usage_ratio >= self.critical_threshold:
            return 'critical'
        elif usage_ratio >= self.warning_threshold:
            return 'warning'
        else:
            return 'ok'

    def get_statistics(self) -> dict:
        """
        Get comprehensive usage statistics and predictions.

        Returns:
            Dictionary containing:
                - Current usage metrics
                - Budget status and alerts
                - Date-based breakdown
                - Asset-based breakdown
                - Budget exhaustion prediction

        Example:
            >>> tracker = CostTracker()
            >>> stats = tracker.get_statistics()
            >>> print(f"Budget used: {stats['budget_used_pct']}%")
            >>> print(f"Days until exhaustion: {stats['prediction']['days_until_exhaustion']}")
        """
        usage_ratio = self.total_cost / self.budget_limit if self.budget_limit > 0 else 0

        # Calculate daily average
        start = datetime.fromisoformat(self.start_date)
        days_elapsed = max(1, (datetime.now() - start).days + 1)
        daily_average_cost = self.total_cost / days_elapsed
        daily_average_requests = self.total_requests / days_elapsed

        # Predict budget exhaustion
        remaining_budget = self.budget_limit - self.total_cost
        if daily_average_cost > 0:
            days_until_exhaustion = remaining_budget / daily_average_cost
        else:
            days_until_exhaustion = float('inf')

        # Calculate success rate
        success_rate = (
            (self.successful_requests / self.total_requests * 100)
            if self.total_requests > 0 else 0
        )

        return {
            # Current status
            'total_requests': self.total_requests,
            'successful_requests': self.successful_requests,
            'failed_requests': self.failed_requests,
            'success_rate_pct': round(success_rate, 2),

            # Budget metrics
            'total_cost': round(self.total_cost, 4),
            'budget_limit': self.budget_limit,
            'budget_remaining': round(remaining_budget, 4),
            'budget_used_pct': round(usage_ratio * 100, 2),
            'alert_level': self._get_alert_level(usage_ratio),

            # Thresholds
            'thresholds': {
                'warning': f"{int(self.warning_threshold * 100)}%",
                'critical': f"{int(self.critical_threshold * 100)}%",
                'danger': f"{int(self.danger_threshold * 100)}%"
            },

            # Time tracking
            'tracking_start_date': self.start_date,
            'days_elapsed': days_elapsed,
            'daily_average_requests': round(daily_average_requests, 2),
            'daily_average_cost': round(daily_average_cost, 4),

            # Prediction
            'prediction': {
                'days_until_exhaustion': round(days_until_exhaustion, 1) if days_until_exhaustion != float('inf') else None,
                'estimated_exhaustion_date': (
                    (datetime.now() + timedelta(days=days_until_exhaustion)).strftime('%Y-%m-%d')
                    if days_until_exhaustion != float('inf') else None
                )
            },

            # Detailed breakdowns
            'requests_by_date': self.requests_by_date,
            'daily_costs': {k: round(v, 4) for k, v in self.daily_costs.items()},
            'requests_by_asset': self.requests_by_asset,

            # Configuration
            'cost_per_request': self.cost_per_request,
            'max_possible_requests': int(self.budget_limit / self.cost_per_request),
            'last_updated': datetime.now().isoformat()
        }

    def reset(self, confirm: bool = True) -> dict:
        """
        Reset all tracking data and statistics.

        Args:
            confirm: Safety flag requiring explicit confirmation (default: True)

        Returns:
            Dictionary with pre-reset statistics and confirmation message

        Raises:
            ValueError: If confirm=False (prevents accidental resets)

        Example:
            >>> tracker = CostTracker()
            >>> result = tracker.reset(confirm=True)
            >>> print(result['message'])
            'Cost tracker reset successfully'
        """
        if not confirm:
            raise ValueError("Reset requires explicit confirmation (confirm=True)")

        # Capture final statistics before reset
        final_stats = self.get_statistics()

        with self._request_lock:
            # Reset all counters
            self.total_requests = 0
            self.total_cost = 0.0
            self.successful_requests = 0
            self.failed_requests = 0
            self.start_date = datetime.now().isoformat()

            # Clear tracking dictionaries
            self.requests_by_date.clear()
            self.requests_by_asset.clear()
            self.daily_costs.clear()

            # Persist reset state
            self._save_data()

        return {
            'message': 'Cost tracker reset successfully',
            'reset_timestamp': datetime.now().isoformat(),
            'previous_statistics': final_stats
        }

    def get_alert_status(self) -> dict:
        """
        Get current alert status with actionable information.

        Returns:
            Dictionary with alert level, threshold info, and recommendations
        """
        usage_ratio = self.total_cost / self.budget_limit if self.budget_limit > 0 else 0
        alert_level = self._get_alert_level(usage_ratio)

        recommendations = {
            'ok': 'Budget usage is healthy. Continue normal operations.',
            'warning': 'Budget is 50% consumed. Monitor usage carefully.',
            'critical': 'Budget is 80% consumed. Consider reducing request frequency.',
            'danger': 'Budget is 95% consumed. Immediate action required - requests will be blocked soon.'
        }

        return {
            'alert_level': alert_level,
            'budget_used_pct': round(usage_ratio * 100, 2),
            'budget_remaining': round(self.budget_limit - self.total_cost, 4),
            'requests_remaining': int((self.budget_limit - self.total_cost) / self.cost_per_request),
            'recommendation': recommendations[alert_level],
            'next_threshold': self._get_next_threshold(usage_ratio),
            'timestamp': datetime.now().isoformat()
        }

    def _get_next_threshold(self, current_ratio: float) -> Optional[dict]:
        """
        Calculate next alert threshold and requests until reached.

        Args:
            current_ratio: Current budget usage ratio

        Returns:
            Dictionary with next threshold info or None if at max
        """
        thresholds = [
            (self.warning_threshold, 'warning'),
            (self.critical_threshold, 'critical'),
            (self.danger_threshold, 'danger')
        ]

        for threshold, level in thresholds:
            if current_ratio < threshold:
                requests_until = int(
                    (threshold * self.budget_limit - self.total_cost) / self.cost_per_request
                )
                return {
                    'level': level,
                    'threshold_pct': int(threshold * 100),
                    'requests_until': max(0, requests_until)
                }

        return None

    def __repr__(self) -> str:
        """String representation of cost tracker state."""
        usage_pct = (self.total_cost / self.budget_limit * 100) if self.budget_limit > 0 else 0
        return (
            f"CostTracker(requests={self.total_requests}, "
            f"cost=${self.total_cost:.4f}, "
            f"budget_used={usage_pct:.1f}%, "
            f"alert={self._get_alert_level(self.total_cost / self.budget_limit)})"
        )
