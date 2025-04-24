# src/quackmetadata/plugin.py
"""
QuackMetadata plugin implementation.

This module provides the QuackMetadata plugin that implements the QuackToolPluginProtocol.
"""

from typing import Any, cast

from quackcore.fs.service import get_service
from quackcore.integrations.core.results import IntegrationResult
from quackcore.integrations.llms import (
    ChatMessage,
    LLMOptions,
    MockLLMClient,
    RoleType,
    create_integration,
)
from quackcore.logging import get_logger

from quackmetadata.protocols import QuackToolPluginProtocol

# Import from our quackcore_candidate modules
from quackmetadata.quackcore_candidate.plugins.tool_plugin import BaseQuackToolPlugin
from quackmetadata.schemas import Metadata
from quackmetadata.utils.prompt_engine import get_template_path, render_prompt
from quackmetadata.utils.rarity import calculate_rarity

fs = get_service()
logger = get_logger(__name__)

# Global instance reference for singleton pattern
_plugin_instance = None


class MetadataPlugin(BaseQuackToolPlugin):
    """
    Plugin for extracting metadata from text documents using LLMs.

    This plugin can:
      1. Download a text file from Google Drive
      2. Extract structured metadata using an LLM
      3. Validate the output against a schema
      4. Upload the results back to Google Drive
    """

    # Define plugin metadata
    tool_name = "metadata"
    tool_version = "0.1.0"
    tool_description = (
        "QuackMetadata plugin for metadata extraction. This plugin downloads a file from Google Drive, "
        "extracts structured metadata using language models, validates the output against a schema, "
        "and uploads the results back to Google Drive."
    )
    tool_author = "AI Product Engineer Team"
    tool_capabilities = [
        "download file",
        "LLM-based metadata extraction",
        "metadata validation",
        "upload file",
    ]

    def __init__(self) -> None:
        """Initialize the metadata plugin."""
        super().__init__()
        self._llm_service = None
        self._using_mock = False

    def _initialize_plugin(self) -> IntegrationResult:
        """
        Initialize plugin-specific functionality.

        Returns:
            IntegrationResult indicating success or failure.
        """
        try:
            # Initialize LLM service
            try:
                self._llm_service = create_integration()
                llm_result = self._llm_service.initialize()
                if not llm_result.success:
                    error_message = f"Failed to initialize LLM service: {llm_result.error}"
                    if "API key not provided" in str(llm_result.error):
                        error_message += "\nPlease ensure your API key is properly configured in quack_config.yaml or as an environment variable."
                    raise Exception(error_message)
            except Exception as e:
                if "API key not provided" in str(e):
                    self.logger.error(
                        "LLM API key missing. Please configure it in quack_config.yaml under integrations.llm.openai.api_key or set the OPENAI_API_KEY environment variable."
                    )
                self.logger.warning(
                    "Falling back to MockLLMClient for development/testing")
                self._llm_service = MockLLMClient()
                self._using_mock = True

            return IntegrationResult.success_result(
                message=(
                    "MetadataPlugin initialized with MockLLMClient. "
                    "Note: Results will be simulated, not real metadata extraction."
                ) if self._using_mock else "MetadataPlugin initialized successfully"
            )
        except Exception as e:
            self.logger.exception("Failed to initialize MetadataPlugin")
            return IntegrationResult.error_result(
                f"Failed to initialize MetadataPlugin: {str(e)}")

    def process_content(self, content: str, options: dict[str, Any]) -> tuple[
        bool, Any, str]:
        """
        Process content with the metadata plugin.

        Args:
            content: The content to process
            options: Processing options

        Returns:
            Tuple of (success, result, error_message)
        """
        try:
            # Extract metadata
            metadata_result = self._extract_metadata(content, options)
            if not metadata_result.success:
                return False, None, str(metadata_result.error)

            metadata = metadata_result.content

            # Create metadata card
            card = self._create_metadata_card(metadata)

            # Return success with metadata and card
            result = {
                "metadata": metadata.model_dump(),
                "card": card,
                "using_mock": self._using_mock,
            }

            return True, result, ""
        except Exception as e:
            self.logger.exception(f"Error processing content: {e}")
            return False, None, str(e)

    def _extract_metadata(self, content: str,
                          options: dict[str, Any]) -> IntegrationResult:
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

        # Get template path
        if prompt_template:
            from quackcore.paths.api.public.path_utils import (
                ensure_clean_path,
            )
            template_path = ensure_clean_path(prompt_template)
        else:
            template_path = get_template_path("generic", "metadata")

        try:
            # Render prompt
            prompt = render_prompt(template_path=template_path,
                                   context={"content": content})
            if verbose:
                self.logger.info(f"Generated prompt:\n{prompt}")

            # Prepare messages for LLM
            messages = [ChatMessage(role=RoleType.USER, content=prompt)]
            llm_options = LLMOptions(temperature=0.1, max_tokens=2000)

            # Try to get a valid response from the LLM
            for attempt in range(max_retries):
                try:
                    self.logger.info(
                        f"Sending prompt to LLM (attempt {attempt + 1}/{max_retries})")
                    result = self._llm_service.chat(messages=messages,
                                                    options=llm_options)
                    if not result.success:
                        self.logger.error(f"LLM call failed: {result.error}")
                        if "API key" in str(result.error):
                            return IntegrationResult.error_result(
                                f"LLM API key error: {result.error}. Please configure your API key in quack_config.yaml."
                            )
                        if attempt < max_retries - 1:
                            import time
                            time.sleep(1)
                            continue
                        return IntegrationResult.error_result(
                            f"Failed to get response from LLM: {result.error}")

                    response = result.content
                    if verbose:
                        self.logger.info(f"LLM response:\n{response}")

                    # Extract and parse JSON
                    json_str = self._extract_json(response)
                    import json
                    try:
                        metadata_dict = json.loads(json_str)
                        metadata = Metadata.model_validate(metadata_dict)

                        # Calculate rarity
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

                # Add feedback for retry
                if attempt < max_retries - 1:
                    messages.append(
                        ChatMessage(role=RoleType.ASSISTANT, content=response))
                    messages.append(
                        ChatMessage(
                            role=RoleType.USER,
                            content="The response couldn't be properly parsed as JSON or didn't match the required schema. "
                                    "Please provide a valid JSON response with all required fields using the exact structure specified in the initial prompt. Return only the JSON object with no markdown or additional text.",
                        )
                    )
                    import time
                    time.sleep(1)

            return IntegrationResult.error_result(
                f"Failed to extract valid metadata after {max_retries} attempts")

        except Exception as e:
            self.logger.exception(f"Error during metadata extraction: {e}")
            return IntegrationResult.error_result(
                f"Failed to extract metadata: {str(e)}")

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

    def _get_output_extension(self) -> str:
        """
        Get the extension for output files.

        Returns:
            Extension string including the dot
        """
        return ".metadata.json"


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
