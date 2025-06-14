"""
Tests for connector configurations.
"""
import pytest
from pydantic import ValidationError

from src.connectors.configs.base import BaseConnectorConfig
from src.connectors.configs.rss import RSSConfig


class TestBaseConnectorConfig:
    """Tests for BaseConnectorConfig."""
    
    def test_default_values(self):
        """Test default configuration values."""
        config = BaseConnectorConfig()
        assert config.enabled is True
        assert config.fetch_interval_minutes == 60
        assert config.max_items_per_fetch == 50
        assert config.retry_attempts == 3
        assert config.timeout_seconds == 30
        assert config.custom_headers is None
    
    def test_custom_values(self):
        """Test custom configuration values."""
        config = BaseConnectorConfig(
            enabled=False,
            fetch_interval_minutes=30,
            max_items_per_fetch=100,
            retry_attempts=5,
            timeout_seconds=60,
            custom_headers={"Authorization": "Bearer token"}
        )
        assert config.enabled is False
        assert config.fetch_interval_minutes == 30
        assert config.max_items_per_fetch == 100
        assert config.retry_attempts == 5
        assert config.timeout_seconds == 60
        assert config.custom_headers == {"Authorization": "Bearer token"}
    
    def test_validation_forbids_extra_fields(self):
        """Test that extra fields are not allowed."""
        with pytest.raises(ValidationError) as exc_info:
            BaseConnectorConfig(unknown_field="value")
        assert "Extra inputs are not permitted" in str(exc_info.value)
    
    def test_type_validation(self):
        """Test type validation."""
        with pytest.raises(ValidationError):
            BaseConnectorConfig(enabled="not a bool")
        
        with pytest.raises(ValidationError):
            BaseConnectorConfig(fetch_interval_minutes="not an int")


class TestRSSConfig:
    """Tests for RSSConfig."""
    
    def test_inherits_base_config(self):
        """Test that RSSConfig inherits from BaseConnectorConfig."""
        config = RSSConfig()
        # Check base fields
        assert config.enabled is True
        assert config.fetch_interval_minutes == 60
        # Check RSS-specific fields
        assert config.parse_full_content is False
        assert config.filter_keywords is None
        assert config.exclude_keywords is None
    
    def test_rss_specific_fields(self):
        """Test RSS-specific configuration fields."""
        config = RSSConfig(
            parse_full_content=True,
            filter_keywords=["AI", "machine learning"],
            exclude_keywords=["spam", "advertisement"]
        )
        assert config.parse_full_content is True
        assert config.filter_keywords == ["AI", "machine learning"]
        assert config.exclude_keywords == ["spam", "advertisement"]
    
    def test_empty_keyword_lists(self):
        """Test empty keyword lists."""
        config = RSSConfig(filter_keywords=[], exclude_keywords=[])
        assert config.filter_keywords == []
        assert config.exclude_keywords == []