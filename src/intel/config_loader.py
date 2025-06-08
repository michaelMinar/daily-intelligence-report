import os
import yaml
from pathlib import Path

def load_config(config_path="config.yaml"):
    with open(config_path) as f:
        raw = yaml.safe_load(f)
    return _expand_env(raw)

def _expand_env(d):
    for key, val in d.items():
        if isinstance(val, dict):
            d[key] = _expand_env(val)
        elif isinstance(val, str) and val.startswith("${") and val.endswith("}"):
            d[key] = os.getenv(val[2:-1], "")
    return d
