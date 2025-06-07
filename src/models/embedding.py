"""Embedding model for vector representations of posts."""

from datetime import datetime
from typing import List, Optional

import numpy as np
from pydantic import BaseModel, Field, field_validator


class Embedding(BaseModel):
    """Model for vector embeddings of posts."""
    
    id: Optional[int] = None
    post_id: int = Field(..., description="ID of the post this embedding represents")
    embedding_blob: Optional[bytes] = Field(
        default=None,
        description="Serialized vector embedding as bytes"
    )
    model_name: str = Field(
        ...,
        description="Name of the model used to generate the embedding"
    )
    created_at: Optional[datetime] = None
    
    # Transient field for working with embeddings as numpy arrays
    _embedding_vector: Optional[np.ndarray] = None
    
    @field_validator('model_name')
    @classmethod
    def validate_model_name(cls, v: str) -> str:
        """Validate model name is not empty."""
        if not v.strip():
            raise ValueError("Model name cannot be empty")
        return v.strip()
    
    @property
    def embedding_vector(self) -> Optional[np.ndarray]:
        """Get embedding as numpy array."""
        if self._embedding_vector is not None:
            return self._embedding_vector
        
        if self.embedding_blob is not None:
            return np.frombuffer(self.embedding_blob, dtype=np.float32)
        
        return None
    
    @embedding_vector.setter
    def embedding_vector(self, vector: np.ndarray) -> None:
        """Set embedding from numpy array."""
        if not isinstance(vector, np.ndarray):
            raise ValueError("Embedding must be a numpy array")
        
        # Ensure float32 dtype for consistency
        if vector.dtype != np.float32:
            vector = vector.astype(np.float32)
        
        self._embedding_vector = vector
        self.embedding_blob = vector.tobytes()
    
    def similarity(self, other: "Embedding") -> float:
        """Calculate cosine similarity with another embedding."""
        vec1 = self.embedding_vector
        vec2 = other.embedding_vector
        
        if vec1 is None or vec2 is None:
            raise ValueError("Both embeddings must have vectors to calculate similarity")
        
        if vec1.shape != vec2.shape:
            raise ValueError("Embedding vectors must have the same shape")
        
        # Cosine similarity
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        
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
        vector_info = f"shape={self.embedding_vector.shape}" if self.embedding_vector is not None else "no vector"
        return f"Embedding(post_id={self.post_id}, model={self.model_name}, {vector_info})"
    
    def __repr__(self) -> str:
        """Developer representation."""
        return f"Embedding(id={self.id}, post_id={self.post_id}, model_name='{self.model_name}')"