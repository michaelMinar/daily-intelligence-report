import os
import tempfile
from pathlib import Path

import pytest

from src.intel.config_loader import _expand_env, load_config


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

    def test_valid_config_with_env_vars(self, monkeypatch):
        """Test load_config successfully loads and expands environment variables"""
        monkeypatch.setenv("TEST_VAR", "test_value")

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
            assert config["database"]["password"] == "test_value"
            assert config["database"]["host"] == "localhost"
            assert config["settings"]["debug"] is True
        finally:
            os.unlink(temp_path)


class TestExpandEnv:
    def test_expand_simple_string(self, monkeypatch):
        """Test _expand_env expands simple environment variable"""
        monkeypatch.setenv("TEST_VAR", "expanded_value")

        config = {"key": "${TEST_VAR}"}
        result = _expand_env(config)
        assert result["key"] == "expanded_value"

    def test_expand_missing_env_var(self):
        """Test _expand_env defaults to empty string for missing env var"""
        config = {"key": "${MISSING_VAR}"}
        result = _expand_env(config)
        assert result["key"] == ""

    def test_expand_nested_dict(self, monkeypatch):
        """Test _expand_env recursively expands nested dictionaries"""
        monkeypatch.setenv("NESTED_VAR", "nested_value")

        config = {"level1": {"level2": {"key": "${NESTED_VAR}"}}}
        result = _expand_env(config)
        assert result["level1"]["level2"]["key"] == "nested_value"

    def test_expand_list_with_env_vars(self, monkeypatch):
        """Test _expand_env expands environment variables in lists"""
        monkeypatch.setenv("LIST_VAR1", "value1")
        monkeypatch.setenv("LIST_VAR2", "value2")

        config = {"items": ["${LIST_VAR1}", "static_value", "${LIST_VAR2}"]}
        result = _expand_env(config)
        assert result["items"] == ["value1", "static_value", "value2"]

    def test_expand_list_with_nested_dicts(self, monkeypatch):
        """Test _expand_env expands env vars in dicts within lists"""
        monkeypatch.setenv("DICT_VAR", "dict_value")

        config = {"items": [{"key": "${DICT_VAR}"}, {"other": "static"}]}
        result = _expand_env(config)
        assert result["items"][0]["key"] == "dict_value"
        assert result["items"][1]["other"] == "static"

    def test_non_placeholder_strings_unchanged(self):
        """Test _expand_env leaves non-placeholder strings unchanged"""
        config = {
            "normal_string": "just text",
            "partial_placeholder": "prefix${VAR}",
            "not_closed": "${VAR",
            "not_opened": "VAR}",
            "empty_placeholder": "${}",
        }
        result = _expand_env(config)
        assert result["normal_string"] == "just text"
        assert result["partial_placeholder"] == "prefix${VAR}"
        assert result["not_closed"] == "${VAR"
        assert result["not_opened"] == "VAR}"
        assert result["empty_placeholder"] == "${}"

    def test_mixed_data_types(self, monkeypatch):
        """Test _expand_env handles mixed data types correctly"""
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
        result = _expand_env(config)
        assert result["string_with_env"] == "string_value"
        assert result["plain_string"] == "no_env"
        assert result["integer"] == 42
        assert result["boolean"] is True
        assert result["null_value"] is None
        assert result["float_value"] == 3.14
        assert result["nested"]["list_with_env"] == ["string_value", 123]


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

            # Verify environment variables are processed (but may be empty)
            assert isinstance(config["auth"]["x_bearer_token"], str)
            assert isinstance(config["auth"]["imap_password"], str)
