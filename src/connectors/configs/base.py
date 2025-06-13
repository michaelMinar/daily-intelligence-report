"""
Base configuration class for all connectors.
"""
from typing import Optional, Dict
from pydantic import BaseModel, Field


class BaseConnectorConfig(BaseModel):
    """Base configuration for all connector types."""
    
    enabled: bool = Field(default=True, description="Whether this connector is enabled")
    fetch_interval_minutes: int = Field(default=60, description="How often to fetch new content")
    max_items_per_fetch: Optional[int] = Field(default=50, description="Maximum items to fetch per run")
    retry_attempts: int = Field(default=3, description="Number of retry attempts on failure")
    timeout_seconds: int = Field(default=30, description="Request timeout in seconds")
    custom_headers: Optional[Dict[str, str]] = Field(default=None, description="Custom HTTP headers")
    
    class Config:
        extra = "forbid"  # Fail if unknown fields are provided