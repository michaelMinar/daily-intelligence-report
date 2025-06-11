import os
import tempfile
from pathlib import Path

import pytest

from src.intel.config_loader import load_config


class TestLoadConfig:
    def test_missing_file(self):
        """Test load_config raises FileNotFoundError for missing file"""
        with pytest.raises(FileNotFoundError, match="Config file not found"):
            load_config("nonexistent.yaml")

    def test_invalid_yaml(self):
        """Test load_config raises ValueError for invalid YAML"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("invalid: yaml: content: [")
            temp_path = f.name

        try:
            with pytest.raises(ValueError, match="Invalid YAML"):
                load_config(temp_path)
        finally:
            os.unlink(temp_path)

    def test_empty_file(self):
        """Test load_config raises ValueError for empty YAML file"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("")
            temp_path = f.name

        try:
            with pytest.raises(ValueError, match="Config file .* is empty"):
                load_config(temp_path)
        finally:
            os.unlink(temp_path)

    def test_non_dict_content(self):
        """Test load_config raises ValueError for non-dict YAML content"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("- item1\n- item2")
            temp_path = f.name

        try:
            with pytest.raises(ValueError, match="must contain a dictionary"):
                load_config(temp_path)
        finally:
            os.unlink(temp_path)

    def test_valid_config_without_env_expansion(self):
        """Test load_config successfully loads config without expanding environment variables"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(
                """
database:
  host: localhost
  password: ${TEST_VAR}
settings:
  debug: true
"""
            )
            temp_path = f.name

        try:
            config = load_config(temp_path)
            # load_config now only parses YAML, doesn't expand env vars
            assert config["database"]["password"] == "${TEST_VAR}"
            assert config["database"]["host"] == "localhost"
            assert config["settings"]["debug"] is True
        finally:
            os.unlink(temp_path)



class TestConfigLoaderIntegration:
    def test_load_actual_config_file(self):
        """Integration test with the actual config.yaml file"""
        config_path = Path(__file__).parent.parent / "config.yaml"
        if config_path.exists():
            # This should not raise any exceptions
            config = load_config(str(config_path))

            # Verify basic structure
            assert isinstance(config, dict)
            assert "storage" in config
            assert "logging" in config
            assert "auth" in config

            # Verify environment variable placeholders are preserved (not expanded)
            assert config["auth"]["x_bearer_token"] == "${DIR_X_API_TOKEN}"
            assert config["auth"]["imap_password"] == "${DIR_EMAIL_PASS}"
