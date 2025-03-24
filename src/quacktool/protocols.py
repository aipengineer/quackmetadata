# src/quacktool/protocols.py
from quackcore.plugins.protocols import QuackPluginProtocol
from quackcore.integrations.results import IntegrationResult
from typing import Protocol, runtime_checkable


@runtime_checkable
class QuackToolPluginProtocol(QuackPluginProtocol, Protocol):
    """Protocol for QuackTool plugins."""

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
            options: dict[str, object] | None = None,
    ) -> IntegrationResult:
        """Process a file using the plugin."""
        ...