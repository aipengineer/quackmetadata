# src/quackmetadata/plugins/metadata.py
"""
QuackMetadata plugin for metadata extraction.

This module implements the metadata extraction plugin that integrates with QuackCore
to download files from Google Drive, extract metadata using LLMs, and upload
results back to Google Drive.
"""

import tempfile
import time
from logging import Logger
from typing import Any, Protocol

from quackcore.errors import QuackIntegrationError

# Use QuackCore FS for all file operations.
from quackcore.fs.service import get_service
from quackcore.integrations.core.results import IntegrationResult
from quackcore.integrations.google.drive import GoogleDriveService
from quackcore.integrations.llms import (
    ChatMessage,
    LLMOptions,
    MockLLMClient,
    RoleType,
    create_integration,
)
from quackcore.logging import get_logger

# Import QuackCore Paths for project-aware path resolution.
from quackcore.paths import service as paths
from quackcore.plugins.protocols import QuackPluginMetadata

from quackmetadata.protocols import QuackToolPluginProtocol
from quackmetadata.schemas.metadata import Metadata
from quackmetadata.utils.prompt_engine import get_template_path, render_prompt
from quackmetadata.utils.rarity import calculate_rarity

fs = get_service()


# Define the SupportsWrite protocol.
class SupportsWrite(Protocol):
    def write(self, s: str) -> int: ...


class MetadataPluginError(Exception):
    """Exception raised for errors in the MetadataPlugin."""

    pass


