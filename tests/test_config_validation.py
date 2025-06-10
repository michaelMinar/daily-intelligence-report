"""Test configuration validation logic."""

import os
from unittest.mock import patch

import pytest

from src.intel.config_schema import (
    get_missing_required_vars,
    get_remediation_message,
    REQUIRED_ENV_VARS
)


class TestConfigSchema:
    """Test configuration schema validation functions."""

    def test_get_missing_required_vars_all_present(self):
        """Test when all required environment variables are present."""
        env_vars = {
            "DIR_X_API_TOKEN": "token1",
            "DIR_EMAIL_PASS": "pass1", 
            "DIR_TRANSCRIPT_API_KEY": "key1"
        }
        missing = get_missing_required_vars(env_vars)
        assert missing == []

    def test_get_missing_required_vars_some_missing(self):
        """Test when some required environment variables are missing."""
        env_vars = {
            "DIR_X_API_TOKEN": "token1",
            # DIR_EMAIL_PASS missing
            "DIR_TRANSCRIPT_API_KEY": "key1"
        }
        missing = get_missing_required_vars(env_vars)
        assert "DIR_EMAIL_PASS" in missing
        assert len(missing) == 1

    def test_get_missing_required_vars_all_missing(self):
        """Test when all required environment variables are missing."""
        env_vars = {}
        missing = get_missing_required_vars(env_vars)
        assert len(missing) == len(REQUIRED_ENV_VARS)
        for var in REQUIRED_ENV_VARS:
            assert var in missing

    def test_get_missing_required_vars_empty_values_considered_missing(self):
        """Test that empty string values are considered missing."""
        env_vars = {
            "DIR_X_API_TOKEN": "",
            "DIR_EMAIL_PASS": "pass1", 
            "DIR_TRANSCRIPT_API_KEY": "key1"
        }
        missing = get_missing_required_vars(env_vars)
        assert "DIR_X_API_TOKEN" in missing

    def test_get_remediation_message_no_missing_vars(self):
        """Test remediation message when no variables are missing."""
        message = get_remediation_message([])
        assert message == ""

    def test_get_remediation_message_single_missing_var(self):
        """Test remediation message for single missing variable."""
        missing_vars = ["DIR_X_API_TOKEN"]
        message = get_remediation_message(missing_vars)
        
        assert "Missing required environment variables: DIR_X_API_TOKEN" in message
        assert "export DIR_X_API_TOKEN=<your_token>" in message
        assert ".env file" in message

    def test_get_remediation_message_multiple_missing_vars(self):
        """Test remediation message for multiple missing variables."""
        missing_vars = ["DIR_X_API_TOKEN", "DIR_EMAIL_PASS"]
        message = get_remediation_message(missing_vars)
        
        assert "DIR_X_API_TOKEN, DIR_EMAIL_PASS" in message
        assert "export DIR_X_API_TOKEN=<your_token>" in message
        assert ".env file" in message


class TestConfigValidationIntegration:
    """Integration tests for configuration validation."""

    def test_config_validation_with_actual_env(self, monkeypatch):
        """Test config validation using actual environment variables."""
        from src.intel.config_loader import validate_config
        
        # Set required environment variables
        monkeypatch.setenv("DIR_X_API_TOKEN", "test_token")
        monkeypatch.setenv("DIR_EMAIL_PASS", "test_pass")
        monkeypatch.setenv("DIR_TRANSCRIPT_API_KEY", "test_key")
        
        # Should not raise any exceptions
        config = {"test": "data"}
        result = validate_config(config)
        assert result == config

    def test_config_validation_missing_env_raises_error(self, monkeypatch):
        """Test that missing environment variables cause validation to fail."""
        from src.intel.config_loader import validate_config
        
        # Clear environment variables
        for var in REQUIRED_ENV_VARS:
            monkeypatch.delenv(var, raising=False)
        
        config = {"test": "data"}
        with pytest.raises(ValueError, match="Configuration validation failed"):
            validate_config(config)

    def test_config_validation_error_includes_remediation(self, monkeypatch):
        """Test that validation error includes helpful remediation message."""
        from src.intel.config_loader import validate_config
        
        # Clear environment variables
        for var in REQUIRED_ENV_VARS:
            monkeypatch.delenv(var, raising=False)
        
        config = {"test": "data"}
        try:
            validate_config(config)
            assert False, "Should have raised ValueError"
        except ValueError as e:
            error_message = str(e)
            assert "Missing required environment variables" in error_message
            assert "export" in error_message
            assert ".env file" in error_message