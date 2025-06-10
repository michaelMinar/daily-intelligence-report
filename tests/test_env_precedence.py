"""Test environment variable precedence and validation."""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from src.models.config import Settings


class TestEnvPrecedence:
    """Test environment variable precedence: env vars > .env > defaults."""

    @pytest.mark.parametrize("env_vars,expected_token", [
        ({"DIR_X_API_TOKEN": "env_token", "DIR_EMAIL_PASS": "env_pass", "DIR_TRANSCRIPT_API_KEY": "env_key"}, "env_token"),
        ({"DIR_X_API_TOKEN": "override_token", "DIR_EMAIL_PASS": "env_pass", "DIR_TRANSCRIPT_API_KEY": "env_key"}, "override_token"),
    ])
    def test_env_vars_override_yaml(self, env_vars, expected_token, monkeypatch):
        """Test that environment variables override YAML config values."""
        # Set environment variables
        for key, value in env_vars.items():
            monkeypatch.setenv(key, value)
        
        # Create temporary YAML config
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("""
auth:
  x_bearer_token: ${DIR_X_API_TOKEN}
  imap_password: ${DIR_EMAIL_PASS}
transcription:
  provider: whisper
  api_key: ${DIR_TRANSCRIPT_API_KEY}
""")
            temp_path = f.name

        try:
            config = Settings.from_yaml(temp_path)
            assert config.auth.x_bearer_token == expected_token
        finally:
            os.unlink(temp_path)

    def test_dotenv_file_support(self, monkeypatch, tmp_path):
        """Test that .env file variables are loaded."""
        # Create .env file
        env_file = tmp_path / ".env"
        env_file.write_text("""
DIR_X_API_TOKEN=dotenv_token
DIR_EMAIL_PASS=dotenv_pass
DIR_TRANSCRIPT_API_KEY=dotenv_key
""")
        
        # Create YAML config
        config_file = tmp_path / "config.yaml"
        config_file.write_text("""
auth:
  x_bearer_token: ${DIR_X_API_TOKEN}
  imap_password: ${DIR_EMAIL_PASS}
transcription:
  provider: whisper
  api_key: ${DIR_TRANSCRIPT_API_KEY}
""")

        # Change to temp directory so .env is found
        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            config = Settings.from_yaml(str(config_file))
            assert config.auth.x_bearer_token == "dotenv_token"
            assert config.auth.imap_password == "dotenv_pass"
            assert config.transcription.api_key == "dotenv_key"
        finally:
            os.chdir(original_cwd)

    def test_env_vars_override_dotenv(self, monkeypatch, tmp_path):
        """Test that environment variables override .env file values."""
        # Set environment variable
        monkeypatch.setenv("DIR_X_API_TOKEN", "env_override")
        monkeypatch.setenv("DIR_EMAIL_PASS", "env_pass")
        monkeypatch.setenv("DIR_TRANSCRIPT_API_KEY", "env_key")
        
        # Create .env file with different value
        env_file = tmp_path / ".env"
        env_file.write_text("DIR_X_API_TOKEN=dotenv_token\n")
        
        # Create YAML config
        config_file = tmp_path / "config.yaml"
        config_file.write_text("""
auth:
  x_bearer_token: ${DIR_X_API_TOKEN}
  imap_password: ${DIR_EMAIL_PASS}
transcription:
  provider: whisper
  api_key: ${DIR_TRANSCRIPT_API_KEY}
""")

        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            config = Settings.from_yaml(str(config_file))
            assert config.auth.x_bearer_token == "env_override"  # env wins over .env
        finally:
            os.chdir(original_cwd)


class TestConfigValidation:
    """Test configuration validation and error handling."""

    def test_missing_required_env_vars_raises_error(self, monkeypatch):
        """Test that missing required environment variables raise validation errors."""
        # Clear all relevant env vars
        for var in ["DIR_X_API_TOKEN", "DIR_EMAIL_PASS", "DIR_TRANSCRIPT_API_KEY"]:
            monkeypatch.delenv(var, raising=False)
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("""
auth:
  x_bearer_token: ${DIR_X_API_TOKEN}
  imap_password: ${DIR_EMAIL_PASS}
transcription:
  provider: whisper
  api_key: ${DIR_TRANSCRIPT_API_KEY}
""")
            temp_path = f.name

        try:
            with pytest.raises(ValueError, match="Required authentication field cannot be empty"):
                Settings.from_yaml(temp_path)
        finally:
            os.unlink(temp_path)

    @pytest.mark.parametrize("malformed_value", [
        "",
        "   ",
        "\t\n",
    ])
    def test_malformed_env_values_raise_error(self, malformed_value, monkeypatch):
        """Test that malformed environment variable values raise validation errors."""
        monkeypatch.setenv("DIR_X_API_TOKEN", malformed_value)
        monkeypatch.setenv("DIR_EMAIL_PASS", "valid_pass")
        monkeypatch.setenv("DIR_TRANSCRIPT_API_KEY", "valid_key")
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("""
auth:
  x_bearer_token: ${DIR_X_API_TOKEN}
  imap_password: ${DIR_EMAIL_PASS}
transcription:
  provider: whisper
  api_key: ${DIR_TRANSCRIPT_API_KEY}
""")
            temp_path = f.name

        try:
            with pytest.raises(ValueError, match="Required authentication field cannot be empty"):
                Settings.from_yaml(temp_path)
        finally:
            os.unlink(temp_path)

    def test_valid_config_loads_successfully(self, monkeypatch):
        """Test that valid configuration loads without errors."""
        monkeypatch.setenv("DIR_X_API_TOKEN", "valid_token")
        monkeypatch.setenv("DIR_EMAIL_PASS", "valid_pass")
        monkeypatch.setenv("DIR_TRANSCRIPT_API_KEY", "valid_key")
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("""
storage:
  sqlite_path: "./data/test.db"
auth:
  x_bearer_token: ${DIR_X_API_TOKEN}
  imap_password: ${DIR_EMAIL_PASS}
transcription:
  provider: whisper
  api_key: ${DIR_TRANSCRIPT_API_KEY}
llm:
  provider: ollama
  model: llama3:8b
""")
            temp_path = f.name

        try:
            config = Settings.from_yaml(temp_path)
            assert config.auth.x_bearer_token == "valid_token"
            assert config.auth.imap_password == "valid_pass"
            assert config.transcription.api_key == "valid_key"
            assert config.storage.sqlite_path == "./data/test.db"
            assert config.llm.provider == "ollama"
        finally:
            os.unlink(temp_path)


class TestErrorMessages:
    """Test quality of error messages and remediation guidance."""

    def test_file_not_found_error_message(self):
        """Test that missing config file produces helpful error message."""
        with pytest.raises(FileNotFoundError, match="Config file not found: nonexistent.yaml"):
            Settings.from_yaml("nonexistent.yaml")

    def test_invalid_yaml_error_message(self):
        """Test that invalid YAML produces helpful error message."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("invalid: yaml: content: [")
            temp_path = f.name

        try:
            with pytest.raises(ValueError, match="Invalid YAML"):
                Settings.from_yaml(temp_path)
        finally:
            os.unlink(temp_path)

    def test_empty_config_error_message(self):
        """Test that empty config file produces helpful error message."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("")
            temp_path = f.name

        try:
            with pytest.raises(ValueError, match="Config file .* is empty"):
                Settings.from_yaml(temp_path)
        finally:
            os.unlink(temp_path)