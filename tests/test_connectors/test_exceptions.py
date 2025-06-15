"""
Tests for connector exceptions.
"""
from src.connectors.exceptions import (
    AuthenticationError,
    ConnectorError,
    NetworkError,
    ParseError,
    RateLimitError,
)


def test_connector_error_base():
    """Test base ConnectorError."""
    error = ConnectorError("Test error")
    assert str(error) == "Test error"
    assert isinstance(error, Exception)


def test_rate_limit_error():
    """Test RateLimitError with retry_after."""
    # Test with default message
    error = RateLimitError()
    assert str(error) == "Rate limit exceeded"
    assert error.retry_after is None
    
    # Test with custom message and retry_after
    error = RateLimitError("Custom message", retry_after=60)
    assert str(error) == "Custom message"
    assert error.retry_after == 60
    
    # Test inheritance
    assert isinstance(error, ConnectorError)


def test_authentication_error():
    """Test AuthenticationError."""
    error = AuthenticationError("Auth failed")
    assert str(error) == "Auth failed"
    assert isinstance(error, ConnectorError)


def test_network_error():
    """Test NetworkError."""
    error = NetworkError("Network failed")
    assert str(error) == "Network failed"
    assert isinstance(error, ConnectorError)


def test_parse_error():
    """Test ParseError."""
    error = ParseError("Parse failed")
    assert str(error) == "Parse failed"
    assert isinstance(error, ConnectorError)