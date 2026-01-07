"""
Bright Data API client for Bloomberg Data Crawler.

Asynchronous HTTP client with retry logic, cost tracking, and caching
for Bright Data Web Unlocker API integration.
"""

import asyncio
import logging
from dataclasses import dataclass
from typing import Any, Optional

import aiohttp

from ..config import APIConfig, BrightDataConfig, CostConfig
from ..utils.exceptions import APIError, BudgetExhaustedError, RateLimitError


logger = logging.getLogger(__name__)


@dataclass
class BrightDataClientConfig:
    """Configuration for Bright Data API client.

    Attributes:
        api_token: Bright Data API token
        zone: Data center zone identifier
        endpoint: API endpoint URL
        timeout: Request timeout in seconds
        max_retries: Maximum retry attempts
        base_delay: Initial retry delay in seconds
    """

    api_token: str
    zone: str = "bloomberg"
    endpoint: str = "https://api.brightdata.com/request"
    timeout: int = 30
    max_retries: int = 3
    base_delay: float = 1.0

    @classmethod
    def from_env(cls) -> "BrightDataClientConfig":
        """Create configuration from environment variables."""
        return cls(
            api_token=BrightDataConfig.API_TOKEN,
            zone=BrightDataConfig.ZONE,
            timeout=APIConfig.REQUEST_TIMEOUT,
            max_retries=3,
            base_delay=1.0,
        )


class AuthError(APIError):
    """Raised when authentication fails (401/403)."""
    pass


class ServerError(APIError):
    """Raised when server returns 5xx error."""
    pass


