"""
Custom exception classes for Bloomberg Data Crawler.

Provides a hierarchy of exceptions for different failure scenarios
with appropriate context and debugging information.
"""

from typing import Any, Optional


class BloombergDataError(Exception):
    """Base exception for all Bloomberg Data Crawler errors.

    All custom exceptions inherit from this class, allowing
    catch-all error handling when needed.

    Attributes:
        message: Human-readable error description
        details: Additional context about the error
    """

    def __init__(self, message: str, details: Optional[dict[str, Any]] = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)

    def __str__(self) -> str:
        if self.details:
            details_str = ", ".join(f"{k}={v}" for k, v in self.details.items())
            return f"{self.message} ({details_str})"
        return self.message


class BudgetExhaustedError(BloombergDataError):
    """Raised when API request budget is exhausted.

    Indicates that the configured request limit has been reached
    and no further API calls can be made until reset.

    Attributes:
        current_usage: Number of requests already made
        budget_limit: Maximum allowed requests
        reset_time: When the budget will reset (optional)
    """

    def __init__(
        self,
        message: str = "API request budget exhausted",
        current_usage: Optional[int] = None,
        budget_limit: Optional[int] = None,
        reset_time: Optional[str] = None,
        **kwargs
    ):
        details = {
            "current_usage": current_usage,
            "budget_limit": budget_limit,
            "reset_time": reset_time,
            **kwargs
        }
        details = {k: v for k, v in details.items() if v is not None}
        super().__init__(message, details)
        self.current_usage = current_usage
        self.budget_limit = budget_limit
        self.reset_time = reset_time


class CacheError(BloombergDataError):
    """Raised when cache operations fail.

    Covers failures in reading from, writing to, or invalidating cache.

    Attributes:
        operation: The cache operation that failed (read/write/delete/clear)
        cache_key: The key involved in the failed operation
    """

    def __init__(
        self,
        message: str,
        operation: Optional[str] = None,
        cache_key: Optional[str] = None,
        **kwargs
    ):
        details = {
            "operation": operation,
            "cache_key": cache_key,
            **kwargs
        }
        details = {k: v for k, v in details.items() if v is not None}
        super().__init__(message, details)
        self.operation = operation
        self.cache_key = cache_key


class ParsingError(BloombergDataError):
    """Raised when data parsing fails.

    Indicates failure to extract or transform data from API responses,
    HTML content, or other data sources.

    Attributes:
        source: Data source that failed to parse
        parser: Parser type used (json/html/xml)
        raw_data: Raw data snippet (optional, for debugging)
    """

    def __init__(
        self,
        message: str,
        source: Optional[str] = None,
        parser: Optional[str] = None,
        raw_data: Optional[str] = None,
        **kwargs
    ):
        details = {
            "source": source,
            "parser": parser,
            **kwargs
        }
        if raw_data:
            # Truncate raw data for readability
            details["raw_data_preview"] = raw_data[:200] + "..." if len(raw_data) > 200 else raw_data

        details = {k: v for k, v in details.items() if v is not None}
        super().__init__(message, details)
        self.source = source
        self.parser = parser
        self.raw_data = raw_data


class APIError(BloombergDataError):
    """Raised when API calls fail.

    Covers HTTP errors, network failures, and invalid responses
    from external APIs.

    Attributes:
        endpoint: API endpoint that failed
        status_code: HTTP status code (if applicable)
        response_body: Response content (if available)
        request_params: Request parameters used
    """

    def __init__(
        self,
        message: str,
        endpoint: Optional[str] = None,
        status_code: Optional[int] = None,
        response_body: Optional[str] = None,
        request_params: Optional[dict[str, Any]] = None,
        **kwargs
    ):
        details = {
            "endpoint": endpoint,
            "status_code": status_code,
            "request_params": request_params,
            **kwargs
        }
        if response_body:
            # Truncate response body for readability
            details["response_preview"] = response_body[:200] + "..." if len(response_body) > 200 else response_body

        details = {k: v for k, v in details.items() if v is not None}
        super().__init__(message, details)
        self.endpoint = endpoint
        self.status_code = status_code
        self.response_body = response_body
        self.request_params = request_params


class RateLimitError(APIError):
    """Raised when API rate limits are exceeded.

    Specialized APIError for rate limiting scenarios, allowing
    clients to implement retry logic with backoff.

    Attributes:
        retry_after: Seconds to wait before retrying (if provided by API)
        requests_remaining: Remaining requests in current window (if known)
        window_reset: When the rate limit window resets
    """

    def __init__(
        self,
        message: str = "API rate limit exceeded",
        retry_after: Optional[int] = None,
        requests_remaining: Optional[int] = None,
        window_reset: Optional[str] = None,
        **kwargs
    ):
        details = {
            "retry_after": retry_after,
            "requests_remaining": requests_remaining,
            "window_reset": window_reset,
            **kwargs
        }
        details = {k: v for k, v in details.items() if v is not None}
        super().__init__(message, **details)
        self.retry_after = retry_after
        self.requests_remaining = requests_remaining
        self.window_reset = window_reset


class CircuitBreakerError(BloombergDataError):
    """Raised when circuit breaker is open.

    Indicates that a service is experiencing failures and the
    circuit breaker has opened to prevent cascading failures.

    Attributes:
        service: Service name with open circuit
        failure_count: Number of consecutive failures
        state: Circuit breaker state (open/half_open)
        reset_timeout: When circuit will attempt to close
    """

    def __init__(
        self,
        message: str = "Circuit breaker is open",
        service: Optional[str] = None,
        failure_count: Optional[int] = None,
        state: str = "open",
        reset_timeout: Optional[str] = None,
        **kwargs
    ):
        details = {
            "service": service,
            "failure_count": failure_count,
            "state": state,
            "reset_timeout": reset_timeout,
            **kwargs
        }
        details = {k: v for k, v in details.items() if v is not None}
        super().__init__(message, details)
        self.service = service
        self.failure_count = failure_count
        self.state = state
        self.reset_timeout = reset_timeout


class DataNormalizationError(BloombergDataError):
    """Raised when data normalization or transformation fails.

    Indicates failure to convert data from one format to another,
    invalid data structures, or missing required fields during normalization.

    Attributes:
        source: Data source being normalized (bloomberg/yfinance/finnhub)
        field: Specific field that caused the error
        value: Value that failed normalization
    """

    def __init__(
        self,
        message: str,
        source: Optional[str] = None,
        field: Optional[str] = None,
        value: Optional[Any] = None,
        **kwargs
    ):
        details = {
            "source": source,
            "field": field,
            **kwargs
        }
        if value is not None:
            # Truncate value for readability
            value_str = str(value)
            details["value"] = value_str[:100] + "..." if len(value_str) > 100 else value_str

        details = {k: v for k, v in details.items() if v is not None}
        super().__init__(message, details)
        self.source = source
        self.field = field
        self.value = value
