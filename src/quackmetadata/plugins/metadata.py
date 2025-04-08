"""
QuackMetadata plugin for metadata extraction.

This module implements the metadata extraction plugin that integrates with QuackCore
to download files from Google Drive, extract metadata using LLMs, and upload
results back to Google Drive.
"""

import time
import tempfile
from logging import Logger
from typing import Any, Protocol

from quackcore.errors import QuackIntegrationError
from quackcore.integrations.core.results import IntegrationResult
from quackcore.integrations.google.drive import GoogleDriveService
from quackcore.integrations.llms import ChatMessage, LLMOptions, RoleType, create_integration, MockLLMClient

from quackcore.logging import get_logger
from quackmetadata.protocols import QuackToolPluginProtocol
from quackmetadata.schemas.metadata import Metadata
from quackmetadata.utils.prompt_engine import render_prompt, get_template_path
from quackmetadata.utils.rarity import calculate_rarity

# Define the SupportsWrite protocol.
class SupportsWrite(Protocol):
    def write(self, s: str) -> int: ...

# Import QuackCore FS service and helper functions.
from quackcore.fs import service as fs, join_path, split_path

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

    def __init__(self):
        """Initialize the metadata plugin."""
        self._logger = get_logger(__name__)
        self._drive_service = None
        self._llm_service = None
        self._initialized = False
        # Create a temporary directory using FS.
        temp_dir_result = fs.create_temp_directory(prefix="quackmetadata_")
        self._temp_dir = temp_dir_result.path if temp_dir_result.success else tempfile.mkdtemp(prefix="quackmetadata_")
        # Create the output directory using FS.
        output_result = fs.create_directory("./output", exist_ok=True)
        self._output_dir = output_result.path if output_result.success else "./output"
        self._using_mock = False

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

    def initialize(self) -> IntegrationResult:
        """
        Initialize the plugin and its dependencies.

        Returns:
            IntegrationResult indicating success or failure.
        """
        if self._initialized:
            return IntegrationResult.success_result(message="MetadataPlugin already initialized")

        try:
            self._initialize_environment()

            self._drive_service = GoogleDriveService()
            drive_result = self._drive_service.initialize()
            if not drive_result.success:
                return IntegrationResult.error_result(f"Failed to initialize Google Drive: {drive_result.error}")

            try:
                self._llm_service = create_integration()
                llm_result = self._llm_service.initialize()
                if not llm_result.success:
                    error_message = f"Failed to initialize LLM service: {llm_result.error}"
                    if "API key not provided" in str(llm_result.error):
                        error_message += (
                            "\nPlease ensure your API key is properly configured in quack_config.yaml or as an environment variable."
                        )
                    raise QuackIntegrationError(error_message)
            except QuackIntegrationError as e:
                if "API key not provided" in str(e):
                    self.logger.error(
                        "LLM API key missing. Please configure it in quack_config.yaml under integrations.llm.openai.api_key or set the OPENAI_API_KEY environment variable."
                    )
                self.logger.warning("Falling back to MockLLMClient for development/testing")
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
                return IntegrationResult.success_result(message="MetadataPlugin initialized successfully")
        except Exception as e:
            self.logger.exception("Failed to initialize MetadataPlugin")
            return IntegrationResult.error_result(f"Failed to initialize MetadataPlugin: {str(e)}")

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

    def process_file(self, file_path: str, output_path: str | None = None, options: dict[str, Any] | None = None) -> IntegrationResult:
        """
        Process a file using the metadata plugin.

        Args:
            file_path: Path to the file to process (local path or Google Drive ID).
            output_path: Optional path for the output metadata file.
            options: Optional processing options:
                - prompt_template: Path to custom prompt template.
                - retries: Number of retries for LLM calls (default: 3).
                - dry_run: Don't upload results to Google Drive (default: False).
                - verbose: Print detailed processing information (default: False).

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
            # Replace os.path.exists with FS's get_file_info.
            local_info = fs.get_file_info(file_path)
            if local_info.success and local_info.exists:
                is_drive_id = False
            else:
                is_drive_id = "/" not in file_path

            if is_drive_id:
                file_result = self._process_drive_file(file_path, output_path, options)
            else:
                file_result = self._process_local_file(file_path, output_path, options)

            return file_result
        except Exception as e:
            self.logger.exception(f"Failed to process file: {e}")
            return IntegrationResult.error_result(f"Failed to process file: {str(e)}")

    def _process_drive_file(self, file_id: str, output_path: str | None, options: dict[str, Any]) -> IntegrationResult:
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

        download_result = self._drive_service.download_file(remote_id=file_id, local_path=self._temp_dir)
        if not download_result.success:
            return IntegrationResult.error_result(f"Failed to download file from Google Drive: {download_result.error}")

        local_path = download_result.content
        self.logger.info(f"Downloaded file to: {local_path}")

        file_info_result = self._drive_service.get_file_info(remote_id=file_id)
        if not file_info_result.success:
            return IntegrationResult.error_result(f"Failed to get file info from Google Drive: {file_info_result.error}")

        file_info = file_info_result.content
        file_name = file_info.get("name", "unknown")

        result = self._process_local_file(local_path, output_path, options)

        if result.success and not options.get("dry_run", False):
            metadata_path = result.content.get("metadata_path")
            if metadata_path:
                parent_id = file_info.get("parents", [None])[0]
                upload_result = self._drive_service.upload_file(file_path=metadata_path, parent_folder_id=parent_id)
                if upload_result.success:
                    result.content["drive_file_id"] = upload_result.content
                    self.logger.info(f"Uploaded metadata file to Google Drive with ID: {upload_result.content}")
                else:
                    self.logger.error(f"Failed to upload metadata file to Google Drive: {upload_result.error}")

        if result.success:
            result.content["original_file_name"] = file_name

        return result

    def _process_local_file(self, file_path: str, output_path: str | None, options: dict[str, Any]) -> IntegrationResult:
        """
        Process a local file.

        Args:
            file_path: Path to the local file.
            output_path: Optional path for the output metadata file.
            options: Processing options.

        Returns:
            IntegrationResult containing the metadata extraction result.
        """
        file_info = fs.get_file_info(file_path)
        if not file_info.success or not file_info.exists:
            return IntegrationResult.error_result(f"File not found: {file_path}")
        if not file_info.is_file:
            return IntegrationResult.error_result(f"Not a file: {file_path}")

        try:
            self.logger.info(f"Reading file: {file_path}")
            read_result = fs.read_text(file_path, encoding="utf-8")
            if not read_result.success:
                return IntegrationResult.error_result(f"Failed to read file: {read_result.error}")
            content = read_result.content

            metadata_result = self._extract_metadata(content=content, options=options)
            if not metadata_result.success:
                return metadata_result
            metadata = metadata_result.content

            if output_path:
                metadata_path = output_path
            else:
                parts = split_path(file_path)
                file_name = parts[-1]
                stem = file_name.rsplit('.', 1)[0]
                metadata_path = join_path(self._output_dir, f"{stem}.metadata.json")

            self.logger.info(f"Writing metadata to: {metadata_path}")
            # Use fs.write_json to write the metadata atomically.
            write_result = fs.write_json(metadata_path, metadata.model_dump(), atomic=True, indent=2)
            if not write_result.success:
                return IntegrationResult.error_result(f"Failed to write metadata file: {write_result.error}")

            card = self._create_metadata_card(metadata)
            file_name = split_path(file_path)[-1]
            message = f"Successfully extracted metadata from {file_name}"
            if self._using_mock:
                message += " (using mock data - not actual language model analysis)"

            return IntegrationResult.success_result(
                content={
                    "metadata": metadata.model_dump(),
                    "metadata_path": metadata_path,
                    "card": card,
                    "using_mock": self._using_mock
                },
                message=message
            )

        except Exception as e:
            self.logger.exception(f"Failed to process local file: {e}")
            return IntegrationResult.error_result(f"Failed to process file: {str(e)}")

    def _extract_metadata(self, content: str, options: dict[str, Any]) -> IntegrationResult:
        """
        Extract metadata from content using LLM.

        Args:
            content: Text content to extract metadata from.
            options: Processing options.

        Returns:
            IntegrationResult containing the extracted metadata.
        """
        max_retries = options.get("retries", 3)
        prompt_template = options.get("prompt_template")
        verbose = options.get("verbose", False)

        template_path = prompt_template if prompt_template else get_template_path("generic", "metadata")

        try:
            prompt = render_prompt(template_path=template_path, context={"content": content})
        except Exception as e:
            return IntegrationResult.error_result(f"Failed to render prompt: {str(e)}")

        if verbose:
            self.logger.info(f"Generated prompt:\n{prompt}")

        messages = [ChatMessage(role=RoleType.USER, content=prompt)]
        llm_options = LLMOptions(temperature=0.1, max_tokens=2000)

        for attempt in range(max_retries):
            try:
                self.logger.info(f"Sending prompt to LLM (attempt {attempt + 1}/{max_retries})")
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
                    return IntegrationResult.error_result(f"Failed to get response from LLM: {result.error}")

                response = result.content
                if verbose:
                    self.logger.info(f"LLM response:\n{response}")

                try:
                    # Use fs.parse_json to parse the response into a dictionary.
                    json_str = self._extract_json(response)
                    metadata_dict = fs.parse_json(json_str)
                    metadata = Metadata.model_validate(metadata_dict)
                    calculated_rarity = calculate_rarity(metadata.summary)
                    if calculated_rarity != metadata.rarity:
                        self.logger.info(f"Overriding LLM rarity '{metadata.rarity}' with calculated rarity '{calculated_rarity}'")
                        metadata.rarity = calculated_rarity

                    return IntegrationResult.success_result(
                        content=metadata,
                        message="Successfully extracted metadata"
                    )
                except Exception as e:
                    self.logger.error(f"Error parsing or validating metadata: {e}")
                    if verbose:
                        self.logger.error(f"Invalid response: {response}")

                if attempt < max_retries - 1:
                    messages.append(ChatMessage(role=RoleType.ASSISTANT, content=response))
                    messages.append(ChatMessage(
                        role=RoleType.USER,
                        content="The response couldn't be properly parsed as JSON or didn't match the required schema. "
                                "Please provide a valid JSON response with all required fields using the exact structure "
                                "specified in the initial prompt. Return only the JSON object with no markdown or additional text."
                    ))
                    time.sleep(1)
            except Exception as e:
                self.logger.exception(f"Error during metadata extraction: {e}")
                if attempt < max_retries - 1:
                    time.sleep(1)
                else:
                    return IntegrationResult.error_result(f"Failed to extract metadata after {max_retries} attempts: {str(e)}")

        return IntegrationResult.error_result(f"Failed to extract valid metadata after {max_retries} attempts")

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
            "╠══════════════════════════════════════════╣"
        ]
        card.append(f"║ Title: {title[:30]}{' ' * (30 - min(30, len(title)))}║")
        card.append(f"║ Domain: {domain[:28]}{' ' * (28 - min(28, len(domain)))}║")
        card.append(f"║ Tone: {tone[:31]}{' ' * (31 - min(31, len(tone)))}║")
        card.append(f"║ Rarity: {rarity[:29]}{' ' * (29 - min(29, len(rarity)))}║")

        if self._using_mock:
            card.append("╠══════════════════════════════════════════╣")
            card.append("║ ⚠️ USING MOCK LLM - DATA IS SIMULATED ⚠️  ║")

        card.append("╚══════════════════════════════════════════╝")
        return "\n".join(card)
