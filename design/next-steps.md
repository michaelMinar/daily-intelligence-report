# Configuration System Implementation Plan

This document outlines how to implement and integrate the `config.yaml` configuration system into the Daily Intelligence Report project.

## Goals

- Centralize runtime parameters.
- Allow environment-specific overrides.
- Securely manage secrets via environment variables or keychain references.

---

## Files Created

- `config.yaml`: Project-level YAML file for all configurable values.
- `src/intel/config_loader.py`: Utility for loading and parsing the config file with environment variable support.

---

## 1. config.yaml Structure

```yaml
# Runtime paths
storage:
  sqlite_path: "./data/dev/intel.db"

logging:
  log_dir: "./logs"

# Ingest targets
ingest:
  rss_feeds:
    - "https://example.com/rss"
  x_accounts:
    - "elonmusk"
  email:
    server: "imap.gmail.com"
    port: 993
    username: "user@example.com"
    use_ssl: true
  podcasts:
    - "https://example.com/feed.xml"
  youtube_channels:
    - "UC1234567890abcdef"

# Auth (read from environment)
auth:
  x_bearer_token: "${X_API_TOKEN}"
  imap_password: "${EMAIL_PASS}"

# Transcription service
transcription:
  provider: "whisper"
  api_key: "${TRANSCRIPT_API_KEY}"

# Embeddings & LLMs
embedding:
  model: "sentence-transformers/all-MiniLM-L6-v2"

llm:
  provider: "ollama"
  model: "llama3:8b"

# Report output
output:
  report_dir: "~/DailyBriefs"
  email_enabled: false
  email_recipients: []
```

---

## 2. config_loader.py

File: `src/intel/config_loader.py`

```python
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
```

---

## 3. Integration Points

Update the following modules to consume values from `load_config()`:
- `init_db.py` — use `config["storage"]["sqlite_path"]`
- `logging_config.py` — point to `config["logging"]["log_dir"]`
- Ingest modules — pull in source targets and secrets from config
- Output & summarization steps — check `config["output"]` for delivery paths

---

## 4. Optional Extensions

- Add Pydantic-based schema validation in `src/intel/config.py`
- Support environment-specific config like `config.dev.yaml`, `config.prod.yaml`

---

## 5. Developer Notes

- Always commit a non-secret template (like `config.sample.yaml`)
- Use `.env` or keychain to store sensitive values, not the YAML file


---

## 6. Supporting Both Local and Cloud LLMs

### Config Flexibility

The `llm` section of `config.yaml` is designed to support both local models via [Ollama](https://ollama.com) and remote models via cloud APIs such as OpenAI, Anthropic, or Google:

**Local (Default)**

```yaml
llm:
  provider: "ollama"
  model: "llama3:8b"
```

**Cloud Example (OpenAI)**

```yaml
llm:
  provider: "openai"
  model: "gpt-4-turbo"
  api_key: "${OPENAI_API_KEY}"
  base_url: "https://api.openai.com/v1"
  temperature: 0.7
  max_tokens: 1024
```

**Cloud Example (Anthropic)**

```yaml
llm:
  provider: "anthropic"
  model: "claude-3-sonnet"
  api_key: "${ANTHROPIC_API_KEY}"
  temperature: 0.5
  max_tokens: 2048
```

---

### Adapter Strategy

Create a file `src/pipeline/llm_adapter.py` with logic to dispatch between providers:

```python
from intel.config_loader import load_config

config = load_config()
llm_cfg = config["llm"]

def get_llm_client():
    provider = llm_cfg["provider"]
    if provider == "ollama":
        return OllamaClient(model=llm_cfg["model"])
    elif provider == "openai":
        return OpenAIClient(api_key=llm_cfg["api_key"], model=llm_cfg["model"])
    elif provider == "anthropic":
        return AnthropicClient(api_key=llm_cfg["api_key"], model=llm_cfg["model"])
    else:
        raise ValueError(f"Unsupported LLM provider: {provider}")
```

Define a common `LLMClient` interface for `.generate(text)` to standardize usage downstream.

---

### Best Practices

- Keep secrets out of `config.yaml` — use `${...}` and environment variables.
- Write separate adapter classes per provider to isolate logic.
- Fail fast with informative errors if config is incomplete or invalid.
