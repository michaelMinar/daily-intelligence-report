"""
Exception hierarchy for connector errors.
"""
from typing import Optional


class ConnectorError(Exception):
    """Base exception for all connector errors."""
    pass


class RateLimitError(ConnectorError):
    """Raised when API rate limit is exceeded."""
    
    def __init__(self, message: str = "Rate limit exceeded", retry_after: Optional[int] = None):
        super().__init__(message)
        self.retry_after = retry_after


class AuthenticationError(ConnectorError):
    """Raised when authentication fails."""
    pass


class NetworkError(ConnectorError):
    """Raised for network-related failures."""
    pass


class ParseError(ConnectorError):
    """Raised when content parsing fails."""
    pass