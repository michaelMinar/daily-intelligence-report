"""Test configuration validation logic."""


import pytest

from src.intel.config_schema import (
    REQUIRED_ENV_VARS,
    get_missing_required_vars,
    get_remediation_message,
)


class TestConfigSchema:
    """Test configuration schema validation functions."""

    def test_get_missing_required_vars_all_present(self):
        """Test when all required environment variables are present."""
        env_vars = {
            "DIR_X_API_TOKEN": "token1",
            "DIR_EMAIL_PASS": "pass1",
            "DIR_TRANSCRIPT_API_KEY": "key1",
        }
        missing = get_missing_required_vars(env_vars)
        assert missing == []

    def test_get_missing_required_vars_some_missing(self):
        """Test when some required environment variables are missing."""
        env_vars = {
            "DIR_X_API_TOKEN": "token1",
            # DIR_EMAIL_PASS missing
            "DIR_TRANSCRIPT_API_KEY": "key1",
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
            "DIR_TRANSCRIPT_API_KEY": "key1",
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

    def test_settings_validation_with_actual_env(self, monkeypatch):
        """Test that Settings.from_yaml works with valid environment variables."""
        from src.models.config import Settings
        import tempfile
        import os

        # Set required environment variables
        monkeypatch.setenv("DIR_X_API_TOKEN", "test_token")
        monkeypatch.setenv("DIR_EMAIL_PASS", "test_pass")
        monkeypatch.setenv("DIR_TRANSCRIPT_API_KEY", "test_key")

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(
                """
auth:
  x_bearer_token: ${DIR_X_API_TOKEN}
  imap_password: ${DIR_EMAIL_PASS}
transcription:
  provider: whisper
  api_key: ${DIR_TRANSCRIPT_API_KEY}
"""
            )
            temp_path = f.name

        try:
            settings = Settings.from_yaml(temp_path)
            assert settings.auth.x_bearer_token == "test_token"
            assert settings.auth.imap_password == "test_pass"
            assert settings.transcription.api_key == "test_key"
        finally:
            os.unlink(temp_path)

    def test_settings_validation_with_empty_strings_raises_error(self, monkeypatch):
        """Test that empty string environment variables cause validation to fail."""
        from src.models.config import Settings
        import tempfile
        import os

        # Set empty environment variables
        monkeypatch.setenv("DIR_X_API_TOKEN", "")
        monkeypatch.setenv("DIR_EMAIL_PASS", "valid_pass")
        monkeypatch.setenv("DIR_TRANSCRIPT_API_KEY", "valid_key")

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(
                """
auth:
  x_bearer_token: ${DIR_X_API_TOKEN}
  imap_password: ${DIR_EMAIL_PASS}
transcription:
  provider: whisper
  api_key: ${DIR_TRANSCRIPT_API_KEY}
"""
            )
            temp_path = f.name

        try:
            with pytest.raises(ValueError, match="Authentication field cannot be empty string"):
                Settings.from_yaml(temp_path)
        finally:
            os.unlink(temp_path)

    def test_get_missing_required_vars_integration(self, monkeypatch):
        """Test get_missing_required_vars and get_remediation_message functions with actual environment."""
        import os

        # Clear environment variables
        for var in REQUIRED_ENV_VARS:
            monkeypatch.delenv(var, raising=False)

        # Set only some variables
        monkeypatch.setenv("DIR_X_API_TOKEN", "test_token")

        missing = get_missing_required_vars(dict(os.environ))
        assert "DIR_EMAIL_PASS" in missing
        assert "DIR_TRANSCRIPT_API_KEY" in missing
        assert "DIR_X_API_TOKEN" not in missing

        # Test remediation message
        remediation = get_remediation_message(missing)
        assert "Missing required environment variables" in remediation
        assert "export" in remediation
        assert ".env file" in remediation
