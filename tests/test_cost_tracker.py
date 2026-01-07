"""
Unit tests for CostTracker class.

Tests cover:
    - Singleton pattern behavior
    - Thread safety
    - Budget tracking and alerts
    - Request recording
    - Statistics generation
    - Persistence and data recovery
    - Budget exhaustion handling
    - Reset functionality
"""

import json
import os
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import pytest

from src.orchestrator.cost_tracker import CostTracker
from src.utils.exceptions import BudgetExhaustedError


@pytest.fixture
def clean_tracker():
    """Provide a fresh CostTracker instance for each test."""
    # Reset the singleton
    CostTracker._instance = None

    # Create new instance
    tracker = CostTracker()

    # Clean up any existing data file
    if tracker.storage_path.exists():
        tracker.storage_path.unlink()

    # Reset the tracker
    try:
        tracker.reset(confirm=True)
    except:
        pass

    yield tracker

    # Cleanup after test
    if tracker.storage_path.exists():
        tracker.storage_path.unlink()


class TestSingletonPattern:
    """Test singleton pattern implementation."""

    def test_singleton_instance(self, clean_tracker):
        """Test that only one instance exists."""
        tracker1 = CostTracker()
        tracker2 = CostTracker()

        assert tracker1 is tracker2
        assert id(tracker1) == id(tracker2)

    def test_thread_safe_singleton(self, clean_tracker):
        """Test singleton is thread-safe."""
        instances = []

        def create_instance():
            tracker = CostTracker()
            instances.append(id(tracker))

        threads = [threading.Thread(target=create_instance) for _ in range(10)]

        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        # All instances should have the same ID
        assert len(set(instances)) == 1


class TestBudgetTracking:
    """Test budget tracking and validation."""

    def test_initial_state(self, clean_tracker):
        """Test initial tracker state."""
        assert clean_tracker.total_requests == 0
        assert clean_tracker.total_cost == 0.0
        assert clean_tracker.successful_requests == 0
        assert clean_tracker.failed_requests == 0

    def test_can_make_request_with_budget(self, clean_tracker):
        """Test request validation when budget is available."""
        assert clean_tracker.can_make_request() is True

    def test_can_make_request_exhausted_budget(self, clean_tracker):
        """Test request validation when budget is exhausted."""
        # Exhaust budget
        max_requests = int(clean_tracker.budget_limit / clean_tracker.cost_per_request)

        for i in range(max_requests):
            clean_tracker.record_request('equity', f'TEST{i}:US', success=True)

        # Next request should raise exception
        with pytest.raises(BudgetExhaustedError) as exc_info:
            clean_tracker.can_make_request()

        assert 'budget exhausted' in str(exc_info.value).lower()
        assert exc_info.value.current_usage == max_requests

    def test_cost_calculation(self, clean_tracker):
        """Test accurate cost calculation."""
        requests = 10
        for i in range(requests):
            clean_tracker.record_request('equity', f'TEST{i}:US', success=True)

        expected_cost = requests * clean_tracker.cost_per_request
        assert abs(clean_tracker.total_cost - expected_cost) < 0.0001


class TestRequestRecording:
    """Test request recording functionality."""

    def test_record_successful_request(self, clean_tracker):
        """Test recording successful request."""
        result = clean_tracker.record_request('equity', 'AAPL:US', success=True)

        assert result['success'] is True
        assert result['request_count'] == 1
        assert result['asset_class'] == 'equity'
        assert result['symbol'] == 'AAPL:US'
        assert clean_tracker.successful_requests == 1
        assert clean_tracker.failed_requests == 0

    def test_record_failed_request(self, clean_tracker):
        """Test recording failed request."""
        result = clean_tracker.record_request('equity', 'AAPL:US', success=False)

        assert result['success'] is False
        assert result['request_count'] == 1
        assert clean_tracker.successful_requests == 0
        assert clean_tracker.failed_requests == 1

    def test_date_based_tracking(self, clean_tracker):
        """Test date-based request tracking."""
        today = datetime.now().strftime('%Y-%m-%d')

        clean_tracker.record_request('equity', 'AAPL:US', success=True)
        clean_tracker.record_request('equity', 'MSFT:US', success=True)

        assert today in clean_tracker.requests_by_date
        assert clean_tracker.requests_by_date[today] == 2

    def test_asset_based_tracking(self, clean_tracker):
        """Test asset-based request tracking."""
        clean_tracker.record_request('equity', 'AAPL:US', success=True)
        clean_tracker.record_request('equity', 'AAPL:US', success=True)
        clean_tracker.record_request('equity', 'MSFT:US', success=True)
        clean_tracker.record_request('index', 'SPX:IND', success=True)

        assert 'equity' in clean_tracker.requests_by_asset
        assert 'index' in clean_tracker.requests_by_asset
        assert clean_tracker.requests_by_asset['equity']['AAPL:US'] == 2
        assert clean_tracker.requests_by_asset['equity']['MSFT:US'] == 1
        assert clean_tracker.requests_by_asset['index']['SPX:IND'] == 1

    def test_thread_safe_recording(self, clean_tracker):
        """Test thread-safe request recording."""
        def record_requests(count):
            for i in range(count):
                clean_tracker.record_request('equity', f'TEST{i}:US', success=True)

        threads = [threading.Thread(target=record_requests, args=(10,)) for _ in range(5)]

        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        # Should have exactly 50 requests
        assert clean_tracker.total_requests == 50


