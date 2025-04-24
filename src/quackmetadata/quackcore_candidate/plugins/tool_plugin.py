# src/quackmetadata/quackcore_candidate/plugins/tool_plugin.py
"""
Base classes for QuackTool plugins.

This module provides base classes for creating QuackTool plugins with
reduced boilerplate and standardized behavior.
"""

import tempfile
from abc import abstractmethod
from logging import Logger
from typing import Any

from quackcore.fs.service import get_service
from quackcore.integrations.core.results import IntegrationResult
from quackcore.integrations.google.drive import GoogleDriveService
from quackcore.logging import get_logger
from quackcore.paths import service as paths
from quackcore.plugins.protocols import QuackPluginMetadata

# Import from the workflow module we created earlier
from quackmetadata.quackcore_candidate.workflow.file_processor import (
    process_file_workflow,
)


# Define the protocol for QuackToolPlugin
class QuackToolPluginProtocol:
    """Protocol for QuackTool plugins."""

    # Add initialization state attribute to the protocol
    _initialized: bool

    @property
    def logger(self) -> Logger:
        """Get the logger for the plugin."""
        ...

    @property
    def name(self) -> str:
        """Get the name of the plugin."""
        ...

    @property
    def version(self) -> str:
        """Get the version of the plugin."""
        ...

    def get_metadata(self) -> QuackPluginMetadata:
        """
        Get metadata for the plugin.

        Returns:
            QuackPluginMetadata: Plugin metadata
        """
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


# Get filesystem service
fs = get_service()


class BaseQuackToolPlugin(QuackToolPluginProtocol):
    """
    Base class for QuackTool plugins.

    This class implements common functionality for QuackTool plugins,
    reducing boilerplate in concrete implementations.

    Attributes:
        tool_name: Name of the tool (override in subclass)
        tool_version: Version of the tool (override in subclass)
        tool_description: Description of the tool (override in subclass)
        tool_author: Author of the tool (override in subclass)
        tool_capabilities: List of tool capabilities (override in subclass)
    """

    # Override these in subclasses
    tool_name = "base_tool"
    tool_version = "0.1.0"
    tool_description = "Base QuackTool plugin"
    tool_author = "AI Product Engineer Team"
    tool_capabilities = []

    def __init__(self) -> None:
        """Initialize the plugin."""
        self._logger: Logger = get_logger(f"{__name__}.{self.tool_name}")
        self._drive_service = None
        self._initialized: bool = False

        # Create a temporary directory
        temp_result = fs.create_temp_directory(prefix=f"{self.tool_name}_")
        if temp_result.success:
            self._temp_dir: str = str(temp_result.path)
        else:
            self._temp_dir = tempfile.mkdtemp(prefix=f"{self.tool_name}_")

        # Resolve the output directory
        try:
            project_context = paths.detect_project_context()
            output_dir = (
                project_context.get_output_dir()
                if project_context.get_output_dir()
                else fs.normalize_path("./output")
            )
        except Exception:
            output_dir = fs.normalize_path("./output")

        dir_result = fs.create_directory(output_dir, exist_ok=True)
        if dir_result.success:
            self._output_dir = str(dir_result.path)
        else:
            self._logger.warning(
                f"Failed to create output directory: {dir_result.error}")
            self._output_dir = "./output"

    @property
    def logger(self) -> Logger:
        """Get the logger for the plugin."""
        return self._logger

    @property
    def name(self) -> str:
        """Get the name of the plugin."""
        return self.tool_name

    @property
    def version(self) -> str:
        """Get the version of the plugin."""
        return self.tool_version

    def get_metadata(self) -> QuackPluginMetadata:
        """
        Get metadata for the plugin.

        Returns:
            QuackPluginMetadata: Plugin metadata.
        """
        return QuackPluginMetadata(
            name=self.name,
            version=self.version,
            description=self.tool_description,
            author=self.tool_author,
            capabilities=self.tool_capabilities,
        )

    def initialize(self) -> IntegrationResult:
        """
        Initialize the plugin and its dependencies.

        Returns:
            IntegrationResult indicating success or failure.
        """
        if self._initialized:
            return IntegrationResult.success_result(
                message=f"{self.name} plugin already initialized"
            )

        try:
            # Initialize environment
            self._initialize_environment()

            # Initialize Google Drive
            self._drive_service = GoogleDriveService()
            drive_result = self._drive_service.initialize()
            if not drive_result.success:
                self._logger.warning(
                    f"Google Drive integration not available: {drive_result.error}")
                self._drive_service = None

            # Call the concrete initialization method
            init_result = self._initialize_plugin()
            if not init_result.success:
                return init_result

            self._initialized = True
            return IntegrationResult.success_result(
                message=f"{self.name} plugin initialized successfully"
            )
        except Exception as e:
            self.logger.exception(f"Failed to initialize {self.name} plugin")
            return IntegrationResult.error_result(
                f"Failed to initialize {self.name} plugin: {str(e)}"
            )

    def _initialize_environment(self) -> None:
        """
        Initialize environment variables from configuration.
        """
        try:
            # Import the tool's initialize function if available
            module_name = self.tool_name.lower()
            initialize_module = __import__(module_name, fromlist=["initialize"])
            if hasattr(initialize_module, "initialize"):
                initialize_module.initialize()
        except Exception as e:
            self.logger.warning(f"Failed to initialize environment: {e}")

    @abstractmethod
    def _initialize_plugin(self) -> IntegrationResult:
        """
        Initialize plugin-specific functionality.

        This method should be implemented by concrete plugin classes.

        Returns:
            IntegrationResult indicating success or failure.
        """
        pass

    def is_available(self) -> bool:
        """
        Check if the plugin is available.

        Returns:
            True if the plugin is available, False otherwise.
        """
        return self._initialized

    @abstractmethod
    def process_content(
            self,
            content: str,
            options: dict[str, Any]
    ) -> tuple[bool, Any, str]:
        """
        Process content with the plugin.

        This method should be implemented by concrete plugin classes.

        Args:
            content: The content to process
            options: Processing options

        Returns:
            Tuple of (success, result, error_message)
        """
        pass

    def process_file(
            self,
            file_path: str,
            output_path: str | None = None,
            options: dict[str, Any] | None = None,
    ) -> IntegrationResult:
        """
        Process a file using the plugin.

        Args:
            file_path: Path to the file to process
            output_path: Optional path for the output file
            options: Optional processing options

        Returns:
            IntegrationResult containing the processing result
        """
        if not self._initialized:
            init_result = self.initialize()
            if not init_result.success:
                return init_result

        # Use the standard file processing workflow
        return process_file_workflow(
            file_path=file_path,
            processor_func=self.process_content,
            output_path=output_path,
            options=options,
            drive_service=self._drive_service,
            temp_dir=self._temp_dir,
            output_dir=self._output_dir,
            output_extension=self._get_output_extension()
        )

    def _get_output_extension(self) -> str:
        """
        Get the extension for output files.

        Returns:
            Extension string including the dot
        """
        return ".json"
