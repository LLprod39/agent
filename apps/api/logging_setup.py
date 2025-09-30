"""Centralized logging setup for the application."""

import logging
from typing import Optional

from ..orchestrator.observability.logging import StructuredLogger
from config.settings import get_settings

# Global structured logger instance
_structured_logger: Optional[StructuredLogger] = None


def get_structured_logger() -> StructuredLogger:
    """Get or create the global structured logger instance."""
    global _structured_logger
    
    if _structured_logger is None:
        settings = get_settings()
        
        # Load observability config if available
        logging_config = {
            "level": settings.log_level,
            "format": "json",  # Always use JSON format for structured logging
            "enabled": True,
        }
        
        _structured_logger = StructuredLogger(logging_config)
    
    return _structured_logger


def setup_structured_logging():
    """Initialize structured logging for the application."""
    logger = get_structured_logger()
    logger.info("Structured logging initialized", component="logging_setup")
    return logger


# Convenience functions for quick logging
def log_info(message: str, **kwargs):
    """Log info message with structured logger."""
    logger = get_structured_logger()
    logger.info(message, **kwargs)


def log_warning(message: str, **kwargs):
    """Log warning message with structured logger."""
    logger = get_structured_logger()
    logger.warning(message, **kwargs)


def log_error(message: str, **kwargs):
    """Log error message with structured logger."""
    logger = get_structured_logger()
    logger.error(message, **kwargs)


def log_debug(message: str, **kwargs):
    """Log debug message with structured logger."""
    logger = get_structured_logger()
    logger.debug(message, **kwargs)
