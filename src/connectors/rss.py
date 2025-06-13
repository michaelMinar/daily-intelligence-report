"""
RSS/Atom feed connector implementation.
"""
import feedparser
from datetime import datetime
from typing import AsyncIterator, Dict, Any, Optional
from time import mktime

import httpx

from src.connectors.base import BaseConnector
from src.connectors.configs.rss import RSSConfig
from src.connectors.exceptions import NetworkError, ParseError
from src.connectors.resilience import network_retry
from src.models.post import Post
from src.models.source import SourceType
from src.connectors import register_connector


class RSSConnector(BaseConnector):
    """Connector for RSS/Atom feeds."""
    
    @network_retry
    async def _fetch_feed(self, url: str, config: RSSConfig) -> str:
        """Fetch feed content with retry logic."""
        try:
            response = await self.http_client.get(
                url,
                timeout=config.timeout_seconds,
                headers=config.custom_headers or {},
                follow_redirects=True
            )
            response.raise_for_status()
            return response.text
        except httpx.NetworkError as e:
            raise NetworkError(f"Network error fetching {url}: {e}")
        except httpx.TimeoutException as e:
            raise NetworkError(f"Timeout fetching {url}: {e}")
        except httpx.HTTPStatusError as e:
            # Don't retry on 4xx errors (client errors)
            if 400 <= e.response.status_code < 500:
                raise
            # Retry on 5xx errors (server errors)
            raise NetworkError(f"HTTP {e.response.status_code} error fetching {url}")
    
    async def fetch_raw_data(self, fetch_state: Optional[Dict[str, Any]] = None) -> AsyncIterator[Dict[str, Any]]:
        """Fetch and parse RSS feed entries."""
        config: RSSConfig = self.source.typed_config
        
        # Fetch feed with retry logic
        feed_content = await self._fetch_feed(self.source.identifier, config)
        
        # Parse with feedparser
        feed = feedparser.parse(feed_content)
        
        # Check for parsing errors
        if feed.bozo and hasattr(feed, 'bozo_exception'):
            # Check if it's a serious error (no entries could be parsed)
            if not feed.entries:
                raise ParseError(f"Failed to parse feed: {feed.bozo_exception}")
            # Otherwise just log a warning and continue
            self.logger.warning(f"Feed parsing warning: {feed.bozo_exception}")
        
        # Handle incremental fetching
        last_seen_guid = fetch_state.get('last_seen_id') if fetch_state else None
        
        # Get entries, limiting to max_items_per_fetch
        entries = feed.entries
        if config.max_items_per_fetch:
            entries = entries[:config.max_items_per_fetch]
        
        # Process entries
        for entry in entries:
            # Stop at previously seen content
            if last_seen_guid:
                entry_guid = entry.get('id') or entry.get('guid') or entry.get('link')
                if entry_guid == last_seen_guid:
                    break
            
            # Apply keyword filters if configured
            if config.filter_keywords or config.exclude_keywords:
                # Combine title and summary/content for filtering
                filter_text = entry.get('title', '') + ' ' + entry.get('summary', '')
                if 'content' in entry and entry.get('content'):
                    filter_text += ' ' + entry['content'][0].get('value', '')
                
                filter_text = filter_text.lower()
                
                # Check filter keywords (must contain at least one)
                if config.filter_keywords:
                    if not any(kw.lower() in filter_text for kw in config.filter_keywords):
                        continue
                
                # Check exclude keywords (must not contain any)
                if config.exclude_keywords:
                    if any(kw.lower() in filter_text for kw in config.exclude_keywords):
                        continue
            
            # Yield entry with feed info
            yield {
                'entry': entry,
                'feed_info': feed.feed
            }
    
    def normalize_to_post(self, raw_data: Dict[str, Any]) -> Optional[Post]:
        """Convert RSS entry to Post model."""
        try:
            entry = raw_data['entry']
            feed_info = raw_data['feed_info']
            
            # Extract title (required)
            title = entry.get('title', '').strip()
            if not title:
                self.logger.warning("Entry has no title, skipping")
                return None
            
            # Extract content (prefer full content over summary)
            content = ""
            if 'content' in entry and entry['content']:
                # content is a list of dicts
                content = entry['content'][0].get('value', '')
            elif 'summary' in entry:
                content = entry['summary']
            
            # Fallback to title if no content
            if not content:
                content = title
            
            # Extract URL
            url = entry.get('link')
            
            # Extract published date
            published_at = None
            if 'published_parsed' in entry and entry['published_parsed']:
                try:
                    published_at = datetime.fromtimestamp(mktime(entry['published_parsed']))
                except (ValueError, OverflowError):
                    pass
            
            if not published_at and 'updated_parsed' in entry and entry['updated_parsed']:
                try:
                    published_at = datetime.fromtimestamp(mktime(entry['updated_parsed']))
                except (ValueError, OverflowError):
                    pass
            
            # Extract GUID (prefer id over guid over link)
            source_guid = entry.get('id') or entry.get('guid') or url
            
            # Build metadata
            metadata = {
                'feed_title': feed_info.get('title', ''),
                'feed_link': feed_info.get('link', ''),
                'author': entry.get('author', ''),
            }
            
            # Add tags if present
            if 'tags' in entry and entry['tags']:
                metadata['tags'] = [tag.get('term', '') for tag in entry['tags'] if tag.get('term')]
            
            # Create Post instance
            return Post(
                source_id=self.source.id,  # Will be overridden in base.run()
                title=title,
                content=content,
                url=url,
                published_at=published_at,
                content_hash="",  # Will be generated in base.run()
                source_guid=source_guid,
                metadata_json=metadata
            )
            
        except Exception as e:
            self.logger.error(f"Error normalizing RSS entry: {e}")
            return None


# Register the connector
register_connector(SourceType.RSS, RSSConnector)