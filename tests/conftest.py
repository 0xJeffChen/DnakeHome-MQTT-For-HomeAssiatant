"""Fixtures for testing."""
import pytest

@pytest.fixture
def hass():
    """Mock Home Assistant instance."""
    from unittest.mock import MagicMock
    return MagicMock()
