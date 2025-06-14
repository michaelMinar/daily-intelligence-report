# Connector Configuration - Implementation Plan

## Overview
We are implementing the next three steps in our development plan for the daily intelligence report generator:
1. Implement basic RSS fetching
2. Add retry/backoff mechanisms  
3. Create a normalize_to_post function

This document outlines the detailed implementation steps for each component. The implementation follows the design specified in `design/connector-design.md`.

## 1. Basic RSS Fetching Implementation

### 1.1 File Structure Setup
Create the following files:
- `src/connectors/__init__.py` - Registry and factory functions
- `src/connectors/base.py` - BaseConnector abstract class
- `src/connectors/rss.py` - RSSConnector implementation
- `src/connectors/configs/base.py` - BaseConnectorConfig
- `src/connectors/configs/rss.py` - RSSConfig
- `config/connectors/defaults/rss.yaml` - Default RSS configuration

### 1.2 BaseConnector Implementation (`src/connectors/base.py`)
```python
from abc import ABC, abstractmethod
from typing import AsyncIterator, Dict, Any, Optional, Type
import logging
import httpx
from datetime import datetime
from src.models.post import Post
from src.models.source import Source
from src.database import Database

class BaseConnector(ABC):
    """Abstract base class implementing Template Method Pattern"""
    
    def __init__(self, source: Source, db: Database, http_client: httpx.AsyncClient):
        self.source = source
        self.db = db
        self.http_client = http_client
        self.logger = logging.getLogger(f"{self.__class__.__name__}:{source.name}")
    
    @abstractmethod
    async def fetch_raw_data(self, fetch_state: Optional[Dict[str, Any]] = None) -> AsyncIterator[Dict[str, Any]]:
        """Yield raw data items from source"""
        pass
    
    @abstractmethod
    def normalize_to_post(self, raw_data: Dict[str, Any]) -> Optional[Post]:
        """Convert raw data to Post model"""
        pass
    
    def extract_fetch_state(self, post: Post) -> Dict[str, Any]:
        """Extract fetch state for incremental fetching"""
        return {
            'last_seen_id': post.source_guid or post.url,
            'last_fetch_timestamp': datetime.utcnow().isoformat()
        }
    
    async def run(self) -> Dict[str, int]:
        """Execute fetch with standardized orchestration"""
        # Implementation as per design doc
```

### 1.3 RSS Connector Implementation (`src/connectors/rss.py`)
```python
import feedparser
from typing import AsyncIterator, Dict, Any, Optional
from datetime import datetime
from src.connectors.base import BaseConnector
from src.models.post import Post
from src.connectors.configs.rss import RSSConfig

class RSSConnector(BaseConnector):
    """RSS/Atom feed connector"""
    
    async def fetch_raw_data(self, fetch_state: Optional[Dict[str, Any]] = None) -> AsyncIterator[Dict[str, Any]]:
        """Fetch and parse RSS feed entries"""
        config: RSSConfig = self.source.typed_config
        
        # Fetch feed using httpx
        response = await self.http_client.get(
            self.source.identifier,
            timeout=config.timeout_seconds,
            headers=config.custom_headers or {}
        )
        response.raise_for_status()
        
        # Parse with feedparser
        feed = feedparser.parse(response.text)
        
        # Handle incremental fetching
        last_seen_guid = fetch_state.get('last_seen_id') if fetch_state else None
        
        # Process entries in reverse chronological order
        entries = feed.entries[:config.max_items_per_fetch]
        
        for entry in entries:
            # Stop at previously seen content
            if last_seen_guid and entry.get('id') == last_seen_guid:
                break
                
            # Apply keyword filters if configured
            if config.filter_keywords or config.exclude_keywords:
                content = entry.get('summary', '') + entry.get('title', '')
                
                if config.filter_keywords:
                    if not any(kw.lower() in content.lower() for kw in config.filter_keywords):
                        continue
                        
                if config.exclude_keywords:
                    if any(kw.lower() in content.lower() for kw in config.exclude_keywords):
                        continue
            
            yield {
                'entry': entry,
                'feed_info': feed.feed
            }
    
    def normalize_to_post(self, raw_data: Dict[str, Any]) -> Optional[Post]:
        """Convert RSS entry to Post model"""
        # Implementation details below
```

