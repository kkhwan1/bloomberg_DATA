"""
Parsers Module

HTML and JSON parsing logic for different asset types from Bloomberg.

Components:
    - BaseParser: Abstract base class for all parsers
    - StockParser: Parser for stock/equity data
    - ForexParser: Parser for foreign exchange data
    - CommodityParser: Parser for commodity data
    - BondParser: Parser for bond/fixed income data
    - ParserFactory: Factory for creating appropriate parser instances
"""

__all__ = [
    "BaseParser",
    "StockParser",
    "ForexParser",
    "CommodityParser",
    "BondParser",
    "ParserFactory",
]

# Lazy imports to avoid circular dependencies
def __getattr__(name):
    if name in __all__:
        # Import will be added when actual classes are implemented
        raise ImportError(f"{name} not yet implemented")
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
