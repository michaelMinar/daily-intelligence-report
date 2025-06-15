"""
Base connector abstract class implementing Template Method Pattern.
"""
import logging
from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator
from datetime import datetime
from typing import Any, Dict, Optional

import httpx

from src.database import Database
from src.models.post import Post
from src.models.source import Source


class BaseConnector(ABC):
    """Abstract base class for content connectors implementing Template Method Pattern."""
    
    def __init__(self, source: Source, db: Database, http_client: httpx.AsyncClient):
        """Initialize with source configuration, database connection, and shared HTTP client."""
        self.source = source
        self.db = db
        self.http_client = http_client
        self.logger = logging.getLogger(f"{self.__class__.__name__}:{source.name}")
        
    @abstractmethod
    def fetch_raw_data(
        self, fetch_state: Optional[Dict[str, Any]] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Yield raw data items from the source.
        
        Args:
            fetch_state: Previous fetch state for incremental fetching
                        (e.g., {'last_seen_id': 'xyz',
                         'last_fetch_timestamp': '2024-01-01T00:00:00Z'})
        """
        pass
        
    @abstractmethod
    def normalize_to_post(self, raw_data: Dict[str, Any]) -> Optional[Post]:
        """Convert raw data to normalized Post model."""
        pass
        
    def extract_fetch_state(self, post: Post) -> Dict[str, Any]:
        """
        Extract fetch state from a processed post for incremental fetching.
        Override in subclasses for source-specific state extraction.
        
        Args:
            post: Processed post object
            
        Returns:
            State dictionary for next fetch
        """
        return {
            'last_seen_id': post.source_guid or post.url,
            'last_fetch_timestamp': datetime.utcnow().isoformat()
        }
    
    async def run(self) -> Dict[str, int]:
        """
        Execute fetch operation with standardized orchestration.
        
        Template Method Pattern: Defines the algorithm structure while allowing
        subclasses to customize specific steps (fetch_raw_data, normalize_to_post).
        
        Returns:
            Statistics dictionary with counts for fetched/new/duplicate/error items
        """
        stats = {
            'fetched': 0,
            'new': 0, 
            'duplicate': 0,
            'error': 0
        }
        
        try:
            # 1. Get previous fetch state
            if self.source.id is None:
                raise ValueError("Source ID cannot be None")
            fetch_state = await self.db.get_source_fetch_state(self.source.id)
            
            # 2. Fetch raw data with incremental support
            last_processed_post = None
            async for raw_item in self.fetch_raw_data(fetch_state):
                stats['fetched'] += 1
                
                try:
                    # 3. Normalize to Post model
                    post = self.normalize_to_post(raw_item)
                    if not post:
                        continue
                        
                    # 4. Set source_id and generate composite hash
                    if self.source.id is None:
                        raise ValueError("Source ID cannot be None")
                    post.source_id = self.source.id
                    post.content_hash = Post.generate_content_hash(
                        post.source_id, post.content, post.url, post.source_guid
                    )
                    
                    # 5. Check for duplicates
                    if await self.db.post_exists_by_hash(post.content_hash):
                        stats['duplicate'] += 1
                        continue
                        
                    # 6. Insert new post
                    await self.db.insert_post(post)
                    stats['new'] += 1
                    last_processed_post = post
                    
                except Exception as e:
                    self.logger.error(f"Error processing item: {e}")
                    stats['error'] += 1
                    
            # 7. Update fetch state if we processed any items
            if last_processed_post and self.source.id is not None:
                new_state = self.extract_fetch_state(last_processed_post)
                await self.db.update_source_fetch_state(self.source.id, new_state)
                
        except Exception as e:
            self.logger.error(f"Fatal error in connector run: {type(e).__name__} - {e}")
            raise
            
        return stats