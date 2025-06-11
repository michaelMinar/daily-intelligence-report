"""Logging utilities for structured logging."""

import logging
from typing import Any


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance for the given name.

    Args:
        name: Logger name, typically __name__ from calling module

    Returns:
        Logger instance configured with intel settings
    """
    return logging.getLogger(name)


def log_with_context(
    logger: logging.Logger,
    level: int,
    message: str,
    **context: Any,
) -> None:
    """Log a message with structured context.

    Args:
        logger: Logger instance
        level: Logging level (e.g., logging.INFO)
        message: Log message
        **context: Additional context to include in log
    """
    extra = {"context": context} if context else {}
    logger.log(level, message, extra=extra)


def log_operation(
    logger: logging.Logger,
    operation: str,
    **context: Any,
) -> None:
    """Log an operation with context for traceability.

    Args:
        logger: Logger instance
        operation: Description of the operation
        **context: Additional context (e.g., source_id, post_id)
    """
    log_with_context(logger, logging.INFO, f"Operation: {operation}", **context)