class MetadataPlugin(QuackToolPluginProtocol):
    """
    Plugin for extracting metadata from text documents using LLMs.

    This plugin can:
      1. Download a text file from Google Drive
      2. Extract structured metadata using an LLM
      3. Validate the output against a schema
      4. Upload the results back to Google Drive
    """

    def __init__(self) -> None:
        """Initialize the metadata plugin."""
        self._logger: Logger = get_logger(__name__)
        self._drive_service = None
        self._llm_service = None
        self._initialized: bool = False
        self._using_mock: bool = False

        # Create a temporary directory using QuackCore FS.
        temp_result = fs.create_temp_directory(prefix="quackmetadata_")
        if temp_result.success:
            self._temp_dir: str = str(temp_result.path)
        else:
            # Fallback to using tempfile if FS operation fails.
            self._temp_dir = tempfile.mkdtemp(prefix="quackmetadata_")

        # Instead of hard-coding "./output", resolve the output directory using QuackCore Paths.
        try:
            project_context = paths.detect_project_context()
            # If a project context exists, use its defined output directory.
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
                f"Failed to create output directory: {dir_result.error}"
            )
            self._output_dir = "./output"

    @property
    def logger(self) -> Logger:
        """Get the logger for the plugin."""
        return self._logger

    @property
    def name(self) -> str:
        """Get the name of the plugin."""
        return "metadata"

    @property
    def version(self) -> str:
        """Get the version of the plugin."""
        return "0.1.0"

    def get_metadata(self) -> QuackPluginMetadata:
        """
        Get metadata for the plugin.

        Returns:
            QuackPluginMetadata: Plugin metadata.
        """
        return QuackPluginMetadata(
            name=self.name,
            version=self.version,
            description=(
                "QuackMetadata plugin for metadata extraction. This plugin downloads a file from Google Drive, "
                "extracts structured metadata using language models, validates the output against a schema, "
                "and uploads the results back to Google Drive."
            ),
            author="AI Product Engineer Team",
            capabilities=[
                "download file",
                "LLM-based metadata extraction",
                "metadata validation",
                "upload file",
            ],
        )

    def initialize(self) -> IntegrationResult:
        """
        Initialize the plugin and its dependencies.

        Returns:
            IntegrationResult indicating success or failure.
        """
        if self._initialized:
            return IntegrationResult.success_result(
                message="MetadataPlugin already initialized"
            )

        try:
            self._initialize_environment()

            self._drive_service = GoogleDriveService()
            drive_result = self._drive_service.initialize()
            if not drive_result.success:
                return IntegrationResult.error_result(
                    f"Failed to initialize Google Drive: {drive_result.error}"
                )

            try:
                self._llm_service = create_integration()
                llm_result = self._llm_service.initialize()
                if not llm_result.success:
                    error_message = (
                        f"Failed to initialize LLM service: {llm_result.error}"
                    )
                    if "API key not provided" in str(llm_result.error):
                        error_message += "\nPlease ensure your API key is properly configured in quack_config.yaml or as an environment variable."
                    raise QuackIntegrationError(error_message)
            except QuackIntegrationError as e:
                if "API key not provided" in str(e):
                    self.logger.error(
                        "LLM API key missing. Please configure it in quack_config.yaml under integrations.llm.openai.api_key or set the OPENAI_API_KEY environment variable."
                    )
                self.logger.warning(
                    "Falling back to MockLLMClient for development/testing"
                )
                self._llm_service = MockLLMClient()
                self._using_mock = True

            self._initialized = True

            if self._using_mock:
                return IntegrationResult.success_result(
                    message=(
                        "MetadataPlugin initialized with MockLLMClient. "
                        "Note: Results will be simulated, not real metadata extraction."
                    )
                )
            else:
                return IntegrationResult.success_result(
                    message="MetadataPlugin initialized successfully"
                )
        except Exception as e:
            self.logger.exception("Failed to initialize MetadataPlugin")
            return IntegrationResult.error_result(
                f"Failed to initialize MetadataPlugin: {str(e)}"
            )

    def _initialize_environment(self) -> None:
        """
        Initialize environment variables from configuration.
        """
        try:
            from quackmetadata import initialize

            initialize()
        except Exception as e:
            self.logger.warning(f"Failed to initialize environment: {e}")

    def is_available(self) -> bool:
        """
        Check if the plugin is available.

        Returns:
            True if the plugin is available, False otherwise.
        """
        return self._initialized

    def process_file(self, file_path: str, output_path: str | None = None,
                     options: dict[str, Any] | None = None) -> IntegrationResult:
        """
        Process a file using the metadata plugin.

        Args:
            file_path: Path to the file to process (local path or Google Drive ID).
            output_path: Optional path for the output metadata file.
            options: Optional processing options.

        Returns:
            IntegrationResult containing the metadata extraction result.
        """
        if not self._initialized:
            init_result = self.initialize()
            if not init_result.success:
                return init_result

        options = options or {}

        if self._using_mock:
            self.logger.warning(
                "Using MockLLMClient - results will be simulated, not real metadata extraction. "
                "Configure your LLM API key to use actual language models."
            )

        try:
            # Add detailed logging
            self.logger.debug(
                f"process_file received file_path type: {type(file_path)}, value: {file_path}")

            # Import exactly what we need
            from quackcore.fs import PathResult

            # First, ensure we have a string representation to work with
            file_path_str = ""

            # For Drive ID detection, we need a raw string before any normalization
            raw_str = str(file_path)

            # Check for Drive ID pattern in raw input
            is_likely_drive_id = (len(raw_str) >= 25 and len(raw_str) <= 45 and
                                  "/" not in raw_str and "\\" not in raw_str and
                                  "." not in raw_str)

            # Extract clean path string
            if isinstance(file_path, PathResult):
                # For PathResult objects
                file_path_str = str(file_path.path)
                self.logger.debug("Extracted path from PathResult")
            elif isinstance(file_path, str):
                if file_path.startswith("success="):
                    # For string representations of PathResult
                    self.logger.warning(
                        "Detected string representation of PathResult, fixing...")
                    import re
                    path_match = re.search(r"path=PosixPath\('([^']+)'\)", file_path)
                    if path_match:
                        file_path_str = path_match.group(1)
                        self.logger.debug(f"Extracted path: {file_path_str}")
                    else:
                        file_path_str = file_path
                else:
                    # For regular strings
                    file_path_str = file_path
            else:
                # For any other type, try to get a string representation
                try:
                    # Try to access path attribute
                    if hasattr(file_path, "path"):
                        path_attr = file_path.path
                        if path_attr is not None:
                            file_path_str = str(path_attr)
                            self.logger.debug(
                                "Extracted path from object with path attribute")
                    # Try to access data attribute
                    elif hasattr(file_path, "data"):
                        data_attr = file_path.data
                        if data_attr is not None:
                            file_path_str = str(data_attr)
                            self.logger.debug(
                                "Extracted path from object with data attribute")
                    else:
                        # Fallback to string conversion
                        file_path_str = str(file_path)
                except Exception as e:
                    self.logger.warning(f"Error extracting path, using str(): {e}")
                    file_path_str = str(file_path)

            self.logger.debug(f"Using file_path_str: {file_path_str}")

            # Process output path similarly
            output_path_str = None
            if output_path is not None:
                try:
                    if isinstance(output_path, PathResult):
                        output_path_str = str(output_path.path)
                    elif isinstance(output_path, str):
                        output_path_str = output_path
                    elif hasattr(output_path, "path"):
                        path_attr = output_path.path
                        if path_attr is not None:
                            output_path_str = str(path_attr)
                    elif hasattr(output_path, "data"):
                        data_attr = output_path.data
                        if data_attr is not None:
                            output_path_str = str(data_attr)
                    else:
                        output_path_str = str(output_path)
                except Exception as e:
                    self.logger.warning(
                        f"Error extracting output path, using str(): {e}")
                    output_path_str = str(output_path)

            # Special case for Drive IDs - detect early and process directly
            if is_likely_drive_id:
                self.logger.info(
                    f"Detected Google Drive file ID from raw input: {raw_str}")
                return self._process_drive_file(raw_str, output_path_str, options)

            # Secondary check for Drive ID after path extraction
            if (len(file_path_str) >= 25 and len(file_path_str) <= 45 and
                    "/" not in file_path_str and "\\" not in file_path_str and
                    "." not in file_path_str):
                self.logger.info(
                    f"Detected Google Drive file ID after path processing: {file_path_str}")
                return self._process_drive_file(file_path_str, output_path_str, options)

            # Get file info to check if it exists locally
            file_info = fs.get_file_info(file_path_str)

            # Final fallback check for Drive ID
            is_drive_id = (not file_info.success or not file_info.exists) and (
                    "/" not in file_path_str and "\\" not in file_path_str
            )

            if is_drive_id:
                self.logger.info(
                    f"File not found locally, treating as Google Drive ID: {file_path_str}")
                return self._process_drive_file(file_path_str, output_path_str, options)
            else:
                self.logger.info(f"Processing as local file: {file_path_str}")
                return self._process_local_file(file_path_str, output_path_str, options)

        except Exception as e:
            self.logger.exception(f"Failed to process file: {e}")
            return IntegrationResult.error_result(f"Failed to process file: {str(e)}")

    def _process_drive_file(
        self, file_id: str, output_path: str | None, options: dict[str, Any]
    ) -> IntegrationResult:
        """
        Process a file from Google Drive.

        Args:
            file_id: Google Drive file ID.
            output_path: Optional path for the output metadata file.
            options: Processing options.

        Returns:
            IntegrationResult containing the metadata extraction result.
        """
        self.logger.info(f"Downloading file from Google Drive with ID: {file_id}")

        # Download the file to the temporary directory
        temp_dir_str = str(self._temp_dir)
        download_result = self._drive_service.download_file(
            remote_id=file_id, local_path=temp_dir_str
        )
        if not download_result.success:
            return IntegrationResult.error_result(
                f"Failed to download file from Google Drive: {download_result.error}"
            )

        # Ensure we have a clean local path
        path_result = fs.normalize_path(download_result.content)
        local_path = str(path_result.path) if path_result.success else str(
            download_result.content)

        self.logger.info(f"Downloaded file to: {local_path}")

        file_info_result = self._drive_service.get_file_info(remote_id=file_id)
        if not file_info_result.success:
            return IntegrationResult.error_result(
                f"Failed to get file info from Google Drive: {file_info_result.error}"
            )

        file_info = file_info_result.content
        file_name = file_info.get("name", "unknown")

        # Process the downloaded local file.
        output_str = str(output_path) if output_path else None
        result = self._process_local_file(local_path, output_str, options)

        if result.success and not options.get("dry_run", False):
            metadata_path = result.content.get("metadata_path")
            if metadata_path:
                parent_id = file_info.get("parents", [None])[0]
                metadata_path_str = str(metadata_path)
                upload_result = self._drive_service.upload_file(
                    file_path=metadata_path_str, parent_folder_id=parent_id
                )
                if upload_result.success:
                    result.content["drive_file_id"] = upload_result.content
                    self.logger.info(
                        f"Uploaded metadata file to Google Drive with ID: {upload_result.content}"
                    )
                else:
                    self.logger.error(
                        f"Failed to upload metadata file to Google Drive: {upload_result.error}"
                    )

        if result.success:
            result.content["original_file_name"] = file_name

        return result

    def _process_local_file(
            self, file_path: str, output_path: str | None, options: dict[str, Any]
    ) -> IntegrationResult:
        """
        Process a local file.
        """
        import os
        # Ensure we're using a clean string path
        file_path_str = str(file_path)

        # Get file info using the string path
        file_info = fs.get_file_info(file_path_str)
        if not file_info.success or not file_info.exists:
            return IntegrationResult.error_result(f"File not found: {file_path_str}")
        if not file_info.is_file:
            return IntegrationResult.error_result(f"Not a file: {file_path_str}")

        try:
            self.logger.info(f"Reading file: {file_path_str}")
            read_result = fs.read_text(file_path_str, encoding="utf-8")
            if not read_result.success:
                return IntegrationResult.error_result(
                    f"Failed to read file: {read_result.error}"
                )
            content = read_result.content

            metadata_result = self._extract_metadata(content=content, options=options)
            if not metadata_result.success:
                return metadata_result
            metadata = metadata_result.content

            # When determining output path:
            if output_path:
                metadata_path = str(output_path)
            else:
                # Use os.path directly for simplicity and reliability
                basename = os.path.basename(file_path_str)
                stem = os.path.splitext(basename)[0]
                metadata_path = os.path.join(str(self._output_dir),
                                             f"{stem}.metadata.json")

            self.logger.info(f"Writing metadata to: {metadata_path}")
            metadata_dict = metadata.model_dump()
            write_result = fs.write_json(
                metadata_path, metadata_dict, atomic=True, indent=2
            )
            if not write_result.success:
                return IntegrationResult.error_result(
                    f"Failed to write metadata file: {write_result.error}"
                )

            card = self._create_metadata_card(metadata)

            # Use os.path to extract the filename for display
            filename = os.path.basename(file_path_str)

            message = f"Successfully extracted metadata from {filename}"
            if self._using_mock:
                message += " (using mock data - not actual language model analysis)"

            return IntegrationResult.success_result(
                content={
                    "metadata": metadata_dict,
                    "metadata_path": metadata_path,
                    "card": card,
                    "using_mock": self._using_mock,
                },
                message=message,
            )

        except Exception as e:
            self.logger.exception(f"Failed to process local file: {e}")
            return IntegrationResult.error_result(f"Failed to process file: {str(e)}")

    def _extract_metadata(
        self, content: str, options: dict[str, Any]
    ) -> IntegrationResult:
        """
        Extract metadata from content using an LLM.

        Args:
            content: Text content to extract metadata from.
            options: Processing options.

        Returns:
            IntegrationResult containing the extracted metadata.
        """
        max_retries = options.get("retries", 3)
        prompt_template = options.get("prompt_template")
        verbose = options.get("verbose", False)

        if prompt_template:
            # Ensure we have a clean path string for user-provided template
            template_path = self._ensure_clean_path(prompt_template)
        else:
            # get_template_path already returns a string, no need for additional processing
            template_path = get_template_path("generic", "metadata")

        try:
            prompt = render_prompt(
                template_path=template_path, context={"content": content}
            )
        except Exception as e:
            return IntegrationResult.error_result(f"Failed to render prompt: {str(e)}")

        if verbose:
            self.logger.info(f"Generated prompt:\n{prompt}")

        messages = [ChatMessage(role=RoleType.USER, content=prompt)]
        llm_options = LLMOptions(temperature=0.1, max_tokens=2000)

        for attempt in range(max_retries):
            try:
                self.logger.info(
                    f"Sending prompt to LLM (attempt {attempt + 1}/{max_retries})"
                )
                result = self._llm_service.chat(messages=messages, options=llm_options)
                if not result.success:
                    self.logger.error(f"LLM call failed: {result.error}")
                    if "API key" in str(result.error):
                        return IntegrationResult.error_result(
                            f"LLM API key error: {result.error}. Please configure your API key in quack_config.yaml or set the appropriate environment variable."
                        )
                    if attempt < max_retries - 1:
                        time.sleep(1)
                        continue
                    return IntegrationResult.error_result(
                        f"Failed to get response from LLM: {result.error}"
                    )

                response = result.content
                if verbose:
                    self.logger.info(f"LLM response:\n{response}")

                try:
                    json_str = self._extract_json(response)
                    import json
                    try:
                        metadata_dict = json.loads(json_str)
                        metadata = Metadata.model_validate(metadata_dict)
                        calculated_rarity = calculate_rarity(metadata.summary)
                        if calculated_rarity != metadata.rarity:
                            self.logger.info(
                                f"Overriding LLM rarity '{metadata.rarity}' with calculated rarity '{calculated_rarity}'"
                            )
                            metadata.rarity = calculated_rarity

                        return IntegrationResult.success_result(
                            content=metadata, message="Successfully extracted metadata"
                        )
                    except json.JSONDecodeError as json_err:
                        raise ValueError(f"Invalid JSON format: {json_err}")

                except Exception as e:
                    self.logger.error(f"Error parsing or validating metadata: {e}")
                    if verbose:
                        self.logger.error(f"Invalid response: {response}")

                if attempt < max_retries - 1:
                    messages.append(
                        ChatMessage(role=RoleType.ASSISTANT, content=response)
                    )
                    messages.append(
                        ChatMessage(
                            role=RoleType.USER,
                            content="The response couldn't be properly parsed as JSON or didn't match the required schema. "
                            "Please provide a valid JSON response with all required fields using the exact structure specified in the initial prompt. Return only the JSON object with no markdown or additional text.",
                        )
                    )
                    time.sleep(1)
            except Exception as e:
                self.logger.exception(f"Error during metadata extraction: {e}")
                if attempt < max_retries - 1:
                    time.sleep(1)
                else:
                    return IntegrationResult.error_result(
                        f"Failed to extract metadata after {max_retries} attempts: {str(e)}"
                    )

        return IntegrationResult.error_result(
            f"Failed to extract valid metadata after {max_retries} attempts"
        )

    def _extract_json(self, text: str) -> str:
        """
        Extract JSON from text, handling markdown code blocks.

        Args:
            text: Text that may contain JSON.

        Returns:
            Extracted JSON string.
        """
        if "```json" in text and "```" in text.split("```json", 1)[1]:
            json_part = text.split("```json", 1)[1].split("```", 1)[0].strip()
            return json_part
        elif "```" in text and "```" in text.split("```", 1)[1]:
            json_part = text.split("```", 1)[1].split("```", 1)[0].strip()
            return json_part
        else:
            return text.strip()

    def _create_metadata_card(self, metadata: Metadata) -> str:
        """
        Create a metadata card for display.

        Args:
            metadata: The extracted metadata.

        Returns:
            A string representing the metadata card.
        """
        title = metadata.title
        domain = metadata.domain
        tone = metadata.tone
        rarity = metadata.rarity

        card = [
            "╔══════════════════════════════════════════╗",
            "║            🃏 METADATA CARD              ║",
            "╠══════════════════════════════════════════╣",
        ]
        card.append(f"║ Title: {title[:30]:30}║")
        card.append(f"║ Domain: {domain[:28]:28}║")
        card.append(f"║ Tone: {tone[:31]:31}║")
        card.append(f"║ Rarity: {rarity[:29]:29}║")

        if self._using_mock:
            card.append("╠══════════════════════════════════════════╣")
            card.append("║ ⚠️ USING MOCK LLM - DATA IS SIMULATED ⚠️  ║")

        card.append("╚══════════════════════════════════════════╝")
        return "\n".join(card)

    def _ensure_clean_path(self, path_or_result) -> str:
        """
        Extract clean path string from various input types.

        Args:
            path_or_result: Can be a string, Path, PathResult, or any other Result object

        Returns:
            A clean path string
        """
        if hasattr(path_or_result, "path") and path_or_result.path is not None:
            # Handle PathResult and similar objects
            return str(path_or_result.path)
        elif hasattr(path_or_result, "data") and path_or_result.data is not None:
            # Handle DataResult objects
            return str(path_or_result.data)
        else:
            # For strings and Path objects
            return str(path_or_result)
