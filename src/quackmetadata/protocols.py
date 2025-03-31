# src/quackmetadata/protocols.py
"""
Protocol definitions for QuackMetadata.

This module defines protocols that plugins must implement to be
compatible with QuackCore and QuackMetadata.
"""

from logging import Logger
from typing import Protocol, runtime_checkable, Any

from quackcore.integrations.core.results import IntegrationResult
from quackcore.plugins.protocols import QuackPluginProtocol


@runtime_checkable
class QuackToolPluginProtocol(QuackPluginProtocol, Protocol):
    """Protocol for QuackTool plugins."""

    # Add initialization state attribute to the protocol
    _initialized: bool

    @property
    def logger(self) -> Logger:
        """Get the logger for the plugin."""
        ...

    @property
    def version(self) -> str:
        """Get the version of the plugin."""
        ...

    def initialize(self) -> IntegrationResult:
        """Initialize the plugin."""
        ...

    def is_available(self) -> bool:
        """Check if the plugin is available."""
        ...

    def process_file(
        self,
        file_path: str,
        output_path: str | None = None,
        options: dict[str, Any] | None = None,
    ) -> IntegrationResult:
        """Process a file using the plugin."""
        ...