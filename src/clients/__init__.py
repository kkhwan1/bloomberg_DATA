"""
HTTP Clients Module

Provides HTTP clients and API wrappers for fetching data from Bloomberg and other sources.

Components:
    - BrightDataClient: Async client for Bright Data Web Unlocker API
    - BrightDataClientConfig: Configuration for Bright Data client
    - YFinanceClient: Yahoo Finance data client (free data source)
    - AuthError: Authentication error exception
    - ServerError: Server error exception
"""

from .bright_data import (
    AuthError,
    BrightDataClient,
    BrightDataClientConfig,
    ServerError,
)
from .yfinance_client import YFinanceClient

__all__ = [
    "BrightDataClient",
    "BrightDataClientConfig",
    "YFinanceClient",
    "AuthError",
    "ServerError",
]
