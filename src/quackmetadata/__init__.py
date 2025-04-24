# src/quackmetadata/__init__.py
"""
QuackMetadata: Extract structured metadata from text documents using LLMs.

This module provides functionality for extracting metadata from text files,
validating against schemas, and integrating with Google Drive.
"""

import logging
from pathlib import Path

# Import core functionality
from quackmetadata.schemas import AuthorProfile, Metadata
from quackmetadata.tool import extract_metadata, process_file, run

# Import version
from quackmetadata.version import __version__

# Initialize logger
logger = logging.getLogger(__name__)

# Define what this package exposes
__all__ = [
    # Version
    "__version__",
    # Core functionality
    "extract_metadata",
    "process_file",
    "run",
    # Data models
    "Metadata",
    "AuthorProfile",
    # Initialization
    "initialize",
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
    logger.debug("QuackMetadata initialized")