### 1.4 Configuration Classes
**`src/connectors/configs/base.py`:**
```python
from pydantic import BaseModel
from typing import Optional, Dict

class BaseConnectorConfig(BaseModel):
    enabled: bool = True
    fetch_interval_minutes: int = 60
    max_items_per_fetch: Optional[int] = 50
    retry_attempts: int = 3
    timeout_seconds: int = 30
    custom_headers: Optional[Dict[str, str]] = None
```

**`src/connectors/configs/rss.py`:**
```python
from typing import Optional, List
from src.connectors.configs.base import BaseConnectorConfig

class RSSConfig(BaseConnectorConfig):
    parse_full_content: bool = False
    filter_keywords: Optional[List[str]] = None
    exclude_keywords: Optional[List[str]] = None
```

### 1.5 Default Configuration
**`config/connectors/defaults/rss.yaml`:**
```yaml
enabled: true
fetch_interval_minutes: 60
max_items_per_fetch: 50
retry_attempts: 3
timeout_seconds: 30
parse_full_content: false
filter_keywords: null
exclude_keywords: null
```

## 2. Retry/Backoff Mechanisms Implementation

### 2.1 Exception Hierarchy (`src/connectors/exceptions.py`)
```python
class ConnectorError(Exception):
    """Base exception for all connector errors"""
    
class RateLimitError(ConnectorError):
    """Raised when API rate limit is exceeded"""
    def __init__(self, retry_after: Optional[int] = None):
        self.retry_after = retry_after
        
class AuthenticationError(ConnectorError):
    """Raised when authentication fails"""
    
class NetworkError(ConnectorError):
    """Raised for network-related failures"""
    
class ParseError(ConnectorError):
    """Raised when content parsing fails"""
```

### 2.2 Retry Decorator Implementation
Using the `tenacity` library, we'll create retry decorators for different scenarios:

**`src/connectors/resilience.py`:**
```python
from tenacity import (
    retry, stop_after_attempt, wait_exponential, 
    retry_if_exception_type, wait_fixed
)
from src.connectors.exceptions import NetworkError, RateLimitError

# Network retry decorator
network_retry = retry(
    retry=retry_if_exception_type(NetworkError),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10)
)

# Rate limit retry decorator
def rate_limit_retry(func):
    return retry(
        retry=retry_if_exception_type(RateLimitError),
        stop=stop_after_attempt(1),
        wait=wait_fixed(lambda retry_state: 
            retry_state.outcome.exception().retry_after or 60
        )
    )(func)
```

### 2.3 Enhanced RSS Connector with Retry
Update `RSSConnector.fetch_raw_data` to use retry decorators:

```python
@network_retry
async def _fetch_feed(self, url: str, config: RSSConfig) -> str:
    """Fetch feed content with retry logic"""
    try:
        response = await self.http_client.get(
            url,
            timeout=config.timeout_seconds,
            headers=config.custom_headers or {}
        )
        response.raise_for_status()
        return response.text
    except httpx.NetworkError as e:
        raise NetworkError(f"Network error fetching {url}: {e}")
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 429:
            retry_after = e.response.headers.get('Retry-After', 60)
            raise RateLimitError(retry_after=int(retry_after))
        raise

async def fetch_raw_data(self, fetch_state: Optional[Dict[str, Any]] = None) -> AsyncIterator[Dict[str, Any]]:
    """Fetch with retry logic"""
    config: RSSConfig = self.source.typed_config
    
    # Fetch with retry
    feed_content = await self._fetch_feed(self.source.identifier, config)
    
    # Continue with parsing...
```

### 2.4 Circuit Breaker Pattern (Optional Enhancement)
```python
class CircuitBreaker:
    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time: Optional[float] = None
        self.state = "closed"  # closed, open, half-open
        
    # Implementation details as per design doc
```

## 3. Normalize to Post Function Implementation

