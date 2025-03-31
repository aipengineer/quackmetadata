# src/quackmetadata/plugins/metadata.py
"""
QuackMetadata plugin for metadata extraction.

This module implements the metadata extraction plugin that integrates with QuackCore
to download files from Google Drive, extract metadata using LLMs, and upload
results back to Google Drive.
"""

import json
import logging
import os
import tempfile
import time
from pathlib import Path
from typing import Any, cast, Protocol


from pydantic import ValidationError
from quackcore.integrations.core.results import IntegrationResult
from quackcore.integrations.google.drive import GoogleDriveService
from quackcore.integrations.llms import ChatMessage, LLMOptions, RoleType, create_integration

from quackmetadata.protocols import QuackToolPluginProtocol
from quackmetadata.schemas.metadata import Metadata
from quackmetadata.utils.prompt_engine import render_prompt, get_template_path
from quackmetadata.utils.rarity import calculate_rarity

# Define the SupportsWrite protocol
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

    def __init__(self):
        """Initialize the metadata plugin."""
        self._logger = logging.getLogger(__name__)
        self._drive_service = None
        self._llm_service = None
        self._initialized = False
        self._temp_dir = tempfile.mkdtemp(prefix="quackmetadata_")
        self._output_dir = Path("./output")
        self._output_dir.mkdir(exist_ok=True, parents=True)

    @property
    def logger(self) -> logging.Logger:
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
            IntegrationResult indicating success or failure
        """
        if self._initialized:
            return IntegrationResult.success_result(
                message="MetadataPlugin already initialized"
            )

        try:
            # Initialize Google Drive integration
            self._drive_service = GoogleDriveService()
            drive_result = self._drive_service.initialize()
            if not drive_result.success:
                return IntegrationResult.error_result(
                    f"Failed to initialize Google Drive: {drive_result.error}"
                )

            # Initialize LLM integration
            self._llm_service = create_integration()
            llm_result = self._llm_service.initialize()
            if not llm_result.success:
                return IntegrationResult.error_result(
                    f"Failed to initialize LLM service: {llm_result.error}"
                )

            self._initialized = True
            return IntegrationResult.success_result(
                message="MetadataPlugin initialized successfully"
            )
        except Exception as e:
            self.logger.exception("Failed to initialize MetadataPlugin")
            return IntegrationResult.error_result(
                f"Failed to initialize MetadataPlugin: {str(e)}"
            )

    def is_available(self) -> bool:
        """
        Check if the plugin is available.

        Returns:
            True if the plugin is available, False otherwise
        """
        return self._initialized

    def process_file(
            self,
            file_path: str,
            output_path: str | None = None,
            options: dict[str, Any] | None = None
    ) -> IntegrationResult:
        """
        Process a file using the metadata plugin.

        Args:
            file_path: Path to the file to process (local path or Google Drive ID)
            output_path: Optional path for the output metadata file
            options: Optional processing options
                - prompt_template: Path to custom prompt template
                - retries: Number of retries for LLM calls (default: 3)
                - dry_run: Don't upload results to Google Drive (default: False)
                - verbose: Print detailed processing information (default: False)

        Returns:
            IntegrationResult containing the metadata extraction result
        """
        if not self._initialized:
            init_result = self.initialize()
            if not init_result.success:
                return init_result

        options = options or {}

        try:
            # Check if the file_path is a Google Drive ID
            is_drive_id = not os.path.exists(file_path) and "/" not in file_path

            if is_drive_id:
                file_result = self._process_drive_file(file_path, output_path, options)
            else:
                file_result = self._process_local_file(file_path, output_path, options)

            return file_result

        except Exception as e:
            self.logger.exception(f"Failed to process file: {e}")
            return IntegrationResult.error_result(
                f"Failed to process file: {str(e)}"
            )

    def _process_drive_file(
            self,
            file_id: str,
            output_path: str | None,
            options: dict[str, Any]
    ) -> IntegrationResult:
        """
        Process a file from Google Drive.

        Args:
            file_id: Google Drive file ID
            output_path: Optional path for the output metadata file
            options: Processing options

        Returns:
            IntegrationResult containing the metadata extraction result
        """
        # Download the file from Google Drive
        self.logger.info(f"Downloading file from Google Drive with ID: {file_id}")

        download_result = self._drive_service.download_file(
            remote_id=file_id,
            local_path=self._temp_dir
        )

        if not download_result.success:
            return IntegrationResult.error_result(
                f"Failed to download file from Google Drive: {download_result.error}"
            )

        local_path = download_result.content
        self.logger.info(f"Downloaded file to: {local_path}")

        # Get file metadata from Google Drive
        file_info_result = self._drive_service.get_file_info(file_id)
        if not file_info_result.success:
            return IntegrationResult.error_result(
                f"Failed to get file info from Google Drive: {file_info_result.error}"
            )

        file_info = file_info_result.content
        file_name = file_info.get("name", "unknown")

        # Process the local file
        result = self._process_local_file(local_path, output_path, options)

        if result.success and not options.get("dry_run", False):
            # Upload the result back to Google Drive
            metadata_path = result.content.get("metadata_path")
            if metadata_path:
                # Get the parent folder ID
                parent_id = file_info.get("parents", [None])[0]

                upload_result = self._drive_service.upload_file(
                    file_path=metadata_path,
                    parent_path=parent_id
                )

                if upload_result.success:
                    result.content["drive_file_id"] = upload_result.content
                    self.logger.info(
                        f"Uploaded metadata file to Google Drive with ID: {upload_result.content}")
                else:
                    self.logger.error(
                        f"Failed to upload metadata file to Google Drive: {upload_result.error}")
                    # Don't fail the overall operation, just log the error

        # Add original file name to the result for display purposes
        if result.success:
            result.content["original_file_name"] = file_name

        return result

    def _process_local_file(
            self,
            file_path: str,
            output_path: str | None,
            options: dict[str, Any]
    ) -> IntegrationResult:
        """
        Process a local file.

        Args:
            file_path: Path to the local file
            output_path: Optional path for the output metadata file
            options: Processing options

        Returns:
            IntegrationResult containing the metadata extraction result
        """
        # Validate file exists and is readable
        path = Path(file_path)
        if not path.exists():
            return IntegrationResult.error_result(f"File not found: {file_path}")

        if not path.is_file():
            return IntegrationResult.error_result(f"Not a file: {file_path}")

        try:
            # Read the file content
            self.logger.info(f"Reading file: {file_path}")
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()

            # Extract metadata using LLM
            metadata_result = self._extract_metadata(
                content=content,
                options=options
            )

            if not metadata_result.success:
                return metadata_result

            metadata = metadata_result.content

            # Determine output path for metadata file
            if output_path:
                metadata_path = Path(output_path)
            else:
                # Create a metadata file with the same name as the input file
                stem = path.stem
                metadata_path = self._output_dir / f"{stem}.metadata.json"

            # Write metadata to file - fixed to correctly type the file object
            self.logger.info(f"Writing metadata to: {metadata_path}")
            with open(metadata_path, "w", encoding="utf-8") as f:
                # Cast the file object to SupportsWrite[str] explicitly
                json_file = cast(SupportsWrite, f)
                json.dump(metadata.model_dump(), json_file, indent=2)

            # Create a card representation
            card = self._create_metadata_card(metadata)

            return IntegrationResult.success_result(
                content={
                    "metadata": metadata.model_dump(),
                    "metadata_path": str(metadata_path),
                    "card": card
                },
                message=f"Successfully extracted metadata from {path.name}"
            )

        except Exception as e:
            self.logger.exception(f"Failed to process local file: {e}")
            return IntegrationResult.error_result(
                f"Failed to process file: {str(e)}"
            )

    def _extract_metadata(
            self,
            content: str,
            options: dict[str, Any]
    ) -> IntegrationResult:
        """
        Extract metadata from content using LLM.

        Args:
            content: Text content to extract metadata from
            options: Processing options

        Returns:
            IntegrationResult containing the extracted metadata
        """
        # Get options
        max_retries = options.get("retries", 3)
        prompt_template = options.get("prompt_template")
        verbose = options.get("verbose", False)

        # Get prompt template path
        if prompt_template:
            template_path = prompt_template
        else:
            template_path = get_template_path("generic", "metadata")

        # Render the prompt
        try:
            prompt = render_prompt(
                template_path=template_path,
                context={"content": content}
            )
        except Exception as e:
            return IntegrationResult.error_result(
                f"Failed to render prompt: {str(e)}"
            )

        if verbose:
            self.logger.info(f"Generated prompt:\n{prompt}")

        # Create LLM messages
        messages = [
            ChatMessage(role=RoleType.USER, content=prompt)
        ]

        # LLM options
        llm_options = LLMOptions(
            temperature=0.1,  # Low temperature for more consistent output
            max_tokens=2000  # Enough for detailed metadata
        )

        # Try multiple times to get a valid response
        for attempt in range(max_retries):
            try:
                self.logger.info(
                    f"Sending prompt to LLM (attempt {attempt + 1}/{max_retries})")

                # Call the LLM
                result = self._llm_service.chat(messages=messages, options=llm_options)

                if not result.success:
                    self.logger.error(f"LLM call failed: {result.error}")
                    if attempt < max_retries - 1:
                        time.sleep(1)  # Brief pause before retry
                        continue
                    return IntegrationResult.error_result(
                        f"Failed to get response from LLM: {result.error}"
                    )

                response = result.content

                if verbose:
                    self.logger.info(f"LLM response:\n{response}")

                # Try to parse the response as JSON
                try:
                    # Extract JSON from the response if it's wrapped in markdown code blocks
                    json_str = self._extract_json(response)
                    metadata_dict = json.loads(json_str)

                    # Validate against the schema
                    metadata = Metadata.model_validate(metadata_dict)

                    # Override rarity with our calculation if needed
                    calculated_rarity = calculate_rarity(metadata.summary)
                    if calculated_rarity != metadata.rarity:
                        self.logger.info(
                            f"Overriding LLM rarity '{metadata.rarity}' with calculated rarity '{calculated_rarity}'"
                        )
                        metadata.rarity = calculated_rarity

                    return IntegrationResult.success_result(
                        content=metadata,
                        message="Successfully extracted metadata"
                    )

                except json.JSONDecodeError as e:
                    self.logger.error(f"Failed to parse JSON from LLM response: {e}")
                    if verbose:
                        self.logger.error(f"Invalid JSON: {response}")

                except ValidationError as e:

                    self.logger.error(f"Validation error in metadata: {e}")

                    if verbose:
                        self.logger.error(
                            f"Invalid metadata: {locals().get('metadata_dict', 'N/A')}")

                # If we get here, something went wrong with parsing/validation
                if attempt < max_retries - 1:
                    # Add a clarification message for the next attempt
                    messages.append(
                        ChatMessage(role=RoleType.ASSISTANT, content=response))
                    messages.append(ChatMessage(
                        role=RoleType.USER,
                        content="The response couldn't be properly parsed as JSON or didn't match the required schema. "
                                "Please provide a valid JSON response with all required fields using the exact structure "
                                "specified in the initial prompt. Return only the JSON object with no markdown or additional text."
                    ))
                    time.sleep(1)  # Brief pause before retry

            except Exception as e:
                self.logger.exception(f"Error during metadata extraction: {e}")
                if attempt < max_retries - 1:
                    time.sleep(1)  # Brief pause before retry
                else:
                    return IntegrationResult.error_result(
                        f"Failed to extract metadata after {max_retries} attempts: {str(e)}"
                    )

        # If we get here, all attempts failed
        return IntegrationResult.error_result(
            f"Failed to extract valid metadata after {max_retries} attempts"
        )

    def _extract_json(self, text: str) -> str:
        """
        Extract JSON from text, handling markdown code blocks.

        Args:
            text: Text that may contain JSON

        Returns:
            Extracted JSON string
        """
        # Check if the response is wrapped in markdown code blocks
        if "```json" in text and "```" in text.split("```json", 1)[1]:
            # Extract the JSON part
            json_part = text.split("```json", 1)[1].split("```", 1)[0].strip()
            return json_part
        elif "```" in text and "```" in text.split("```", 1)[1]:
            # Extract from generic code block
            json_part = text.split("```", 1)[1].split("```", 1)[0].strip()
            return json_part
        else:
            # Assume the whole text is JSON
            return text.strip()

    def _create_metadata_card(self, metadata: Metadata) -> str:
        """
        Create a metadata card for display.

        Args:
            metadata: The extracted metadata

        Returns:
            A string representing the metadata card
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

        # Add fields with proper padding
        card.append(f"║ Title: {title[:30]}{' ' * (30 - min(30, len(title)))}║")
        card.append(f"║ Domain: {domain[:28]}{' ' * (28 - min(28, len(domain)))}║")
        card.append(f"║ Tone: {tone[:31]}{' ' * (31 - min(31, len(tone)))}║")
        card.append(f"║ Rarity: {rarity[:29]}{' ' * (29 - min(29, len(rarity)))}║")

        card.append("╚══════════════════════════════════════════╝")

        return "\n".join(card)