class BrightDataClient:
    """Asynchronous Bright Data API client with retry logic and cost tracking.

    Features:
    - Async HTTP with aiohttp
    - Exponential backoff retry (max 3 attempts)
    - Cost tracking integration
    - Cache integration
    - Timeout handling (30s default)
    - Comprehensive error handling

    Example:
        ```python
        from src.clients.bright_data import BrightDataClient, BrightDataClientConfig
        from src.tracking.cost_tracker import CostTracker
        from src.cache.response_cache import ResponseCache

        config = BrightDataClientConfig.from_env()
        cost_tracker = CostTracker()
        cache = ResponseCache()

        async with BrightDataClient(config, cost_tracker, cache) as client:
            html = await client.fetch("https://www.bloomberg.com/quote/AAPL:US")
            if html:
                print(f"Fetched {len(html)} bytes")
        ```
    """

    def __init__(
        self,
        config: BrightDataClientConfig,
        cost_tracker: Any,
        cache: Any,
    ):
        """Initialize Bright Data client.

        Args:
            config: Client configuration
            cost_tracker: Cost tracking instance
            cache: Response cache instance
        """
        self.config = config
        self.cost_tracker = cost_tracker
        self.cache = cache
        self._session: Optional[aiohttp.ClientSession] = None
        self._stats = {
            "requests_made": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "retries": 0,
            "errors": 0,
        }

        logger.info(
            "Initialized BrightDataClient",
            extra={
                "zone": config.zone,
                "timeout": config.timeout,
                "max_retries": config.max_retries,
            },
        )

    async def __aenter__(self) -> "BrightDataClient":
        """Enter async context manager."""
        await self._ensure_session()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit async context manager."""
        await self.close()

    async def _ensure_session(self) -> None:
        """Ensure aiohttp session is initialized."""
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=self.config.timeout)
            self._session = aiohttp.ClientSession(timeout=timeout)
            logger.debug("Created new aiohttp session")

    async def close(self) -> None:
        """Close aiohttp session and cleanup resources."""
        if self._session and not self._session.closed:
            await self._session.close()
            logger.debug("Closed aiohttp session")

    def _get_cache_key(self, url: str) -> str:
        """Generate cache key for URL.

        Args:
            url: Target URL

        Returns:
            Cache key string
        """
        return f"bright_data:{url}"

    async def _check_budget(self) -> None:
        """Check if budget allows for request.

        Raises:
            BudgetExhaustedError: If budget is exhausted
        """
        if not self.cost_tracker.can_make_request():
            stats = self.cost_tracker.get_stats()
            raise BudgetExhaustedError(
                "Cannot make request: budget exhausted",
                current_usage=stats.get("requests_made", 0),
                budget_limit=stats.get("max_requests", 0),
                cost_spent=stats.get("total_cost", 0),
            )

    async def _make_request(self, url: str) -> str:
        """Make HTTP request to Bright Data API.

        Args:
            url: Target URL to fetch

        Returns:
            Response HTML content

        Raises:
            AuthError: Authentication failed (401/403)
            RateLimitError: Rate limit exceeded (429)
            ServerError: Server error (5xx)
            APIError: Other API errors
        """
        await self._ensure_session()

        headers = {
            "Authorization": f"Bearer {self.config.api_token}",
            "Content-Type": "application/json",
        }

        payload = {
            "zone": self.config.zone,
            "url": url,
            "format": "raw",
        }

        logger.debug(
            "Making Bright Data API request",
            extra={
                "url": url,
                "zone": self.config.zone,
                "endpoint": self.config.endpoint,
            },
        )

        try:
            async with self._session.post(
                self.config.endpoint,
                headers=headers,
                json=payload,
            ) as response:
                # Handle authentication errors
                if response.status in (401, 403):
                    error_body = await response.text()
                    logger.error(
                        "Authentication failed",
                        extra={
                            "status": response.status,
                            "url": url,
                        },
                    )
                    raise AuthError(
                        f"Authentication failed: {response.status}",
                        endpoint=self.config.endpoint,
                        status_code=response.status,
                        response_body=error_body,
                        request_params=payload,
                    )

                # Handle rate limiting (retryable)
                if response.status == 429:
                    retry_after = response.headers.get("Retry-After")
                    error_body = await response.text()
                    logger.warning(
                        "Rate limit exceeded",
                        extra={
                            "url": url,
                            "retry_after": retry_after,
                        },
                    )
                    raise RateLimitError(
                        "Rate limit exceeded",
                        endpoint=self.config.endpoint,
                        status_code=response.status,
                        retry_after=int(retry_after) if retry_after else None,
                        response_body=error_body,
                        request_params=payload,
                    )

                # Handle server errors (retryable)
                if response.status >= 500:
                    error_body = await response.text()
                    logger.error(
                        "Server error",
                        extra={
                            "status": response.status,
                            "url": url,
                        },
                    )
                    raise ServerError(
                        f"Server error: {response.status}",
                        endpoint=self.config.endpoint,
                        status_code=response.status,
                        response_body=error_body,
                        request_params=payload,
                    )

                # Handle other client errors
                if response.status >= 400:
                    error_body = await response.text()
                    logger.error(
                        "Client error",
                        extra={
                            "status": response.status,
                            "url": url,
                        },
                    )
                    raise APIError(
                        f"Request failed: {response.status}",
                        endpoint=self.config.endpoint,
                        status_code=response.status,
                        response_body=error_body,
                        request_params=payload,
                    )

                # Success - return response body
                content = await response.text()
                logger.info(
                    "Request successful",
                    extra={
                        "url": url,
                        "content_length": len(content),
                        "status": response.status,
                    },
                )
                return content

        except aiohttp.ClientError as e:
            logger.error(
                "HTTP client error",
                extra={
                    "url": url,
                    "error": str(e),
                },
            )
            raise APIError(
                f"HTTP client error: {str(e)}",
                endpoint=self.config.endpoint,
                request_params=payload,
            ) from e

    async def _fetch_with_retry(self, url: str) -> str:
        """Fetch URL with exponential backoff retry logic.

        Retries on:
        - RateLimitError (429)
        - ServerError (5xx)

        Does not retry on:
        - AuthError (401/403)
        - Other APIError instances

        Args:
            url: Target URL to fetch

        Returns:
            Response HTML content

        Raises:
            AuthError: Authentication failed (non-retryable)
            APIError: Request failed after retries
        """
        last_exception: Optional[Exception] = None

        for attempt in range(self.config.max_retries):
            try:
                return await self._make_request(url)

            except AuthError:
                # Don't retry auth errors
                raise

            except (RateLimitError, ServerError) as e:
                last_exception = e
                self._stats["retries"] += 1

                if attempt < self.config.max_retries - 1:
                    # Calculate exponential backoff delay
                    delay = self.config.base_delay * (2 ** attempt)

                    # Add jitter to prevent thundering herd
                    import random
                    jitter = random.uniform(0, delay * 0.1)
                    total_delay = delay + jitter

                    logger.warning(
                        "Retrying request",
                        extra={
                            "attempt": attempt + 1,
                            "max_retries": self.config.max_retries,
                            "delay": round(total_delay, 2),
                            "error": str(e),
                            "url": url,
                        },
                    )

                    await asyncio.sleep(total_delay)
                else:
                    logger.error(
                        "Max retries exceeded",
                        extra={
                            "url": url,
                            "attempts": self.config.max_retries,
                        },
                    )

            except Exception as e:
                # Unexpected error - don't retry
                logger.error(
                    "Unexpected error during request",
                    extra={
                        "url": url,
                        "error": str(e),
                        "error_type": type(e).__name__,
                    },
                )
                raise

        # All retries exhausted
        if last_exception:
            raise last_exception

        raise APIError(
            "Request failed after retries",
            endpoint=self.config.endpoint,
            request_params={"url": url},
        )

    async def fetch(self, url: str, use_cache: bool = True) -> Optional[str]:
        """Fetch URL with caching, budget check, and cost tracking.

        Args:
            url: Target URL to fetch
            use_cache: Whether to use cache (default: True)

        Returns:
            HTML content if successful, None on error

        Example:
            ```python
            html = await client.fetch("https://www.bloomberg.com/quote/AAPL:US")
            if html:
                print(f"Got {len(html)} bytes")
            ```
        """
        cache_key = self._get_cache_key(url)

        # Check cache first
        if use_cache:
            cached = await self.cache.get(cache_key)
            if cached:
                self._stats["cache_hits"] += 1
                logger.debug(
                    "Cache hit",
                    extra={
                        "url": url,
                        "cache_key": cache_key,
                    },
                )
                return cached

            self._stats["cache_misses"] += 1

        try:
            # Check budget before making request
            await self._check_budget()

            # Make request with retry logic
            content = await self._fetch_with_retry(url)

            # Track cost and stats
            self.cost_tracker.record_request()
            self._stats["requests_made"] += 1

            # Cache response
            if use_cache:
                await self.cache.set(cache_key, content)
                logger.debug(
                    "Cached response",
                    extra={
                        "url": url,
                        "cache_key": cache_key,
                        "content_length": len(content),
                    },
                )

            return content

        except BudgetExhaustedError:
            logger.error(
                "Budget exhausted, cannot fetch URL",
                extra={"url": url},
            )
            raise

        except AuthError:
            logger.error(
                "Authentication error, cannot fetch URL",
                extra={"url": url},
            )
            self._stats["errors"] += 1
            raise

        except Exception as e:
            logger.error(
                "Failed to fetch URL",
                extra={
                    "url": url,
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
            )
            self._stats["errors"] += 1
            return None

    async def fetch_multiple(
        self,
        urls: list[str],
        max_concurrent: int = 5,
    ) -> dict[str, Optional[str]]:
        """Fetch multiple URLs concurrently with rate limiting.

        Args:
            urls: List of URLs to fetch
            max_concurrent: Maximum concurrent requests (default: 5)

        Returns:
            Dictionary mapping URLs to their HTML content (or None on error)

        Example:
            ```python
            urls = [
                "https://www.bloomberg.com/quote/AAPL:US",
                "https://www.bloomberg.com/quote/MSFT:US",
            ]
            results = await client.fetch_multiple(urls)
            for url, html in results.items():
                if html:
                    print(f"{url}: {len(html)} bytes")
            ```
        """
        semaphore = asyncio.Semaphore(max_concurrent)

        async def fetch_with_semaphore(url: str) -> tuple[str, Optional[str]]:
            async with semaphore:
                content = await self.fetch(url)
                return url, content

        logger.info(
            "Fetching multiple URLs",
            extra={
                "url_count": len(urls),
                "max_concurrent": max_concurrent,
            },
        )

        tasks = [fetch_with_semaphore(url) for url in urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        output = {}
        for result in results:
            if isinstance(result, Exception):
                logger.error(
                    "Error in concurrent fetch",
                    extra={"error": str(result)},
                )
                continue

            url, content = result
            output[url] = content

        logger.info(
            "Completed multiple fetch",
            extra={
                "requested": len(urls),
                "successful": sum(1 for v in output.values() if v is not None),
                "failed": sum(1 for v in output.values() if v is None),
            },
        )

        return output

    def get_cache_stats(self) -> dict[str, Any]:
        """Get cache statistics.

        Returns:
            Dictionary with cache metrics
        """
        total_requests = self._stats["cache_hits"] + self._stats["cache_misses"]
        hit_rate = (
            self._stats["cache_hits"] / total_requests
            if total_requests > 0
            else 0.0
        )

        return {
            "cache_hits": self._stats["cache_hits"],
            "cache_misses": self._stats["cache_misses"],
            "total_requests": total_requests,
            "hit_rate": round(hit_rate, 3),
        }

    def get_cost_stats(self) -> dict[str, Any]:
        """Get cost tracking statistics.

        Returns:
            Dictionary with cost metrics
        """
        cost_stats = self.cost_tracker.get_stats()

        return {
            "requests_made": self._stats["requests_made"],
            "total_cost": cost_stats.get("total_cost", 0),
            "remaining_budget": cost_stats.get("remaining_budget", 0),
            "budget_used_percent": cost_stats.get("budget_used_percent", 0),
        }

    def get_stats(self) -> dict[str, Any]:
        """Get all client statistics.

        Returns:
            Dictionary with all metrics
        """
        cache_stats = self.get_cache_stats()
        cost_stats = self.get_cost_stats()

        return {
            **self._stats,
            "cache": cache_stats,
            "cost": cost_stats,
        }
