import os
from typing import Any, Dict

import yaml
from dotenv import load_dotenv

from .config_schema import get_missing_required_vars, get_remediation_message


def load_config(config_path: str = "config.yaml") -> Dict[str, Any]:
    # Load .env file if present
    load_dotenv()

    try:
        with open(config_path) as f:
            raw = yaml.safe_load(f)
        if raw is None:
            raise ValueError(f"Config file {config_path} is empty")
        if not isinstance(raw, dict):
            raise ValueError(f"Config file {config_path} must contain a dictionary")

        expanded_config = _expand_env(raw)
        return validate_config(expanded_config)
    except FileNotFoundError:
        raise FileNotFoundError(f"Config file not found: {config_path}") from None
    except yaml.YAMLError as e:
        raise ValueError(f"Invalid YAML in config file {config_path}: {e}") from e


def validate_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """Validate configuration and check for missing required environment variables."""
    missing_vars = get_missing_required_vars(os.environ)

    if missing_vars:
        remediation = get_remediation_message(missing_vars)
        raise ValueError(f"Configuration validation failed:\n{remediation}")

    return config


def _expand_env(d: Dict[str, Any]) -> Dict[str, Any]:
    for key, val in d.items():
        if isinstance(val, dict):
            d[key] = _expand_env(val)
        elif isinstance(val, list):
            d[key] = [_expand_env_value(item) for item in val]
        elif isinstance(val, str) and val.startswith("${") and val.endswith("}") and len(val) > 3:
            d[key] = os.getenv(val[2:-1], "")
    return d


def _expand_env_value(val: Any) -> Any:
    if isinstance(val, dict):
        return _expand_env(val)
    elif isinstance(val, str) and val.startswith("${") and val.endswith("}") and len(val) > 3:
        return os.getenv(val[2:-1], "")
    return val
