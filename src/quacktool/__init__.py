# src/quacktool/__init__.py
"""
QuackTool: A QuackVerse tool for task automation.

This module serves as a starting point for building a custom QuackVerse tool
integrated with QuackCore.
"""

# Import version directly - this is a simple import that won't cause circular dependencies
from quacktool.version import __version__

# Import lazily-loaded modules directly
from quacktool.config import get_config, get_logger
from quacktool.core import process_asset
from quacktool.models import AssetConfig, ProcessingOptions, ProcessingResult

# Define what this package exposes
__all__ = [
    # Version
    "__version__",
    # Config
    "get_config",
    "get_logger",
    # Core functionality
    "process_asset",
    # Models
    "AssetConfig",
    "ProcessingOptions",
    "ProcessingResult",
]