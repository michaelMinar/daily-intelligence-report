import os
from typing import Any, Dict, List, Union

import yaml


def load_config(config_path: str = "config.yaml") -> Dict[str, Any]:
    try:
        with open(config_path) as f:
            raw = yaml.safe_load(f)
        if raw is None:
            raise ValueError(f"Config file {config_path} is empty")
        if not isinstance(raw, dict):
            raise ValueError(f"Config file {config_path} must contain a dictionary")
        return _expand_env(raw)
    except FileNotFoundError:
        raise FileNotFoundError(f"Config file not found: {config_path}") from None
    except yaml.YAMLError as e:
        raise ValueError(f"Invalid YAML in config file {config_path}: {e}") from e

def _expand_env(d: Dict[str, Any]) -> Dict[str, Any]:
    for key, val in d.items():
        if isinstance(val, dict):
            d[key] = _expand_env(val)
        elif isinstance(val, list):
            d[key] = [_expand_env_value(item) for item in val]
        elif (
            isinstance(val, str)
            and val.startswith("${")
            and val.endswith("}")
            and len(val) > 3
        ):
            d[key] = os.getenv(val[2:-1], "")
    return d

def _expand_env_value(val: Any) -> Any:
    if isinstance(val, dict):
        return _expand_env(val)
    elif (
        isinstance(val, str)
        and val.startswith("${")
        and val.endswith("}")
        and len(val) > 3
    ):
        return os.getenv(val[2:-1], "")
    return val
