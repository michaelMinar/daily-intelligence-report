"""
Tests for RSS connector resilience features.
"""
from unittest.mock import AsyncMock, Mock

import httpx
import pytest

from src.connectors.exceptions import ParseError
from src.connectors.rss import RSSConnector
from src.database import Database
from src.models.source import Source, SourceType


@pytest.fixture
def mock_source():
    """Create a mock RSS source."""
    return Source(
        id=1,
        type=SourceType.RSS,
        identifier="https://example.com/feed.xml",
        name="Test RSS Feed",
        active=True,
        config={'retry_attempts': 3}
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


class TestRSSConnectorResilience:
    """Test RSS connector resilience features."""
    
    @pytest.mark.asyncio
    async def test_retry_on_network_error(self, mock_source, mock_db):
        """Test retry logic on network errors."""
        # Create HTTP client that fails twice then succeeds
        mock_http_client = Mock(spec=httpx.AsyncClient)
        responses = [
            httpx.NetworkError("Network error 1"),
            httpx.NetworkError("Network error 2"),
            Mock(text="""<rss><channel><title>Test</title>
                        <item><title>Test Post</title><link>http://example.com</link></item>
                        </channel></rss>""", 
                 raise_for_status=Mock())
        ]
        mock_http_client.get = AsyncMock(side_effect=responses)
        
        connector = RSSConnector(mock_source, mock_db, mock_http_client)
        
        # Should succeed after retries
        items = []
        async for item in connector.fetch_raw_data():
            items.append(item)
        
        # Should have called get 3 times
        assert mock_http_client.get.call_count == 3
        # Verify that the data fetched after retry is correct
        assert len(items) == 1
        assert items[0]['entry']['title'] == 'Test Post'
    
    @pytest.mark.asyncio
    async def test_retry_on_timeout(self, mock_source, mock_db):
        """Test retry logic on timeout errors."""
        mock_http_client = Mock(spec=httpx.AsyncClient)
        responses = [
            httpx.TimeoutException("Timeout"),
            Mock(text="<rss><channel><title>Test</title></channel></rss>", 
                 raise_for_status=Mock())
        ]
        mock_http_client.get = AsyncMock(side_effect=responses)
        
        connector = RSSConnector(mock_source, mock_db, mock_http_client)
        
        items = []
        async for item in connector.fetch_raw_data():
            items.append(item)
        
        assert mock_http_client.get.call_count == 2
    
    @pytest.mark.asyncio
    async def test_retry_on_5xx_errors(self, mock_source, mock_db):
        """Test retry logic on server errors (5xx)."""
        mock_http_client = Mock(spec=httpx.AsyncClient)
        
        # Create mock responses
        error_response = Mock(status_code=503)
        error = httpx.HTTPStatusError(
            "Service unavailable", request=Mock(), response=error_response
        )
        
        success_response = Mock(
            text="<rss><channel><title>Test</title></channel></rss>",
            raise_for_status=Mock()
        )
        
        mock_http_client.get = AsyncMock(side_effect=[error, success_response])
        
        connector = RSSConnector(mock_source, mock_db, mock_http_client)
        
        items = []
        async for item in connector.fetch_raw_data():
            items.append(item)
        
        assert mock_http_client.get.call_count == 2
    
    @pytest.mark.asyncio
    async def test_no_retry_on_4xx_errors(self, mock_source, mock_db):
        """Test no retry on client errors (4xx)."""
        mock_http_client = Mock(spec=httpx.AsyncClient)
        
        # Create 404 error
        error_response = Mock(status_code=404)
        error = httpx.HTTPStatusError("Not found", request=Mock(), response=error_response)
        
        mock_http_client.get = AsyncMock(side_effect=error)
        
        connector = RSSConnector(mock_source, mock_db, mock_http_client)
        
        # Should raise immediately without retry
        with pytest.raises(httpx.HTTPStatusError):
            async for _ in connector.fetch_raw_data():
                pass
        
        # Should only call once (no retry)
        assert mock_http_client.get.call_count == 1
    
    @pytest.mark.asyncio
    async def test_parse_error_on_invalid_feed(self, mock_source, mock_db):
        """Test parse error handling for completely invalid feeds."""
        mock_http_client = Mock(spec=httpx.AsyncClient)
        # Use completely invalid XML that feedparser can't handle
        mock_response = Mock(
            text="Not even XML, just plain text",
            raise_for_status=Mock()
        )
        mock_http_client.get = AsyncMock(return_value=mock_response)
        
        connector = RSSConnector(mock_source, mock_db, mock_http_client)
        
        # Should raise ParseError for invalid feed with no entries
        with pytest.raises(ParseError) as exc_info:
            async for _ in connector.fetch_raw_data():
                pass
        
        assert "Failed to parse feed" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_partial_parse_continues(self, mock_source, mock_db):
        """Test that partial parse errors don't stop processing."""
        mock_http_client = Mock(spec=httpx.AsyncClient)
        
        # RSS with one valid entry and some invalid XML
        partial_rss = """<?xml version="1.0"?>
        <rss version="2.0">
          <channel>
            <title>Test</title>
            <item>
              <title>Valid Item</title>
              <description>This item is valid</description>
            </item>
            <item>
              <title>Invalid Item</title>
              <description>This item has invalid XML &badentity;</description>
            </item>
          </channel>
        </rss>"""
        
        mock_response = Mock(text=partial_rss, raise_for_status=Mock())
        mock_http_client.get = AsyncMock(return_value=mock_response)
        
        connector = RSSConnector(mock_source, mock_db, mock_http_client)
        
        # Should process the valid item despite parse warning
        items = []
        async for item in connector.fetch_raw_data():
            items.append(item)
        
        assert len(items) >= 1  # At least one valid item
        assert items[0]['entry']['title'] == 'Valid Item'
    
    @pytest.mark.asyncio
    async def test_retry_exhaustion_raises_error(self, mock_source, mock_db):
        """Test that exhausting retries raises the error."""
        mock_http_client = Mock(spec=httpx.AsyncClient)
        
        # Always fail with network error
        mock_http_client.get = AsyncMock(side_effect=httpx.NetworkError("Persistent error"))
        
        connector = RSSConnector(mock_source, mock_db, mock_http_client)
        
        # Should eventually raise RetryError after retries exhausted
        from tenacity import RetryError
        with pytest.raises(RetryError):
            async for _ in connector.fetch_raw_data():
                pass
        
        # Should have tried 3 times (configured retry attempts)
        assert mock_http_client.get.call_count == 3
    
    @pytest.mark.asyncio 
    async def test_successful_retry_resets_state(self, mock_source, mock_db):
        """Test that successful retry properly processes feed."""
        mock_http_client = Mock(spec=httpx.AsyncClient)
        
        valid_rss = """<?xml version="1.0"?>
        <rss version="2.0">
          <channel>
            <title>Test Feed</title>
            <item>
              <title>Test Item</title>
              <guid>item-1</guid>
              <description>Test description</description>
            </item>
          </channel>
        </rss>"""
        
        responses = [
            httpx.NetworkError("Temporary error"),
            Mock(text=valid_rss, raise_for_status=Mock())
        ]
        mock_http_client.get = AsyncMock(side_effect=responses)
        
        connector = RSSConnector(mock_source, mock_db, mock_http_client)
        
        # Run full pipeline
        stats = await connector.run()
        
        assert stats['fetched'] == 1
        assert stats['new'] == 1
        assert stats['error'] == 0
        assert mock_db.insert_post.call_count == 1