class TestAlertThresholds:
    """Test alert threshold system."""

    def test_alert_level_ok(self, clean_tracker):
        """Test OK alert level (< 50%)."""
        # Use 25% of budget
        requests = int(0.25 * clean_tracker.budget_limit / clean_tracker.cost_per_request)

        for i in range(requests):
            clean_tracker.record_request('equity', f'TEST{i}:US', success=True)

        stats = clean_tracker.get_statistics()
        assert stats['alert_level'] == 'ok'

    def test_alert_level_warning(self, clean_tracker):
        """Test WARNING alert level (>= 50%, < 80%)."""
        # Use 60% of budget
        requests = int(0.60 * clean_tracker.budget_limit / clean_tracker.cost_per_request)

        for i in range(requests):
            clean_tracker.record_request('equity', f'TEST{i}:US', success=True)

        stats = clean_tracker.get_statistics()
        assert stats['alert_level'] == 'warning'
        assert stats['budget_used_pct'] >= 50

    def test_alert_level_critical(self, clean_tracker):
        """Test CRITICAL alert level (>= 80%, < 95%)."""
        # Use 85% of budget
        requests = int(0.85 * clean_tracker.budget_limit / clean_tracker.cost_per_request)

        for i in range(requests):
            clean_tracker.record_request('equity', f'TEST{i}:US', success=True)

        stats = clean_tracker.get_statistics()
        assert stats['alert_level'] == 'critical'
        assert stats['budget_used_pct'] >= 80

    def test_alert_level_danger(self, clean_tracker):
        """Test DANGER alert level (>= 95%)."""
        # Use 96% of budget
        requests = int(0.96 * clean_tracker.budget_limit / clean_tracker.cost_per_request)

        for i in range(requests):
            clean_tracker.record_request('equity', f'TEST{i}:US', success=True)

        stats = clean_tracker.get_statistics()
        assert stats['alert_level'] == 'danger'
        assert stats['budget_used_pct'] >= 95

    def test_alert_status(self, clean_tracker):
        """Test get_alert_status method."""
        clean_tracker.record_request('equity', 'AAPL:US', success=True)

        alert = clean_tracker.get_alert_status()

        assert 'alert_level' in alert
        assert 'budget_used_pct' in alert
        assert 'budget_remaining' in alert
        assert 'requests_remaining' in alert
        assert 'recommendation' in alert


class TestStatistics:
    """Test statistics generation."""

    def test_get_statistics_structure(self, clean_tracker):
        """Test statistics output structure."""
        clean_tracker.record_request('equity', 'AAPL:US', success=True)

        stats = clean_tracker.get_statistics()

        # Check required keys
        required_keys = [
            'total_requests', 'successful_requests', 'failed_requests',
            'total_cost', 'budget_limit', 'budget_remaining', 'budget_used_pct',
            'alert_level', 'tracking_start_date', 'days_elapsed',
            'daily_average_requests', 'daily_average_cost', 'prediction',
            'requests_by_date', 'daily_costs', 'requests_by_asset'
        ]

        for key in required_keys:
            assert key in stats

    def test_success_rate_calculation(self, clean_tracker):
        """Test success rate calculation."""
        # 7 successful, 3 failed = 70% success rate
        for i in range(7):
            clean_tracker.record_request('equity', f'TEST{i}:US', success=True)
        for i in range(3):
            clean_tracker.record_request('equity', f'FAIL{i}:US', success=False)

        stats = clean_tracker.get_statistics()
        assert abs(stats['success_rate_pct'] - 70.0) < 0.1

    def test_budget_exhaustion_prediction(self, clean_tracker):
        """Test budget exhaustion prediction."""
        # Record some requests
        for i in range(10):
            clean_tracker.record_request('equity', f'TEST{i}:US', success=True)

        stats = clean_tracker.get_statistics()

        assert 'prediction' in stats
        assert 'days_until_exhaustion' in stats['prediction']
        assert stats['prediction']['days_until_exhaustion'] is not None

    def test_daily_averages(self, clean_tracker):
        """Test daily average calculations."""
        # Record requests
        for i in range(10):
            clean_tracker.record_request('equity', f'TEST{i}:US', success=True)

        stats = clean_tracker.get_statistics()

        assert stats['daily_average_requests'] > 0
        assert stats['daily_average_cost'] > 0


