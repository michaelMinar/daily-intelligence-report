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
        default=None,
        description="When the post was originally published"
    )
    ingested_at: Optional[datetime] = Field(
        default=None,
        description="When the post was ingested into our system"
    )
    content_hash: Optional[str] = Field(
        default=None,
        description="SHA-256 hash of content for deduplication"
    )
    metadata_json: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Additional metadata as JSON"
    )
    
    @computed_field
    def computed_content_hash(self) -> str:
        """Compute SHA-256 hash of title + content for deduplication."""
        content_to_hash = f"{self.title}\n{self.content}"
        return hashlib.sha256(content_to_hash.encode("utf-8")).hexdigest()
    
    @model_validator(mode='after')
    def set_content_hash(self) -> 'Post':
        """Set content_hash after model initialization if not provided."""
        if self.content_hash is None:
            self.content_hash = str(self.computed_content_hash)
        return self
    
    model_config = ConfigDict(
        json_encoders={
            datetime: lambda v: v.isoformat() if v else None
        }
    )
        
    def __str__(self) -> str:
        """String representation."""
        return f"{self.title}"
    
    def __repr__(self) -> str:
        """Developer representation."""
        return (
            f"Post(id={self.id}, source_id={self.source_id}, "
            f"title='{self.title[:50]}...')"
        )