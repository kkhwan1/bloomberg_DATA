"""
Unit tests for Bright Data API client.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.clients.bright_data import (
    AuthError,
    BrightDataClient,
    BrightDataClientConfig,
    RateLimitError,
    ServerError,
)
from src.utils.exceptions import BudgetExhaustedError


@pytest.fixture
def config():
    """Create test configuration."""
    return BrightDataClientConfig(
        api_token="test_token_123",
        zone="test_zone",
        timeout=5,
        max_retries=3,
        base_delay=0.1,
    )


@pytest.fixture
def mock_cost_tracker():
    """Create mock cost tracker."""
    tracker = MagicMock()
    tracker.can_make_request.return_value = True
    tracker.record_request.return_value = None
    tracker.get_stats.return_value = {
        "requests_made": 0,
        "total_cost": 0,
        "remaining_budget": 5.50,
        "budget_used_percent": 0,
    }
    return tracker


@pytest.fixture
def mock_cache():
    """Create mock cache."""
    cache = MagicMock()
    cache.get = AsyncMock(return_value=None)
    cache.set = AsyncMock(return_value=None)
    return cache


@pytest.fixture
def client(config, mock_cost_tracker, mock_cache):
    """Create test client."""
    return BrightDataClient(config, mock_cost_tracker, mock_cache)


@pytest.mark.asyncio
async def test_client_initialization(config, mock_cost_tracker, mock_cache):
    """Test client initialization."""
    client = BrightDataClient(config, mock_cost_tracker, mock_cache)

    assert client.config == config
    assert client.cost_tracker == mock_cost_tracker
    assert client.cache == mock_cache
    assert client._stats["requests_made"] == 0
    assert client._stats["cache_hits"] == 0

    await client.close()


@pytest.mark.asyncio
async def test_context_manager(config, mock_cost_tracker, mock_cache):
    """Test async context manager."""
    async with BrightDataClient(config, mock_cost_tracker, mock_cache) as client:
        assert client._session is not None
        assert not client._session.closed


@pytest.mark.asyncio
async def test_successful_fetch(client, mock_cost_tracker, mock_cache):
    """Test successful URL fetch."""
    test_url = "https://www.bloomberg.com/quote/AAPL:US"
    expected_html = "<html>Bloomberg data</html>"

    with patch.object(client, "_fetch_with_retry", new_callable=AsyncMock) as mock_fetch:
        mock_fetch.return_value = expected_html

        result = await client.fetch(test_url, use_cache=False)

        assert result == expected_html
        assert client._stats["requests_made"] == 1
        mock_cost_tracker.record_request.assert_called_once()


@pytest.mark.asyncio
async def test_cache_hit(client, mock_cache):
    """Test cache hit scenario."""
    test_url = "https://www.bloomberg.com/quote/AAPL:US"
    cached_html = "<html>Cached data</html>"

    mock_cache.get = AsyncMock(return_value=cached_html)

    result = await client.fetch(test_url, use_cache=True)

    assert result == cached_html
    assert client._stats["cache_hits"] == 1
    assert client._stats["requests_made"] == 0


@pytest.mark.asyncio
async def test_cache_miss(client, mock_cache):
    """Test cache miss scenario."""
    test_url = "https://www.bloomberg.com/quote/AAPL:US"
    expected_html = "<html>Fresh data</html>"

    mock_cache.get = AsyncMock(return_value=None)

    with patch.object(client, "_fetch_with_retry", new_callable=AsyncMock) as mock_fetch:
        mock_fetch.return_value = expected_html

        result = await client.fetch(test_url, use_cache=True)

        assert result == expected_html
        assert client._stats["cache_misses"] == 1
        mock_cache.set.assert_called_once()


@pytest.mark.asyncio
async def test_budget_exhausted(client, mock_cost_tracker):
    """Test budget exhausted error."""
    test_url = "https://www.bloomberg.com/quote/AAPL:US"

    mock_cost_tracker.can_make_request.return_value = False
    mock_cost_tracker.get_stats.return_value = {
        "requests_made": 3666,
        "max_requests": 3666,
        "total_cost": 5.50,
    }

    with pytest.raises(BudgetExhaustedError) as exc_info:
        await client.fetch(test_url, use_cache=False)

    assert "budget exhausted" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_auth_error_401(client):
    """Test authentication error (401)."""
    with patch.object(client, "_make_request", new_callable=AsyncMock) as mock_request:
        mock_request.side_effect = AuthError(
            "Authentication failed: 401",
            status_code=401,
        )

        with pytest.raises(AuthError) as exc_info:
            await client.fetch("https://test.com", use_cache=False)

        assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_rate_limit_retry(client):
    """Test rate limit with retry."""
    test_url = "https://www.bloomberg.com/quote/AAPL:US"
    expected_html = "<html>Success after retry</html>"

    with patch.object(client, "_make_request", new_callable=AsyncMock) as mock_request:
        # First call raises rate limit, second succeeds
        mock_request.side_effect = [
            RateLimitError("Rate limit exceeded", status_code=429),
            expected_html,
        ]

        result = await client._fetch_with_retry(test_url)

        assert result == expected_html
        assert mock_request.call_count == 2
        assert client._stats["retries"] == 1


@pytest.mark.asyncio
async def test_server_error_retry(client):
    """Test server error with retry."""
    test_url = "https://www.bloomberg.com/quote/AAPL:US"
    expected_html = "<html>Success after retry</html>"

    with patch.object(client, "_make_request", new_callable=AsyncMock) as mock_request:
        # First call raises server error, second succeeds
        mock_request.side_effect = [
            ServerError("Server error: 503", status_code=503),
            expected_html,
        ]

        result = await client._fetch_with_retry(test_url)

        assert result == expected_html
        assert mock_request.call_count == 2


@pytest.mark.asyncio
async def test_max_retries_exceeded(client):
    """Test max retries exceeded."""
    test_url = "https://www.bloomberg.com/quote/AAPL:US"

    with patch.object(client, "_make_request", new_callable=AsyncMock) as mock_request:
        # Always raise server error
        mock_request.side_effect = ServerError("Server error: 503", status_code=503)

        with pytest.raises(ServerError):
            await client._fetch_with_retry(test_url)

        assert mock_request.call_count == client.config.max_retries


@pytest.mark.asyncio
async def test_fetch_multiple(client):
    """Test fetching multiple URLs concurrently."""
    urls = [
        "https://www.bloomberg.com/quote/AAPL:US",
        "https://www.bloomberg.com/quote/MSFT:US",
        "https://www.bloomberg.com/quote/GOOGL:US",
    ]

    with patch.object(client, "fetch", new_callable=AsyncMock) as mock_fetch:
        mock_fetch.side_effect = lambda url: f"<html>Content for {url}</html>"

        results = await client.fetch_multiple(urls, max_concurrent=2)

        assert len(results) == 3
        for url in urls:
            assert url in results
            assert "Content for" in results[url]


@pytest.mark.asyncio
async def test_get_cache_stats(client):
    """Test cache statistics."""
    client._stats["cache_hits"] = 10
    client._stats["cache_misses"] = 5

    stats = client.get_cache_stats()

    assert stats["cache_hits"] == 10
    assert stats["cache_misses"] == 5
    assert stats["total_requests"] == 15
    assert stats["hit_rate"] == pytest.approx(0.667, abs=0.01)


@pytest.mark.asyncio
async def test_get_cost_stats(client, mock_cost_tracker):
    """Test cost statistics."""
    client._stats["requests_made"] = 100
    mock_cost_tracker.get_stats.return_value = {
        "total_cost": 0.15,
        "remaining_budget": 5.35,
        "budget_used_percent": 2.7,
    }

    stats = client.get_cost_stats()

    assert stats["requests_made"] == 100
    assert stats["total_cost"] == 0.15
    assert stats["remaining_budget"] == 5.35
    assert stats["budget_used_percent"] == 2.7


@pytest.mark.asyncio
async def test_exponential_backoff(client):
    """Test exponential backoff delay calculation."""
    test_url = "https://www.bloomberg.com/quote/AAPL:US"

    with patch.object(client, "_make_request", new_callable=AsyncMock) as mock_request:
        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            mock_request.side_effect = [
                RateLimitError("Rate limit", status_code=429),
                RateLimitError("Rate limit", status_code=429),
                "<html>Success</html>",
            ]

            await client._fetch_with_retry(test_url)

            # Check that sleep was called with increasing delays
            assert mock_sleep.call_count == 2
            delays = [call[0][0] for call in mock_sleep.call_args_list]
            assert delays[1] > delays[0]  # Second delay should be longer
