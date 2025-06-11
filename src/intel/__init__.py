"""Daily Intelligence Report Package

This package provides the core functionality for the daily intelligence report system.
"""

import logging.config

from .logging_config import LOGGING_CONFIG

# Bootstrap logging configuration on import
logging.config.dictConfig(LOGGING_CONFIG)

__version__ = "0.1.0"
