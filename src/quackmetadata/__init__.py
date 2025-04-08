# src/quackmetadata/__init__.py
"""
Initialization module for QuackMetadata.

This module handles environment setup and other initialization tasks
that should be performed when the application starts.
"""

import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# Import version directly - this is a simple import that won't cause circular dependencies
from quackmetadata.version import __version__

# Import lazily-loaded modules directly
from quackmetadata.config import get_config, get_logger
from quackmetadata.plugins.metadata import MetadataPlugin
from quackmetadata.schemas.metadata import AuthorProfile, Metadata

# Define what this package exposes
__all__ = [
    # Version
    "__version__",
    # Config
    "get_config",
    "get_logger",
    # Metadata functionality
    "MetadataPlugin",
    "Metadata",
    "AuthorProfile",
    "initialize"
]


def ensure_directories() -> None:
    """Ensure necessary directories exist."""
    try:
        Path("./output").mkdir(exist_ok=True, parents=True)
        Path("./temp").mkdir(exist_ok=True, parents=True)
        Path("./logs").mkdir(exist_ok=True, parents=True)
        logger.debug("Directory structure initialized")
    except Exception as e:
        logger.warning(f"Error creating directories: {e}")


def initialize() -> None:
    """Initialize QuackMetadata application."""
    ensure_directories()

    # Let QuackCore handle environment variables when its APIs are called
    logger.debug("QuackMetadata initialized")