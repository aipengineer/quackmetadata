# src/quackmetadata/plugins/__init__.py
"""
Plugins package for QuackMetadata.
"""

from quackmetadata.plugins.metadata import MetadataPlugin
from quackmetadata.plugins.plugin_factory import create_plugin

__all__ = ["MetadataPlugin", "create_plugin"]
