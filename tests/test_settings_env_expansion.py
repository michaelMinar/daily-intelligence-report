"""Tests for Settings environment variable expansion."""

import os
import tempfile
from pathlib import Path

import pytest

from src.models.config import Settings


class TestSettingsEnvExpansion:
    """Test Settings._expand_env_vars method functionality."""

    def test_expand_simple_string(self, monkeypatch):
        """Test Settings._expand_env_vars expands simple environment variable"""
        monkeypatch.setenv("TEST_VAR", "expanded_value")

        config = {"key": "${TEST_VAR}"}
        result = Settings._expand_env_vars(config)
        assert result["key"] == "expanded_value"

    def test_expand_missing_env_var(self):
        """Test Settings._expand_env_vars returns None for missing env var"""
        config = {"key": "${MISSING_VAR}"}
        result = Settings._expand_env_vars(config)
        assert result["key"] is None

    def test_expand_nested_dict(self, monkeypatch):
        """Test Settings._expand_env_vars recursively expands nested dictionaries"""
        monkeypatch.setenv("NESTED_VAR", "nested_value")

        config = {"level1": {"level2": {"key": "${NESTED_VAR}"}}}
        result = Settings._expand_env_vars(config)
        assert result["level1"]["level2"]["key"] == "nested_value"

    def test_expand_list_with_env_vars(self, monkeypatch):
        """Test Settings._expand_env_vars expands environment variables in lists"""
        monkeypatch.setenv("LIST_VAR1", "value1")
        monkeypatch.setenv("LIST_VAR2", "value2")

        config = {"items": ["${LIST_VAR1}", "static_value", "${LIST_VAR2}"]}
        result = Settings._expand_env_vars(config)
        assert result["items"] == ["value1", "static_value", "value2"]

    def test_expand_list_with_nested_dicts(self, monkeypatch):
        """Test Settings._expand_env_vars expands env vars in dicts within lists"""
        monkeypatch.setenv("DICT_VAR", "dict_value")

        config = {"items": [{"key": "${DICT_VAR}"}, {"other": "static"}]}
        result = Settings._expand_env_vars(config)
        assert result["items"][0]["key"] == "dict_value"
        assert result["items"][1]["other"] == "static"

    def test_non_placeholder_strings_unchanged(self):
        """Test Settings._expand_env_vars leaves non-placeholder strings unchanged"""
        config = {
            "normal_string": "just text",
            "partial_placeholder": "prefix${VAR}",
            "not_closed": "${VAR",
            "not_opened": "VAR}",
            "empty_placeholder": "${}",
        }
        result = Settings._expand_env_vars(config)
        assert result["normal_string"] == "just text"
        assert result["partial_placeholder"] == "prefix${VAR}"
        assert result["not_closed"] == "${VAR"
        assert result["not_opened"] == "VAR}"
        assert result["empty_placeholder"] == "${}"

    def test_mixed_data_types(self, monkeypatch):
        """Test Settings._expand_env_vars handles mixed data types correctly"""
        monkeypatch.setenv("STRING_VAR", "string_value")

        config = {
            "string_with_env": "${STRING_VAR}",
            "plain_string": "no_env",
            "integer": 42,
            "boolean": True,
            "null_value": None,
            "float_value": 3.14,
            "nested": {"list_with_env": ["${STRING_VAR}", 123]},
        }
        result = Settings._expand_env_vars(config)
        assert result["string_with_env"] == "string_value"
        assert result["plain_string"] == "no_env"
        assert result["integer"] == 42
        assert result["boolean"] is True
        assert result["null_value"] is None
        assert result["float_value"] == 3.14
        assert result["nested"]["list_with_env"] == ["string_value", 123]


class TestSettingsFromYamlIntegration:
    """Integration tests for Settings.from_yaml with environment expansion."""

    def test_from_yaml_with_env_vars(self, monkeypatch):
        """Test Settings.from_yaml successfully loads and expands environment variables"""
        monkeypatch.setenv("DIR_X_API_TOKEN", "test_x_token")
        monkeypatch.setenv("DIR_EMAIL_PASS", "test_email_pass")
        monkeypatch.setenv("DIR_TRANSCRIPT_API_KEY", "test_transcript_key")

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(
                """
storage:
  sqlite_path: "./data/test.db"
auth:
  x_bearer_token: "${DIR_X_API_TOKEN}"
  imap_password: "${DIR_EMAIL_PASS}"
transcription:
  provider: "whisper"
  api_key: "${DIR_TRANSCRIPT_API_KEY}"
"""
            )
            temp_path = f.name

        try:
            settings = Settings.from_yaml(temp_path)
            assert settings.auth.x_bearer_token == "test_x_token"
            assert settings.auth.imap_password == "test_email_pass"
            assert settings.transcription.api_key == "test_transcript_key"
            assert settings.storage.sqlite_path == "./data/test.db"
        finally:
            os.unlink(temp_path)

    def test_from_yaml_with_missing_env_vars(self):
        """Test Settings.from_yaml handles missing environment variables"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(
                """
storage:
  sqlite_path: "./data/test.db"
auth:
  x_bearer_token: "${MISSING_X_TOKEN}"
  imap_password: "${MISSING_EMAIL_PASS}"
"""
            )
            temp_path = f.name

        try:
            settings = Settings.from_yaml(temp_path)
            # Missing env vars should result in None values
            assert settings.auth.x_bearer_token is None
            assert settings.auth.imap_password is None
            assert settings.storage.sqlite_path == "./data/test.db"
        finally:
            os.unlink(temp_path)

    def test_from_yaml_with_dotenv_file(self, monkeypatch):
        """Test Settings.from_yaml loads from .env file"""
        # Create temporary directory for config and .env files
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create .env file
            env_file = temp_path / ".env"
            env_file.write_text(
                """DIR_X_API_TOKEN=dotenv_x_token
DIR_EMAIL_PASS=dotenv_email_pass
"""
            )
            
            # Create config file
            config_file = temp_path / "config.yaml"
            config_file.write_text(
                """
auth:
  x_bearer_token: "${DIR_X_API_TOKEN}"
  imap_password: "${DIR_EMAIL_PASS}"
"""
            )
            
            settings = Settings.from_yaml(str(config_file))
            assert settings.auth.x_bearer_token == "dotenv_x_token"
            assert settings.auth.imap_password == "dotenv_email_pass"

    def test_from_yaml_env_precedence_over_dotenv(self, monkeypatch):
        """Test that environment variables take precedence over .env file"""
        # Set env var
        monkeypatch.setenv("DIR_X_API_TOKEN", "env_var_token")
        
        # Create temporary directory for config and .env files
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create .env file with different value
            env_file = temp_path / ".env"
            env_file.write_text("DIR_X_API_TOKEN=dotenv_token")
            
            # Create config file
            config_file = temp_path / "config.yaml"
            config_file.write_text(
                """
auth:
  x_bearer_token: "${DIR_X_API_TOKEN}"
"""
            )
            
            settings = Settings.from_yaml(str(config_file))
            # Environment variable should take precedence
            assert settings.auth.x_bearer_token == "env_var_token"