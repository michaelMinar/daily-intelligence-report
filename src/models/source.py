"""Source model for content sources like RSS feeds, Twitter, etc."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict, Field


class SourceType(str, Enum):
    """Supported source types."""

    RSS = "rss"
    TWITTER = "twitter"
    EMAIL = "email"
    PODCAST = "podcast"
    YOUTUBE = "youtube"


class Source(BaseModel):
    """Model for content sources."""

    id: Optional[int] = None
    type: SourceType
    identifier: str = Field(
        ...,
        description="Generic identifier: URL for RSS/YouTube, handle for Twitter, email for IMAP",
    )
    name: str = Field(..., description="Human-readable name for the source")
    config: Optional[Dict[str, Any]] = Field(
        default=None, description="Source-specific configuration"
    )
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    active: bool = Field(default=True, description="Whether the source is active")
    
    @property
    def typed_config(self):
        """Return strongly-typed configuration object."""
        from src.connectors.configs.base import BaseConnectorConfig
        from src.connectors.configs.rss import RSSConfig
        
        # Map source types to config classes
        config_map = {
            SourceType.RSS: RSSConfig,
            # Add other mappings as we implement them
        }
        
        config_class = config_map.get(self.type, BaseConnectorConfig)
        return config_class(**self.config) if self.config else config_class()

    model_config = ConfigDict(json_encoders={datetime: lambda v: v.isoformat() if v else None})

    def __str__(self) -> str:
        """String representation."""
        return f"{self.name} ({self.type.value})"

    def __repr__(self) -> str:
        """Developer representation."""
        return f"Source(id={self.id}, type={self.type.value}, name='{self.name}')"
