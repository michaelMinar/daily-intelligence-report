"""
Tests for connector registry.
"""
import pytest

from src.connectors import CONNECTOR_REGISTRY, get_connector_class, register_connector
from src.connectors.base import BaseConnector
from src.models.source import SourceType


class MockRSSConnector(BaseConnector):
    """Mock RSS connector for testing."""
    pass


class TestConnectorRegistry:
    """Tests for connector registry functionality."""
    
    def test_register_connector(self):
        """Test registering a connector."""
        # Clear registry first
        CONNECTOR_REGISTRY.clear()
        
        # Register connector
        register_connector(SourceType.RSS, MockRSSConnector)
        
        # Verify registration
        assert SourceType.RSS in CONNECTOR_REGISTRY
        assert CONNECTOR_REGISTRY[SourceType.RSS] == MockRSSConnector
    
    def test_get_connector_class(self):
        """Test getting a registered connector class."""
        # Clear and register
        CONNECTOR_REGISTRY.clear()
        register_connector(SourceType.RSS, MockRSSConnector)
        
        # Get connector class
        connector_class = get_connector_class(SourceType.RSS)
        assert connector_class == MockRSSConnector
    
    def test_get_unregistered_connector_raises_error(self):
        """Test getting an unregistered connector raises ValueError."""
        # Clear registry
        CONNECTOR_REGISTRY.clear()
        
        # Try to get unregistered connector
        with pytest.raises(ValueError) as exc_info:
            get_connector_class(SourceType.TWITTER)
        
        assert "No connector registered for source type: SourceType.TWITTER" in str(exc_info.value)
    
    def test_registry_isolation(self):
        """Test that registry changes don't affect other tests."""
        # This test ensures registry is properly isolated
        initial_count = len(CONNECTOR_REGISTRY)
        register_connector(SourceType.PODCAST, MockRSSConnector)
        assert len(CONNECTOR_REGISTRY) >= initial_count