"""
Tests for RSS connector.
"""
from time import struct_time
from unittest.mock import AsyncMock, Mock

import httpx
import pytest

from src.connectors.rss import RSSConnector
from src.database import Database
from src.models.source import Source, SourceType

# Sample RSS feed for testing
SAMPLE_RSS_FEED = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Test Blog</title>
    <link>https://example.com</link>
    <description>A test blog</description>
    <item>
      <title>First Post</title>
      <link>https://example.com/post1</link>
      <guid>post-1</guid>
      <description>This is the first post</description>
      <pubDate>Mon, 01 Jan 2024 12:00:00 GMT</pubDate>
      <author>John Doe</author>
    </item>
    <item>
      <title>Second Post</title>
      <link>https://example.com/post2</link>
      <guid>post-2</guid>
      <description>This is the second post</description>
      <content:encoded>Full content of the second post</content:encoded>
      <pubDate>Tue, 02 Jan 2024 12:00:00 GMT</pubDate>
    </item>
  </channel>
</rss>"""


@pytest.fixture
def mock_source():
    """Create a mock RSS source."""
    return Source(
        id=1,
        type=SourceType.RSS,
        identifier="https://example.com/feed.xml",
        name="Test RSS Feed",
        active=True,
        config={
            'max_items_per_fetch': 10
        }
    )


@pytest.fixture
def mock_db():
    """Create a mock database."""
    db = Mock(spec=Database)
    db.get_source_fetch_state = AsyncMock(return_value=None)
    db.post_exists_by_hash = AsyncMock(return_value=False)
    db.insert_post = AsyncMock(return_value=1)
    db.update_source_fetch_state = AsyncMock()
    return db


@pytest.fixture
def mock_http_response():
    """Create a mock HTTP response."""
    response = Mock(spec=httpx.Response)
    response.text = SAMPLE_RSS_FEED
    response.raise_for_status = Mock()
    return response


@pytest.fixture
def mock_http_client(mock_http_response):
    """Create a mock HTTP client."""
    client = Mock(spec=httpx.AsyncClient)
    client.get = AsyncMock(return_value=mock_http_response)
    return client


@pytest.fixture
def rss_connector(mock_source, mock_db, mock_http_client):
    """Create an RSS connector instance."""
    return RSSConnector(mock_source, mock_db, mock_http_client)


class TestRSSConnector:
    """Tests for RSSConnector."""
    
    @pytest.mark.asyncio
    async def test_fetch_raw_data_basic(self, rss_connector, mock_http_client):
        """Test basic RSS feed fetching."""
        items = []
        async for item in rss_connector.fetch_raw_data():
            items.append(item)
        
        # Should have 2 items from sample feed
        assert len(items) == 2
        
        # Check first item
        assert items[0]['entry']['title'] == 'First Post'
        assert items[0]['entry']['link'] == 'https://example.com/post1'
        assert items[0]['entry']['guid'] == 'post-1'
        assert items[0]['feed_info']['title'] == 'Test Blog'
        
        # Check HTTP client was called correctly
        mock_http_client.get.assert_called_once_with(
            "https://example.com/feed.xml",
            timeout=30,
            headers={},
            follow_redirects=True
        )
    
    @pytest.mark.asyncio
    async def test_fetch_raw_data_with_incremental_state(self, rss_connector):
        """Test incremental fetching with previous state."""
        fetch_state = {'last_seen_id': 'post-1'}
        
        items = []
        async for item in rss_connector.fetch_raw_data(fetch_state):
            items.append(item)
        
        # Should stop at post-1, so no items returned
        assert len(items) == 0
    
    @pytest.mark.asyncio
    async def test_fetch_raw_data_with_max_items(self, mock_source, mock_db, mock_http_client):
        """Test respecting max_items_per_fetch configuration."""
        mock_source.config = {'max_items_per_fetch': 1}
        connector = RSSConnector(mock_source, mock_db, mock_http_client)
        
        items = []
        async for item in connector.fetch_raw_data():
            items.append(item)
        
        # Should only return 1 item due to config
        assert len(items) == 1
    
    @pytest.mark.asyncio
    async def test_fetch_raw_data_with_filter_keywords(
        self, mock_source, mock_db, mock_http_client
    ):
        """Test keyword filtering."""
        mock_source.config = {
            'filter_keywords': ['second'],
            'max_items_per_fetch': 10
        }
        connector = RSSConnector(mock_source, mock_db, mock_http_client)
        
        items = []
        async for item in connector.fetch_raw_data():
            items.append(item)
        
        # Should only return the second post
        assert len(items) == 1
        assert items[0]['entry']['title'] == 'Second Post'
    
    @pytest.mark.asyncio
    async def test_fetch_raw_data_with_exclude_keywords(
        self, mock_source, mock_db, mock_http_client
    ):
        """Test exclude keyword filtering."""
        mock_source.config = {
            'exclude_keywords': ['first'],
            'max_items_per_fetch': 10
        }
        connector = RSSConnector(mock_source, mock_db, mock_http_client)
        
        items = []
        async for item in connector.fetch_raw_data():
            items.append(item)
        
        # Should exclude the first post
        assert len(items) == 1
        assert items[0]['entry']['title'] == 'Second Post'
    
    @pytest.mark.asyncio
    async def test_fetch_raw_data_http_error(self, rss_connector, mock_http_client):
        """Test handling of HTTP errors."""
        mock_http_client.get.side_effect = httpx.HTTPStatusError(
            "404 Not Found", request=Mock(), response=Mock(status_code=404)
        )
        
        with pytest.raises(httpx.HTTPStatusError):
            async for _ in rss_connector.fetch_raw_data():
                pass
    
    def test_normalize_to_post_basic(self, rss_connector):
        """Test basic post normalization."""
        # Mock feedparser entry
        entry = {
            'title': 'Test Post',
            'link': 'https://example.com/test',
            'guid': 'test-guid',
            'summary': 'Test summary',
            'author': 'Test Author',
            'published_parsed': struct_time((2024, 1, 1, 12, 0, 0, 0, 1, 0))
        }
        
        raw_data = {
            'entry': entry,
            'feed_info': {
                'title': 'Test Feed',
                'link': 'https://example.com'
            }
        }
        
        post = rss_connector.normalize_to_post(raw_data)
        
        assert post is not None
        assert post.title == 'Test Post'
        assert post.content == 'Test summary'
        assert post.url == 'https://example.com/test'
        assert post.source_guid == 'test-guid'
        assert post.published_at.year == 2024
        assert post.metadata_json['feed_title'] == 'Test Feed'
        assert post.metadata_json['author'] == 'Test Author'
    
    def test_normalize_to_post_with_content(self, rss_connector):
        """Test normalization preferring content over summary."""
        entry = {
            'title': 'Test Post',
            'summary': 'Short summary',
            'content': [{'value': 'Full content here'}]
        }
        
        raw_data = {
            'entry': entry,
            'feed_info': {}
        }
        
        post = rss_connector.normalize_to_post(raw_data)
        
        assert post is not None
        assert post.content == 'Full content here'
    
    def test_normalize_to_post_no_title(self, rss_connector):
        """Test normalization with missing title."""
        entry = {
            'summary': 'Content without title'
        }
        
        raw_data = {
            'entry': entry,
            'feed_info': {}
        }
        
        post = rss_connector.normalize_to_post(raw_data)
        
        # Should return None for entries without title
        assert post is None
    
    def test_normalize_to_post_with_tags(self, rss_connector):
        """Test normalization with tags."""
        entry = {
            'title': 'Tagged Post',
            'summary': 'Post with tags',
            'tags': [
                {'term': 'python'},
                {'term': 'programming'},
                {'term': ''}  # Empty tag should be filtered
            ]
        }
        
        raw_data = {
            'entry': entry,
            'feed_info': {}
        }
        
        post = rss_connector.normalize_to_post(raw_data)
        
        assert post is not None
        assert post.metadata_json['tags'] == ['python', 'programming']
    
    def test_normalize_to_post_guid_fallback(self, rss_connector):
        """Test GUID fallback logic."""
        # Test with id
        entry = {'title': 'Test', 'id': 'entry-id', 'guid': 'entry-guid', 'link': 'https://test.com'}
        post = rss_connector.normalize_to_post({'entry': entry, 'feed_info': {}})
        assert post.source_guid == 'entry-id'
        
        # Test with guid (no id)
        entry = {'title': 'Test', 'guid': 'entry-guid', 'link': 'https://test.com'}
        post = rss_connector.normalize_to_post({'entry': entry, 'feed_info': {}})
        assert post.source_guid == 'entry-guid'
        
        # Test with link (no id or guid)
        entry = {'title': 'Test', 'link': 'https://test.com'}
        post = rss_connector.normalize_to_post({'entry': entry, 'feed_info': {}})
        assert post.source_guid == 'https://test.com'
    
    def test_normalize_to_post_date_parsing(self, rss_connector):
        """Test various date parsing scenarios."""
        # Test with published_parsed
        entry = {
            'title': 'Test',
            'published_parsed': struct_time((2024, 1, 15, 10, 30, 0, 0, 15, 0))
        }
        post = rss_connector.normalize_to_post({'entry': entry, 'feed_info': {}})
        assert post.published_at.day == 15
        assert post.published_at.hour == 10
        
        # Test with updated_parsed (no published)
        entry = {
            'title': 'Test',
            'updated_parsed': struct_time((2024, 2, 20, 14, 45, 0, 0, 51, 0))
        }
        post = rss_connector.normalize_to_post({'entry': entry, 'feed_info': {}})
        assert post.published_at.month == 2
        assert post.published_at.day == 20
        
        # Test with no date
        entry = {'title': 'Test'}
        post = rss_connector.normalize_to_post({'entry': entry, 'feed_info': {}})
        assert post.published_at is None
    
    def test_normalize_to_post_exception_handling(self, rss_connector):
        """Test exception handling in normalization."""
        # Pass invalid data
        raw_data = {'entry': None, 'feed_info': {}}
        
        post = rss_connector.normalize_to_post(raw_data)
        
        # Should return None and not raise
        assert post is None
    
    @pytest.mark.asyncio
    async def test_integration_with_base_connector(self, rss_connector, mock_db):
        """Test integration with base connector run method."""
        # Run the connector
        stats = await rss_connector.run()
        
        # Check stats
        assert stats['fetched'] == 2
        assert stats['new'] == 2
        assert stats['duplicate'] == 0
        assert stats['error'] == 0
        
        # Check database interactions
        assert mock_db.insert_post.call_count == 2
        assert mock_db.update_source_fetch_state.call_count == 1


class TestRSSConnectorRegistration:
    """Test RSS connector registration."""
    
    def test_rss_connector_can_be_registered(self):
        """Test that RSSConnector can be registered and retrieved."""
        from src.connectors import CONNECTOR_REGISTRY, get_connector_class, register_connector
        
        # Save current state
        original_registry = CONNECTOR_REGISTRY.copy()
        
        try:
            # Register RSS connector
            register_connector(SourceType.RSS, RSSConnector)
            
            # Verify it can be retrieved
            connector_class = get_connector_class(SourceType.RSS)
            assert connector_class == RSSConnector
        finally:
            # Restore original state
            CONNECTOR_REGISTRY.clear()
            CONNECTOR_REGISTRY.update(original_registry)