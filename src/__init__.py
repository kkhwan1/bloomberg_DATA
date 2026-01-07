"""
Bloomberg Data Crawler - Main Package

A modular system for crawling, parsing, and storing financial data from Bloomberg.

Modules:
    clients: HTTP clients and API wrappers for data retrieval
    parsers: HTML/JSON parsing logic for different asset types
    orchestrator: Workflow coordination and scheduling
    normalizer: Data normalization and standardization
    storage: Database operations and data persistence
    utils: Shared utilities and helpers
"""

__version__ = "0.1.0"
__author__ = "Bloomberg Data Team"

__all__ = [
    "__version__",
    "__author__",
]
