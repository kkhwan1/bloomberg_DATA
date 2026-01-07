"""
Test Fixtures

Shared test data, mock responses, and fixture utilities.

Components:
    - Mock Bloomberg API responses
    - Sample HTML pages for parser testing
    - Test database fixtures
    - Configuration fixtures
"""

__all__ = [
    "load_fixture",
    "get_mock_response",
    "create_test_database",
]

import json
from pathlib import Path
from typing import Any, Dict


def load_fixture(filename: str) -> str:
    """
    Load fixture file content.

    Args:
        filename: Name of fixture file

    Returns:
        File content as string
    """
    fixture_path = Path(__file__).parent / filename
    return fixture_path.read_text(encoding="utf-8")


def get_mock_response(asset_type: str, endpoint: str) -> Dict[str, Any]:
    """
    Get mock API response for testing.

    Args:
        asset_type: Type of asset (stock, forex, commodity, bond)
        endpoint: API endpoint name

    Returns:
        Mock response as dictionary
    """
    fixture_file = f"mock_responses/{asset_type}_{endpoint}.json"
    content = load_fixture(fixture_file)
    return json.loads(content)


def create_test_database() -> str:
    """
    Create temporary test database.

    Returns:
        Database connection string
    """
    # Implementation will be added when database layer is ready
    raise NotImplementedError("Test database creation not yet implemented")
