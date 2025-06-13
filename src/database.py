"""
Database interface for connectors.
"""
from typing import List, Optional, Dict, Any
from abc import ABC, abstractmethod
from src.models.post import Post
from src.models.source import Source


class Database(ABC):
    """Abstract database interface."""
    
    @abstractmethod
    async def post_exists_by_hash(self, content_hash: str) -> bool:
        """Check if a post with the given content hash already exists."""
        pass
    
    @abstractmethod
    async def insert_post(self, post: Post) -> int:
        """Insert a new post and return its ID."""
        pass
    
    @abstractmethod
    async def get_active_sources(self) -> List[Source]:
        """Get all active sources."""
        pass
    
    @abstractmethod
    async def get_source_fetch_state(self, source_id: int) -> Optional[Dict[str, Any]]:
        """Retrieve the last fetch state for a source."""
        pass
    
    @abstractmethod
    async def update_source_fetch_state(self, source_id: int, fetch_state: Dict[str, Any]) -> None:
        """Update the fetch state for a source."""
        pass
    
    @abstractmethod
    async def update_source_status(self, source_id: int, status: str) -> None:
        """Update the status of a source."""
        pass