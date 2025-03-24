# src/quacktool/__init__.py
"""
QuackTool: A QuackVerse tool for task automation.

This module serves as a starting point for building a custom QuackVerse tool
integrated with QuackCore.
"""

# Re-export commonly used components for convenience
from quacktool.config import get_logger
from quacktool.core import process_asset
from quacktool.models import AssetConfig, ProcessingOptions, ProcessingResult

# Import version from version.py instead of defining it here
from quacktool.version import __version__

# Initialize config lazily when actually needed, not at import time
from quacktool.config import get_config

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