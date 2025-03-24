# src/quacktool/__init__.py
"""
QuackTool: A QuackVerse tool for task automation.

This module serves as a starting point for building a custom QuackVerse tool
integrated with QuackCore.
"""

# Import version directly - this is a simple import that won't cause circular dependencies
from quacktool.version import __version__

# Define module-level variables for lazy loading
# We'll populate these with the actual objects when they're accessed
get_config = None
get_logger = None
process_asset = None
AssetConfig = None
ProcessingOptions = None
ProcessingResult = None

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


# Set up lazy import machinery
class _LazyLoader:
    """Helper class to implement lazy loading of module attributes."""

    @staticmethod
    def _get_config():
        """Lazy load get_config."""
        global get_config
        if get_config is None:
            from quacktool.config import get_config as _get_config
            get_config = _get_config
        return get_config

    @staticmethod
    def _get_logger():
        """Lazy load get_logger."""
        global get_logger
        if get_logger is None:
            from quacktool.config import get_logger as _get_logger
            get_logger = _get_logger
        return get_logger

    @staticmethod
    def _process_asset():
        """Lazy load process_asset."""
        global process_asset
        if process_asset is None:
            from quacktool.core import process_asset as _process_asset
            process_asset = _process_asset
        return process_asset

    @staticmethod
    def _get_asset_config():
        """Lazy load AssetConfig."""
        global AssetConfig
        if AssetConfig is None:
            from quacktool.models import AssetConfig as _AssetConfig
            AssetConfig = _AssetConfig
        return AssetConfig

    @staticmethod
    def _get_processing_options():
        """Lazy load ProcessingOptions."""
        global ProcessingOptions
        if ProcessingOptions is None:
            from quacktool.models import ProcessingOptions as _ProcessingOptions
            ProcessingOptions = _ProcessingOptions
        return ProcessingOptions

    @staticmethod
    def _get_processing_result():
        """Lazy load ProcessingResult."""
        global ProcessingResult
        if ProcessingResult is None:
            from quacktool.models import ProcessingResult as _ProcessingResult
            ProcessingResult = _ProcessingResult
        return ProcessingResult


# Create the single loader instance
_loader = _LazyLoader()


# Define __getattr__ to handle lazy imports
def __getattr__(name):
    """Lazily import and return attributes on first access."""
    if name == "get_config":
        return _loader._get_config()
    elif name == "get_logger":
        return _loader._get_logger()
    elif name == "process_asset":
        return _loader._process_asset()
    elif name == "AssetConfig":
        return _loader._get_asset_config()
    elif name == "ProcessingOptions":
        return _loader._get_processing_options()
    elif name == "ProcessingResult":
        return _loader._get_processing_result()

    raise AttributeError(f"module 'quacktool' has no attribute '{name}'")