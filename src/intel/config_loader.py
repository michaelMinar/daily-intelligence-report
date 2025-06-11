from typing import Any, Dict

import yaml


def load_config(config_path: str = "config.yaml") -> Dict[str, Any]:
    """Load YAML configuration file.
    
    Note: This function now only handles YAML parsing. 
    For full configuration with environment variable handling, use Settings.from_yaml() instead.
    """
    try:
        with open(config_path) as f:
            raw = yaml.safe_load(f)
        if raw is None:
            raise ValueError(f"Config file {config_path} is empty")
        if not isinstance(raw, dict):
            raise ValueError(f"Config file {config_path} must contain a dictionary")

        return raw
    except FileNotFoundError:
        raise FileNotFoundError(f"Config file not found: {config_path}") from None
    except yaml.YAMLError as e:
        raise ValueError(f"Invalid YAML in config file {config_path}: {e}") from e
