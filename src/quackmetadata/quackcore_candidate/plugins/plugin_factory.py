# src/quackmetadata/quackcore_candidate/plugins/plugin_factory.py
"""
Plugin factory module for QuackMetadata.

This module provides factory functions for creating plugin instances
that can be discovered by QuackCore's plugin system.
"""

from typing import cast

from quackcore.logging import get_logger

from quackmetadata.plugin import MetadataPlugin
from quackmetadata.protocols import QuackToolPluginProtocol

logger = get_logger(__name__)

# Global instance reference for singleton pattern
_plugin_instance = None


def create_plugin() -> QuackToolPluginProtocol:
    """
    Create and return a QuackMetadata plugin instance.

    This function is used by QuackCore's plugin discovery system to
    create an instance of the plugin.

    Returns:
        An instance of the QuackMetadata plugin
    """
    global _plugin_instance

    if _plugin_instance is None:
        logger.debug("Creating new MetadataPlugin instance")
        _plugin_instance = MetadataPlugin()

    return cast(QuackToolPluginProtocol, _plugin_instance)
