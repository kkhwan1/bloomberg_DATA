"""
Circuit Breaker Pattern Implementation.

Provides fault tolerance and resilience for external API calls through
state-based failure handling with automatic recovery.
"""

import logging
import threading
import time
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Optional

from src.utils.exceptions import APIError

logger = logging.getLogger(__name__)


class CircuitState(str, Enum):
    """Circuit breaker state machine states."""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Blocking requests due to failures
    HALF_OPEN = "half_open"  # Testing recovery


class CircuitBreakerError(APIError):
    """Raised when circuit breaker is in OPEN state."""

    def __init__(self, message: str, state: CircuitState, **kwargs):
        super().__init__(message, **kwargs)
        self.state = state


class CircuitBreaker:
    """
    Circuit breaker pattern for fault tolerance and resilience.

    Prevents cascading failures by temporarily blocking requests to failing services.
    Uses a state machine with three states: CLOSED, OPEN, and HALF_OPEN.

    State Transitions:
        CLOSED → OPEN: After failure_threshold consecutive failures
        OPEN → HALF_OPEN: After recovery_timeout seconds
        HALF_OPEN → CLOSED: On first successful request
        HALF_OPEN → OPEN: On any failure

    Attributes:
        name: Identifier for this circuit breaker
        failure_threshold: Number of failures before opening circuit
        recovery_timeout: Seconds to wait before attempting recovery
        success_threshold: Successful calls needed in HALF_OPEN to close circuit
        state: Current circuit state (CLOSED, OPEN, HALF_OPEN)

    Example:
        >>> breaker = CircuitBreaker("yfinance_api", failure_threshold=3)
        >>> try:
        ...     result = breaker.call(fetch_data, symbol="AAPL")
        ...     print(f"Got data: {result}")
        ... except CircuitBreakerError:
        ...     print("Service unavailable - circuit is open")
    """

    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        success_threshold: int = 1,
    ):
        """
        Initialize circuit breaker.

        Args:
            name: Identifier for this circuit breaker
            failure_threshold: Consecutive failures before opening (default: 5)
            recovery_timeout: Seconds before attempting recovery (default: 60)
            success_threshold: Successes needed to close from HALF_OPEN (default: 1)
        """
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.success_threshold = success_threshold

        # State management
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: Optional[datetime] = None
        self._opened_at: Optional[datetime] = None

        # Thread safety
        self._lock = threading.Lock()

        # Statistics
        self._total_calls = 0
        self._total_failures = 0
        self._total_successes = 0
        self._state_changes = []

        logger.info(
            f"Circuit breaker initialized: {name}",
            extra={
                "failure_threshold": failure_threshold,
                "recovery_timeout": recovery_timeout,
                "success_threshold": success_threshold,
            },
        )

    @property
    def state(self) -> CircuitState:
        """Get current circuit state."""
        with self._lock:
            # Check if we should transition from OPEN to HALF_OPEN
            if self._state == CircuitState.OPEN:
                if self._should_attempt_reset():
                    self._transition_to_half_open()
            return self._state

    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt recovery."""
        if not self._opened_at:
            return False
        elapsed = (datetime.now() - self._opened_at).total_seconds()
        return elapsed >= self.recovery_timeout

    def _transition_to_half_open(self) -> None:
        """Transition from OPEN to HALF_OPEN state."""
        old_state = self._state
        self._state = CircuitState.HALF_OPEN
        self._success_count = 0
        self._record_state_change(old_state, CircuitState.HALF_OPEN)
        logger.info(f"Circuit breaker {self.name}: OPEN → HALF_OPEN (attempting recovery)")

    def _transition_to_open(self) -> None:
        """Transition to OPEN state due to failures."""
        old_state = self._state
        self._state = CircuitState.OPEN
        self._opened_at = datetime.now()
        self._failure_count = 0  # Reset for next cycle
        self._record_state_change(old_state, CircuitState.OPEN)
        logger.warning(
            f"Circuit breaker {self.name}: {old_state} → OPEN (threshold exceeded)",
            extra={
                "failure_threshold": self.failure_threshold,
                "recovery_timeout": self.recovery_timeout,
            },
        )

    def _transition_to_closed(self) -> None:
        """Transition to CLOSED state after successful recovery."""
        old_state = self._state
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._opened_at = None
        self._record_state_change(old_state, CircuitState.CLOSED)
        logger.info(f"Circuit breaker {self.name}: {old_state} → CLOSED (recovered)")

    def _record_state_change(self, from_state: CircuitState, to_state: CircuitState) -> None:
        """Record state transition for statistics."""
        self._state_changes.append(
            {
                "timestamp": datetime.now().isoformat(),
                "from_state": from_state.value,
                "to_state": to_state.value,
                "failure_count": self._failure_count,
                "total_failures": self._total_failures,
            }
        )

    def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function through circuit breaker.

        Args:
            func: Callable to execute
            *args: Positional arguments for func
            **kwargs: Keyword arguments for func

        Returns:
            Result from func execution

        Raises:
            CircuitBreakerError: If circuit is OPEN
            Exception: Any exception raised by func

        Example:
            >>> breaker = CircuitBreaker("api")
            >>> result = breaker.call(api.fetch, "AAPL")
        """
        with self._lock:
            self._total_calls += 1
            current_state = self.state  # Triggers OPEN → HALF_OPEN check

            # Block requests when circuit is OPEN
            if current_state == CircuitState.OPEN:
                logger.warning(
                    f"Circuit breaker {self.name} is OPEN - blocking request",
                    extra={
                        "opened_at": self._opened_at.isoformat() if self._opened_at else None,
                        "recovery_in": self._get_recovery_time_remaining(),
                    },
                )
                raise CircuitBreakerError(
                    f"Circuit breaker '{self.name}' is OPEN - service unavailable",
                    state=CircuitState.OPEN,
                    endpoint=self.name,
                    message="Circuit breaker is open due to previous failures",
                )

        # Execute function
        try:
            result = func(*args, **kwargs)
            self.record_success()
            return result

        except Exception as e:
            self.record_failure()
            raise

    def record_success(self) -> None:
        """Record successful operation."""
        with self._lock:
            self._total_successes += 1
            self._failure_count = 0  # Reset consecutive failures
            self._last_failure_time = None

            if self._state == CircuitState.HALF_OPEN:
                self._success_count += 1
                logger.debug(
                    f"Circuit breaker {self.name}: success in HALF_OPEN "
                    f"({self._success_count}/{self.success_threshold})"
                )

                # Close circuit after enough successes
                if self._success_count >= self.success_threshold:
                    self._transition_to_closed()

            logger.debug(f"Circuit breaker {self.name}: recorded success (state={self._state})")

    def record_failure(self) -> None:
        """Record failed operation."""
        with self._lock:
            self._total_failures += 1
            self._failure_count += 1
            self._last_failure_time = datetime.now()

            logger.debug(
                f"Circuit breaker {self.name}: recorded failure "
                f"({self._failure_count}/{self.failure_threshold})"
            )

            # Transition based on current state
            if self._state == CircuitState.HALF_OPEN:
                # Any failure in HALF_OPEN immediately opens circuit
                self._transition_to_open()

            elif self._state == CircuitState.CLOSED:
                # Open circuit after threshold failures
                if self._failure_count >= self.failure_threshold:
                    self._transition_to_open()

    def is_available(self) -> bool:
        """
        Check if service is available for requests.

        Returns:
            True if circuit is CLOSED or HALF_OPEN, False if OPEN
        """
        return self.state != CircuitState.OPEN

    def reset(self) -> None:
        """Manually reset circuit breaker to CLOSED state."""
        with self._lock:
            old_state = self._state
            self._state = CircuitState.CLOSED
            self._failure_count = 0
            self._success_count = 0
            self._opened_at = None
            self._last_failure_time = None
            logger.info(f"Circuit breaker {self.name}: manual reset from {old_state} to CLOSED")

    def _get_recovery_time_remaining(self) -> Optional[int]:
        """Get seconds remaining until recovery attempt."""
        if not self._opened_at or self._state != CircuitState.OPEN:
            return None
        elapsed = (datetime.now() - self._opened_at).total_seconds()
        remaining = max(0, self.recovery_timeout - elapsed)
        return int(remaining)

    def get_statistics(self) -> dict:
        """
        Get comprehensive circuit breaker statistics.

        Returns:
            Dictionary with state, counters, and metrics
        """
        with self._lock:
            failure_rate = (
                (self._total_failures / self._total_calls * 100)
                if self._total_calls > 0
                else 0
            )

            return {
                "name": self.name,
                "state": self._state.value,
                "is_available": self.is_available(),
                "configuration": {
                    "failure_threshold": self.failure_threshold,
                    "recovery_timeout": self.recovery_timeout,
                    "success_threshold": self.success_threshold,
                },
                "counters": {
                    "total_calls": self._total_calls,
                    "total_successes": self._total_successes,
                    "total_failures": self._total_failures,
                    "consecutive_failures": self._failure_count,
                    "consecutive_successes": self._success_count,
                },
                "metrics": {
                    "failure_rate_pct": round(failure_rate, 2),
                    "success_rate_pct": round(100 - failure_rate, 2),
                },
                "state_info": {
                    "current_state": self._state.value,
                    "opened_at": self._opened_at.isoformat() if self._opened_at else None,
                    "last_failure_at": (
                        self._last_failure_time.isoformat() if self._last_failure_time else None
                    ),
                    "recovery_in_seconds": self._get_recovery_time_remaining(),
                },
                "state_changes": self._state_changes[-10:],  # Last 10 transitions
            }

    def __repr__(self) -> str:
        """String representation for debugging."""
        return (
            f"CircuitBreaker(name={self.name}, state={self._state.value}, "
            f"failures={self._failure_count}/{self.failure_threshold})"
        )
