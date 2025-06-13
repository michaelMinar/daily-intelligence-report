"""
RSS-specific configuration.
"""
from typing import Optional, List
from .base import BaseConnectorConfig


class RSSConfig(BaseConnectorConfig):
    """Configuration specific to RSS connectors."""
    
    parse_full_content: bool = False
    filter_keywords: Optional[List[str]] = None
    exclude_keywords: Optional[List[str]] = None