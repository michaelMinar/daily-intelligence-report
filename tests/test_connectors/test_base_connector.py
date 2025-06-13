"""
Tests for base connector functionality.
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime
from typing import AsyncIterator, Dict, Any, Optional

import httpx

from src.connectors.base import BaseConnector
from src.models.post import Post
from src.models.source import Source, SourceType
from src.database import Database


class MockConnector(BaseConnector):
    """Mock implementation of BaseConnector for testing."""
    
    def __init__(self, source: Source, db: Database, http_client: httpx.AsyncClient):
        super().__init__(source, db, http_client)
        self.raw_data_items = []
        self.normalize_responses = {}
    
    async def fetch_raw_data(self, fetch_state: Optional[Dict[str, Any]] = None) -> AsyncIterator[Dict[str, Any]]:
        """Yield test data."""
        for item in self.raw_data_items:
            yield item
    
    def normalize_to_post(self, raw_data: Dict[str, Any]) -> Optional[Post]:
        """Return pre-configured post or None."""
        return self.normalize_responses.get(id(raw_data))


@pytest.fixture
def mock_source():
    """Create a mock source."""
    return Source(
        id=1,
        type=SourceType.RSS,
        identifier="https://example.com/feed.xml",
        name="Test Source",
        active=True
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
def mock_http_client():
    """Create a mock HTTP client."""
    return Mock(spec=httpx.AsyncClient)


@pytest.fixture
def mock_connector(mock_source, mock_db, mock_http_client):
    """Create a mock connector instance."""
    return MockConnector(mock_source, mock_db, mock_http_client)


class TestBaseConnector:
    """Tests for BaseConnector."""
    
    def test_initialization(self, mock_source, mock_db, mock_http_client):
        """Test connector initialization."""
        connector = MockConnector(mock_source, mock_db, mock_http_client)
        assert connector.source == mock_source
        assert connector.db == mock_db
        assert connector.http_client == mock_http_client
        assert "MockConnector:Test Source" in connector.logger.name
    
    def test_extract_fetch_state_with_guid(self):
        """Test extract_fetch_state with source_guid."""
        connector = MockConnector(Mock(), Mock(), Mock())
        post = Post(
            source_id=1,
            title="Test",
            content="Content",
            source_guid="guid-123",
            url="https://example.com"
        )
        
        state = connector.extract_fetch_state(post)
        assert state['last_seen_id'] == "guid-123"
        assert 'last_fetch_timestamp' in state
    
    def test_extract_fetch_state_with_url(self):
        """Test extract_fetch_state falls back to URL when no GUID."""
        connector = MockConnector(Mock(), Mock(), Mock())
        post = Post(
            source_id=1,
            title="Test",
            content="Content",
            source_guid=None,
            url="https://example.com"
        )
        
        state = connector.extract_fetch_state(post)
        assert state['last_seen_id'] == "https://example.com"
    
    @pytest.mark.asyncio
    async def test_run_successful_flow(self, mock_connector, mock_db):
        """Test successful run with new posts."""
        # Setup test data
        raw_item1 = {"id": 1, "data": "test1"}
        raw_item2 = {"id": 2, "data": "test2"}
        
        post1 = Post(
            source_id=1,
            title="Post 1",
            content="Content 1",
            source_guid="guid-1"
        )
        post2 = Post(
            source_id=1,
            title="Post 2",
            content="Content 2",
            source_guid="guid-2"
        )
        
        mock_connector.raw_data_items = [raw_item1, raw_item2]
        mock_connector.normalize_responses = {
            id(raw_item1): post1,
            id(raw_item2): post2
        }
        
        # Run connector
        stats = await mock_connector.run()
        
        # Verify stats
        assert stats['fetched'] == 2
        assert stats['new'] == 2
        assert stats['duplicate'] == 0
        assert stats['error'] == 0
        
        # Verify database calls
        assert mock_db.get_source_fetch_state.call_count == 1
        assert mock_db.post_exists_by_hash.call_count == 2
        assert mock_db.insert_post.call_count == 2
        assert mock_db.update_source_fetch_state.call_count == 1
    
    @pytest.mark.asyncio
    async def test_run_with_duplicates(self, mock_connector, mock_db):
        """Test run with duplicate detection."""
        # Setup test data
        raw_item = {"id": 1, "data": "test"}
        post = Post(
            source_id=1,
            title="Post",
            content="Content",
            source_guid="guid-1"
        )
        
        mock_connector.raw_data_items = [raw_item]
        mock_connector.normalize_responses = {id(raw_item): post}
        
        # Mark post as duplicate
        mock_db.post_exists_by_hash.return_value = True
        
        # Run connector
        stats = await mock_connector.run()
        
        # Verify stats
        assert stats['fetched'] == 1
        assert stats['new'] == 0
        assert stats['duplicate'] == 1
        assert stats['error'] == 0
        
        # Verify no insert was called
        assert mock_db.insert_post.call_count == 0
        # Verify no state update (no new posts)
        assert mock_db.update_source_fetch_state.call_count == 0
    
    @pytest.mark.asyncio
    async def test_run_with_normalization_error(self, mock_connector, mock_db):
        """Test run with normalization errors."""
        # Setup test data with error
        raw_item = {"id": 1, "data": "test"}
        mock_connector.raw_data_items = [raw_item]
        
        # Make normalize_to_post raise an exception
        mock_connector.normalize_to_post = Mock(side_effect=Exception("Normalize error"))
        
        # Run connector
        stats = await mock_connector.run()
        
        # Verify stats
        assert stats['fetched'] == 1
        assert stats['new'] == 0
        assert stats['duplicate'] == 0
        assert stats['error'] == 1
    
    @pytest.mark.asyncio
    async def test_run_with_incremental_fetch(self, mock_connector, mock_db):
        """Test run with previous fetch state."""
        # Setup previous state
        previous_state = {
            'last_seen_id': 'guid-123',
            'last_fetch_timestamp': '2024-01-01T00:00:00'
        }
        mock_db.get_source_fetch_state.return_value = previous_state
        
        # Run connector
        await mock_connector.run()
        
        # Verify fetch_raw_data was called with state
        mock_db.get_source_fetch_state.assert_called_once_with(1)
    
    @pytest.mark.asyncio
    async def test_run_with_none_normalization(self, mock_connector, mock_db):
        """Test run when normalize_to_post returns None (filtered items)."""
        raw_item = {"id": 1, "data": "test"}
        mock_connector.raw_data_items = [raw_item]
        mock_connector.normalize_responses = {id(raw_item): None}
        
        stats = await mock_connector.run()
        
        # Item was fetched but not processed
        assert stats['fetched'] == 1
        assert stats['new'] == 0
        assert stats['duplicate'] == 0
        assert stats['error'] == 0
        
        # No database operations should occur
        assert mock_db.post_exists_by_hash.call_count == 0
        assert mock_db.insert_post.call_count == 0