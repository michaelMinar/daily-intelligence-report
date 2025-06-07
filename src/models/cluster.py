"""Cluster model for topic clustering of posts."""

from datetime import datetime
from typing import List, Optional

import numpy as np
from pydantic import BaseModel, Field, field_validator


class Cluster(BaseModel):
    """Model for topic clusters."""
    
    id: Optional[int] = None
    label: str = Field(..., description="Human-readable cluster label")
    description: Optional[str] = Field(
        default=None,
        description="Detailed description of the cluster topic"
    )
    created_at: Optional[datetime] = None
    post_count: int = Field(default=0, description="Number of posts in this cluster")
    centroid_blob: Optional[bytes] = Field(
        default=None,
        description="Serialized cluster centroid as bytes"
    )
    
    # Transient field for working with centroid as numpy array
    _centroid_vector: Optional[np.ndarray] = None
    
    @field_validator('label')
    @classmethod
    def validate_label(cls, v: str) -> str:
        """Validate label is not empty."""
        if not v.strip():
            raise ValueError("Cluster label cannot be empty")
        return v.strip()
    
    @property
    def centroid_vector(self) -> Optional[np.ndarray]:
        """Get centroid as numpy array."""
        if self._centroid_vector is not None:
            return self._centroid_vector
        
        if self.centroid_blob is not None:
            return np.frombuffer(self.centroid_blob, dtype=np.float32)
        
        return None
    
    @centroid_vector.setter
    def centroid_vector(self, vector: np.ndarray) -> None:
        """Set centroid from numpy array."""
        if not isinstance(vector, np.ndarray):
            raise ValueError("Centroid must be a numpy array")
        
        # Ensure float32 dtype for consistency
        if vector.dtype != np.float32:
            vector = vector.astype(np.float32)
        
        self._centroid_vector = vector
        self.centroid_blob = vector.tobytes()
    
    def distance_to_centroid(self, embedding_vector: np.ndarray) -> float:
        """Calculate Euclidean distance from embedding to cluster centroid."""
        centroid = self.centroid_vector
        
        if centroid is None:
            raise ValueError("Cluster must have a centroid to calculate distance")
        
        if embedding_vector.shape != centroid.shape:
            raise ValueError("Embedding and centroid vectors must have the same shape")
        
        return float(np.linalg.norm(embedding_vector - centroid))
    
    def similarity_to_centroid(self, embedding_vector: np.ndarray) -> float:
        """Calculate cosine similarity between embedding and cluster centroid."""
        centroid = self.centroid_vector
        
        if centroid is None:
            raise ValueError("Cluster must have a centroid to calculate similarity")
        
        if embedding_vector.shape != centroid.shape:
            raise ValueError("Embedding and centroid vectors must have the same shape")
        
        # Cosine similarity
        dot_product = np.dot(embedding_vector, centroid)
        norm1 = np.linalg.norm(embedding_vector)
        norm2 = np.linalg.norm(centroid)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return float(dot_product / (norm1 * norm2))
    
    class Config:
        """Pydantic configuration."""
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None,
            bytes: lambda v: v.hex() if v else None,
        }
        arbitrary_types_allowed = True
        
    def __str__(self) -> str:
        """String representation."""
        return f"{self.label} ({self.post_count} posts)"
    
    def __repr__(self) -> str:
        """Developer representation."""
        return f"Cluster(id={self.id}, label='{self.label}', post_count={self.post_count})"