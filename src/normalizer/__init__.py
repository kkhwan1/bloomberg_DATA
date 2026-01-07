"""
Normalizer Module

Data normalization, standardization, and transformation.

Components:
    - MarketQuote: Normalized market data schema
    - QuoteCollection: Collection of market quotes
    - DataTransformer: Multi-source data transformation
    - AssetClass: Asset classification enum
    - DataSource: Data provider enum
    - MarketStatus: Trading status enum
"""

from .schemas import (
    AssetClass,
    DataSource,
    MarketQuote,
    MarketStatus,
    QuoteCollection,
)
from .transformer import DataTransformer

__all__ = [
    "MarketQuote",
    "QuoteCollection",
    "DataTransformer",
    "AssetClass",
    "DataSource",
    "MarketStatus",
]
