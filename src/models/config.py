"""Pydantic models for configuration validation."""

import os
from pathlib import Path
from typing import Any, List, Optional

import yaml
from dotenv import load_dotenv
from pydantic import BaseModel, Field, validator


class StorageSettings(BaseModel):
    sqlite_path: str = "./data/dev/intel.db"


class LoggingSettings(BaseModel):
    log_dir: str = "./logs"


class IngestSettings(BaseModel):
    rss_feeds: List[str] = []
    x_accounts: List[str] = []
    podcasts: List[str] = []
    youtube_channels: List[str] = []


class EmailSettings(BaseModel):
    server: str = "imap.gmail.com"
    port: int = 993
    username: str = "user@example.com"
    use_ssl: bool = True


class AuthSettings(BaseModel):
    x_bearer_token: str = Field(..., env="DIR_X_API_TOKEN")
    imap_password: str = Field(..., env="DIR_EMAIL_PASS")

    @validator("x_bearer_token", "imap_password")
    def validate_not_empty(cls, v: str) -> str:
        if not v or v.strip() == "":
            raise ValueError("Required authentication field cannot be empty")
        return v


class TranscriptionSettings(BaseModel):
    provider: str = "whisper"
    api_key: str = Field(..., env="DIR_TRANSCRIPT_API_KEY")

    @validator("api_key")
    def validate_api_key_not_empty(cls, v: str) -> str:
        if not v or v.strip() == "":
            raise ValueError("Transcription API key cannot be empty")
        return v


class EmbeddingSettings(BaseModel):
    model: str = "sentence-transformers/all-MiniLM-L6-v2"


class LLMSettings(BaseModel):
    provider: str = "ollama"
    model: str = "llama3:8b"
    api_key: Optional[str] = Field(None, env="DIR_OPENAI_API_KEY")
    base_url: Optional[str] = None
    temperature: float = 0.7
    max_tokens: int = 1024


class OutputSettings(BaseModel):
    report_dir: str = "~/DailyBriefs"
    email_enabled: bool = False
    email_recipients: List[str] = []


class Settings(BaseModel):
    storage: StorageSettings = StorageSettings()
    logging: LoggingSettings = LoggingSettings()
    ingest: IngestSettings = IngestSettings()
    email: EmailSettings = EmailSettings()
    auth: AuthSettings
    transcription: TranscriptionSettings
    embedding: EmbeddingSettings = EmbeddingSettings()
    llm: LLMSettings = LLMSettings()
    output: OutputSettings = OutputSettings()

    @classmethod
    def from_yaml(cls, config_path: str = "config.yaml") -> "Settings":
        """Factory method to create Settings from YAML file with environment variable expansion."""
        # Load .env file if present (look in same directory as config file and current directory)
        config_dir = Path(config_path).parent
        load_dotenv(config_dir / ".env")  # Try config directory first
        load_dotenv()  # Then try current directory

        try:
            with open(config_path) as f:
                raw_config = yaml.safe_load(f)

            if raw_config is None:
                raise ValueError(f"Config file {config_path} is empty")
            if not isinstance(raw_config, dict):
                raise ValueError(f"Config file {config_path} must contain a dictionary")

            # Expand environment variables
            expanded_config = cls._expand_env_vars(raw_config)

            return cls(**expanded_config)

        except FileNotFoundError:
            raise FileNotFoundError(f"Config file not found: {config_path}") from None
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML in config file {config_path}: {e}") from e

    @staticmethod
    def _expand_env_vars(data: Any) -> Any:
        """Recursively expand environment variables in configuration data."""
        if isinstance(data, dict):
            return {key: Settings._expand_env_vars(value) for key, value in data.items()}
        elif isinstance(data, list):
            return [Settings._expand_env_vars(item) for item in data]
        elif (
            isinstance(data, str) and data.startswith("${") and data.endswith("}") and len(data) > 3
        ):
            env_var = data[2:-1]
            return os.getenv(env_var, "")
        else:
            return data
