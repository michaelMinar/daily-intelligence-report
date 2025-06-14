"""
Connector module for ingesting content from various sources.
"""
from typing import Dict, Type

from src.models.source import SourceType

from .base import BaseConnector

# Registry will be populated as connectors are implemented
CONNECTOR_REGISTRY: Dict[SourceType, Type[BaseConnector]] = {}


def get_connector_class(source_type: SourceType) -> Type[BaseConnector]:
    """Factory method to get connector class by source type."""
    if source_type not in CONNECTOR_REGISTRY:
        raise ValueError(f"No connector registered for source type: {source_type}")
    return CONNECTOR_REGISTRY[source_type]


def register_connector(source_type: SourceType, connector_class: Type[BaseConnector]) -> None:
    """Register a connector class for a source type."""
    CONNECTOR_REGISTRY[source_type] = connector_class