### 3.1 Post Model Enhancement (`src/models/post.py`)
```python
import hashlib
from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel

class Post(BaseModel):
    source_id: int
    title: str
    content: str
    url: Optional[str] = None
    published_at: Optional[datetime] = None
    content_hash: str
    source_guid: Optional[str] = None
    metadata_json: Optional[Dict[str, Any]] = None
    
    @classmethod
    def generate_content_hash(cls, source_id: int, content: str, 
                            url: Optional[str] = None, 
                            source_guid: Optional[str] = None) -> str:
        """Generate composite hash for deduplication"""
        identifier = source_guid or url or ""
        hash_input = f"{source_id}:{identifier}:{content}"
        return hashlib.sha256(hash_input.encode('utf-8')).hexdigest()
```

### 3.2 RSS Normalize Implementation
Complete the `normalize_to_post` method in `RSSConnector`:

```python
def normalize_to_post(self, raw_data: Dict[str, Any]) -> Optional[Post]:
    """Convert RSS entry to Post model"""
    entry = raw_data['entry']
    feed_info = raw_data['feed_info']
    
    # Extract title
    title = entry.get('title', 'Untitled')
    
    # Extract content (prefer content over summary)
    content = None
    if 'content' in entry:
        content = entry.content[0].value
    elif 'summary' in entry:
        content = entry.summary
    else:
        content = title  # Fallback to title if no content
    
    # Extract URL
    url = entry.get('link')
    
    # Extract published date
    published_at = None
    if 'published_parsed' in entry:
        published_at = datetime.fromtimestamp(
            feedparser._parse_date(entry.published_parsed)
        )
    elif 'updated_parsed' in entry:
        published_at = datetime.fromtimestamp(
            feedparser._parse_date(entry.updated_parsed)
        )
    
    # Extract GUID
    source_guid = entry.get('id') or entry.get('guid')
    
    # Build metadata
    metadata = {
        'feed_title': feed_info.get('title'),
        'feed_link': feed_info.get('link'),
        'author': entry.get('author'),
        'tags': [tag.term for tag in entry.get('tags', [])]
    }
    
    # Create Post instance
    return Post(
        source_id=self.source.id,  # Will be set in base.run()
        title=title,
        content=content,
        url=url,
        published_at=published_at,
        content_hash="",  # Will be generated in base.run()
        source_guid=source_guid,
        metadata_json=metadata
    )
```

### 3.3 Full Content Extraction (Optional)
If `parse_full_content` is enabled, fetch and extract article content:

```python
async def _extract_full_content(self, url: str) -> Optional[str]:
    """Extract full article content from URL"""
    try:
        # Option 1: Use newspaper3k or similar
        # Option 2: Use custom extraction based on site
        # Option 3: Use readability algorithm
        pass
    except Exception as e:
        self.logger.warning(f"Failed to extract full content from {url}: {e}")
        return None
```

## Testing Strategy

### Unit Tests (`tests/test_connectors/test_rss.py`)
```python
import pytest
from unittest.mock import Mock, AsyncMock
from src.connectors.rss import RSSConnector
from src.models.source import Source, SourceType

@pytest.mark.asyncio
async def test_rss_fetch_raw_data():
    # Test successful fetch
    # Test incremental fetch with state
    # Test keyword filtering
    pass

def test_normalize_to_post():
    # Test with complete entry
    # Test with minimal entry
    # Test with missing fields
    pass
```

### Integration Tests
```python
@pytest.mark.asyncio
async def test_rss_connector_full_flow():
    # Test complete fetch → normalize → save flow
    # Test deduplication
    # Test error handling
    pass
```

## Implementation Order

1. **Phase 1: Core Structure**
   - Create base connector abstract class
   - Implement configuration classes
   - Set up exception hierarchy

2. **Phase 2: RSS Connector**
   - Implement basic fetch_raw_data
   - Implement normalize_to_post
   - Add unit tests

3. **Phase 3: Retry/Resilience**
   - Add retry decorators
   - Implement error handling
   - Add network resilience tests

4. **Phase 4: Integration**
   - Wire up with database
   - Test full pipeline
   - Add logging and monitoring

## Next Steps After Implementation

1. Code review and testing
2. Integration with database layer
3. Add connector pool for concurrent execution
4. Implement remaining connectors (Twitter, Email, etc.)
5. Set up scheduling and automation
