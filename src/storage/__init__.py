"""
Storage Module

Data persistence and storage management for Bloomberg Data Crawler.

Components:
    - CSVWriter: CSV-based storage with daily partitioning
    - JSONWriter: JSON Lines storage with fast serialization
    - DatabaseManager: Database connection and session management (planned)
    - Repository: Generic data access layer (planned)
    - CacheManager: In-memory and disk caching (planned)
"""

from .csv_writer import CSVWriter
from .json_writer import JSONWriter

__all__ = [
    "CSVWriter",
    "JSONWriter",
]