class TestPersistence:
    """Test data persistence functionality."""

    def test_data_persistence(self, clean_tracker):
        """Test data is persisted to JSON file."""
        clean_tracker.record_request('equity', 'AAPL:US', success=True)

        assert clean_tracker.storage_path.exists()

        # Load and verify JSON
        with open(clean_tracker.storage_path, 'r') as f:
            data = json.load(f)

        assert data['total_requests'] == 1
        assert 'equity' in data['requests_by_asset']

    def test_data_recovery(self, clean_tracker):
        """Test data is recovered on initialization."""
        # Record some data
        clean_tracker.record_request('equity', 'AAPL:US', success=True)
        clean_tracker.record_request('equity', 'MSFT:US', success=True)

        # Create new instance (simulates restart)
        CostTracker._instance = None
        new_tracker = CostTracker()

        # Data should be recovered
        assert new_tracker.total_requests == 2
        assert 'AAPL:US' in new_tracker.requests_by_asset['equity']

    def test_corrupted_data_handling(self, clean_tracker):
        """Test handling of corrupted persistence file."""
        # Write invalid JSON
        with open(clean_tracker.storage_path, 'w') as f:
            f.write("invalid json {{{")

        # Should handle gracefully
        CostTracker._instance = None
        new_tracker = CostTracker()

        # Should start fresh
        assert new_tracker.total_requests == 0


class TestReset:
    """Test reset functionality."""

    def test_reset_with_confirmation(self, clean_tracker):
        """Test reset with confirmation."""
        # Record some data
        for i in range(5):
            clean_tracker.record_request('equity', f'TEST{i}:US', success=True)

        # Reset
        result = clean_tracker.reset(confirm=True)

        assert 'message' in result
        assert 'previous_statistics' in result
        assert clean_tracker.total_requests == 0
        assert clean_tracker.total_cost == 0.0

    def test_reset_without_confirmation(self, clean_tracker):
        """Test reset requires confirmation."""
        with pytest.raises(ValueError) as exc_info:
            clean_tracker.reset(confirm=False)

        assert 'confirmation' in str(exc_info.value).lower()

    def test_reset_clears_all_data(self, clean_tracker):
        """Test reset clears all tracking data."""
        # Add various data
        clean_tracker.record_request('equity', 'AAPL:US', success=True)
        clean_tracker.record_request('index', 'SPX:IND', success=False)

        # Reset
        clean_tracker.reset(confirm=True)

        # Check all data cleared
        assert len(clean_tracker.requests_by_date) == 0
        assert len(clean_tracker.requests_by_asset) == 0
        assert len(clean_tracker.daily_costs) == 0
        assert clean_tracker.successful_requests == 0
        assert clean_tracker.failed_requests == 0


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_zero_budget(self):
        """Test handling of zero budget."""
        CostTracker._instance = None

        with patch('src.config.CostConfig.TOTAL_BUDGET', 0.0):
            tracker = CostTracker()

            with pytest.raises(BudgetExhaustedError):
                tracker.can_make_request()

    def test_repr(self, clean_tracker):
        """Test string representation."""
        clean_tracker.record_request('equity', 'AAPL:US', success=True)

        repr_str = repr(clean_tracker)

        assert 'CostTracker' in repr_str
        assert 'requests=1' in repr_str
        assert 'alert=' in repr_str

    def test_concurrent_reads_and_writes(self, clean_tracker):
        """Test concurrent statistics reads during writes."""
        def write_requests():
            for i in range(20):
                clean_tracker.record_request('equity', f'W{i}:US', success=True)
                time.sleep(0.01)

        def read_statistics():
            for _ in range(20):
                clean_tracker.get_statistics()
                time.sleep(0.01)

        threads = [
            threading.Thread(target=write_requests),
            threading.Thread(target=read_statistics),
            threading.Thread(target=read_statistics)
        ]

        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        # Should complete without errors
        assert clean_tracker.total_requests == 20
