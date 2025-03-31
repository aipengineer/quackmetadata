# src/quackmetadata/__init__.py
"""
QuackMetadata: A QuackVerse tool for extracting structured metadata from documents.

This module serves as a starting point for building a custom QuackVerse tool
integrated with QuackCore.
"""

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
]