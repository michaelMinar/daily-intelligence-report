"""Post model for ingested content."""

import hashlib
from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict, Field, computed_field, model_validator


class Post(BaseModel):
    """Model for ingested content posts."""

    id: Optional[int] = None
    source_id: int = Field(..., description="ID of the source this post came from")
    title: str = Field(..., description="Post title")
    content: str = Field(..., description="Post content/body")
    url: Optional[str] = Field(default=None, description="Original URL of the post")
    published_at: Optional[datetime] = Field(
        default=None, description="When the post was originally published"
    )
    ingested_at: Optional[datetime] = Field(
        default=None, description="When the post was ingested into our system"
    )
    content_hash: Optional[str] = Field(
        default=None, description="SHA-256 hash of content for deduplication"
    )
    source_guid: Optional[str] = Field(
        default=None, description="Original source identifier (RSS GUID, Tweet ID, etc.)"
    )
    metadata_json: Optional[Dict[str, Any]] = Field(
        default=None, description="Additional metadata as JSON"
    )

    @classmethod
    def generate_content_hash(
        cls,
        source_id: int,
        content: str,
        url: Optional[str] = None,
        source_guid: Optional[str] = None,
    ) -> str:
        """Generate composite hash for robust deduplication.
        
        Combines source_id, content, and available identifiers to prevent
        false deduplication when the same content appears across different sources.
        
        Args:
            source_id: ID of the source
            content: Main content text
            url: Content URL if available
            source_guid: Source-specific identifier (RSS GUID, Tweet ID, etc.)
            
        Returns:
            SHA-256 hash string for deduplication
        """
        identifier = source_guid or url or ""
        hash_input = f"{source_id}:{identifier}:{content}"
        return hashlib.sha256(hash_input.encode("utf-8")).hexdigest()

    @computed_field
    def computed_content_hash(self) -> str:
        """Compute SHA-256 hash using the generate_content_hash method."""
        return self.generate_content_hash(
            self.source_id, self.content, self.url, self.source_guid
        )

    @model_validator(mode="after")
    def set_content_hash(self) -> "Post":
        """Set content_hash after model initialization if not provided."""
        if self.content_hash is None:
            self.content_hash = str(self.computed_content_hash)
        return self

    model_config = ConfigDict(json_encoders={datetime: lambda v: v.isoformat() if v else None})

    def __str__(self) -> str:
        """String representation."""
        return f"{self.title}"

    def __repr__(self) -> str:
        """Developer representation."""
        return f"Post(id={self.id}, source_id={self.source_id}, " f"title='{self.title[:50]}...')"
