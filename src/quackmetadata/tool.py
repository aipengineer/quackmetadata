# src/quackmetadata/tool.py
"""
QuackMetadata - Core business logic for metadata extraction.

This module contains the essential functionality for extracting structured metadata
from text documents using language models. It follows the QuackTool principle of
focusing only on the core business logic, with minimal dependencies on QuackCore.
"""

import json
import time
from typing import Any

# Import QuackCore essentials
from quackcore.integrations.core.results import IntegrationResult
from quackcore.integrations.llms import (
    ChatMessage,
    LLMOptions,
    RoleType,
    create_integration,
)
from quackcore.logging import get_logger

# Import only the essential schemas
from quackmetadata.schemas import Metadata

logger = get_logger(__name__)


def extract_metadata(content: str, options: dict[str, Any] = None) -> IntegrationResult:
    """
    Extract metadata from document content using an LLM.

    Args:
        content: Text content to extract metadata from
        options: Processing options (retries, prompt_template, verbose)

    Returns:
        IntegrationResult containing extracted metadata or error
    """
    options = options or {}
    max_retries = options.get("retries", 3)
    verbose = options.get("verbose", False)

    # Get prompt template - delegated to helper function to keep this core logic clean
    prompt_template = options.get("prompt_template")

    try:
        # Generate prompt from template
        from quackmetadata.utils.prompt_engine import get_template_path, render_prompt

        if prompt_template:
            template_path = prompt_template
        else:
            template_path = get_template_path("generic", "metadata")

        prompt = render_prompt(template_path=template_path,
                               context={"content": content})

        if verbose:
            logger.info(f"Generated prompt:\n{prompt}")

        # Initialize LLM service
        llm_service = create_integration()
        llm_init_result = llm_service.initialize()
        if not llm_init_result.success:
            return IntegrationResult.error_result(
                f"Failed to initialize LLM: {llm_init_result.error}"
            )

        # Prepare messages for LLM
        messages = [ChatMessage(role=RoleType.USER, content=prompt)]
        llm_options = LLMOptions(temperature=0.1, max_tokens=2000)

        # Try multiple times to get valid result from LLM
        for attempt in range(max_retries):
            try:
                logger.info(
                    f"Sending prompt to LLM (attempt {attempt + 1}/{max_retries})")
                result = llm_service.chat(messages=messages, options=llm_options)

                if not result.success:
                    logger.error(f"LLM call failed: {result.error}")
                    if "API key" in str(result.error):
                        return IntegrationResult.error_result(
                            f"LLM API key error: {result.error}. Please configure your API key."
                        )
                    if attempt < max_retries - 1:
                        time.sleep(1)
                        continue
                    return IntegrationResult.error_result(
                        f"Failed to get response from LLM: {result.error}"
                    )

                response = result.content
                if verbose:
                    logger.info(f"LLM response:\n{response}")

                # Extract and parse JSON
                json_str = extract_json(response)
                try:
                    metadata_dict = json.loads(json_str)
                    metadata = Metadata.model_validate(metadata_dict)

                    # Calculate rarity score based on content
                    from quackmetadata.utils.rarity import calculate_rarity
                    calculated_rarity = calculate_rarity(metadata.summary)
                    if calculated_rarity != metadata.rarity:
                        logger.info(
                            f"Overriding LLM rarity '{metadata.rarity}' with calculated rarity '{calculated_rarity}'"
                        )
                        metadata.rarity = calculated_rarity

                    return IntegrationResult.success_result(
                        content=metadata,
                        message="Successfully extracted metadata"
                    )
                except json.JSONDecodeError as json_err:
                    raise ValueError(f"Invalid JSON format: {json_err}")

            except Exception as e:
                logger.error(f"Error parsing or validating metadata: {e}")
                if verbose:
                    logger.error(f"Invalid response: {response}")

                # Add feedback for retry if we have attempts left
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

        return IntegrationResult.error_result(
            f"Failed to extract valid metadata after {max_retries} attempts"
        )

    except Exception as e:
        logger.exception(f"Error during metadata extraction: {e}")
        return IntegrationResult.error_result(f"Failed to extract metadata: {str(e)}")


def extract_json(text: str) -> str:
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


def create_metadata_card(metadata: Metadata, using_mock: bool = False) -> str:
    """
    Create a formatted metadata card for display.

    Args:
        metadata: The extracted metadata
        using_mock: Whether mock data was used

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
        "╠══════════════════════════════════════════╣",
    ]
    card.append(f"║ Title: {title[:30]:30}║")
    card.append(f"║ Domain: {domain[:28]:28}║")
    card.append(f"║ Tone: {tone[:31]:31}║")
    card.append(f"║ Rarity: {rarity[:29]:29}║")

    if using_mock:
        card.append("╠══════════════════════════════════════════╣")
        card.append("║ ⚠️ USING MOCK LLM - DATA IS SIMULATED ⚠️  ║")

    card.append("╚══════════════════════════════════════════╝")
    return "\n".join(card)


def process_file(file_path: str, output_path: str | None = None,
                 options: dict[str, Any] | None = None) -> IntegrationResult:
    """
    Process a file to extract metadata.

    This is the main entry point function that handles both local files and Google Drive files.
    It delegates to specialized functions for each case.

    Args:
        file_path: Path to the file or Google Drive ID
        output_path: Path to save the output metadata
        options: Processing options

    Returns:
        IntegrationResult containing the extraction result
    """
    from quackcore.fs.service import get_service
    fs = get_service()

    logger.info(f"Processing file: {file_path}")
    options = options or {}

    # Try to detect if this is a Google Drive ID
    if _is_likely_drive_id(file_path):
        # Process as Google Drive file
        logger.info(f"Processing as Google Drive file ID: {file_path}")
        from quackmetadata.integrations.drive_handler import process_drive_file
        return process_drive_file(file_path, output_path, options)

    # Process as local file
    logger.info(f"Processing as local file: {file_path}")

    # Ensure the file exists
    file_info = fs.get_file_info(file_path)
    if not file_info.success or not file_info.exists:
        return IntegrationResult.error_result(f"File not found: {file_path}")

    try:
        # Read the file content
        read_result = fs.read_text(file_path, encoding="utf-8")
        if not read_result.success:
            return IntegrationResult.error_result(
                f"Failed to read file: {read_result.error}")

        content = read_result.content

        # Extract metadata
        metadata_result = extract_metadata(content, options)
        if not metadata_result.success:
            return metadata_result

        metadata = metadata_result.content

        # Determine output path
        import os
        if output_path:
            metadata_path = output_path
        else:
            # Create a default output path
            from quackcore.paths import service as paths
            output_dir = paths.get_output_dir() or "./output"
            fs.create_directory(output_dir, exist_ok=True)

            basename = os.path.basename(file_path)
            stem = os.path.splitext(basename)[0]
            metadata_path = os.path.join(output_dir, f"{stem}.metadata.json")

        # Write metadata to file
        metadata_dict = metadata.model_dump()
        write_result = fs.write_json(metadata_path, metadata_dict, atomic=True,
                                     indent=2)
        if not write_result.success:
            return IntegrationResult.error_result(
                f"Failed to write metadata: {write_result.error}")

        # Create metadata card for display
        card = create_metadata_card(metadata, options.get("using_mock", False))

        # Return success result
        return IntegrationResult.success_result(
            content={
                "metadata": metadata_dict,
                "metadata_path": metadata_path,
                "card": card,
                "using_mock": options.get("using_mock", False),
            },
            message=f"Successfully extracted metadata from {os.path.basename(file_path)}"
        )

    except Exception as e:
        logger.exception(f"Failed to process file: {e}")
        return IntegrationResult.error_result(f"Failed to process file: {str(e)}")


def _is_likely_drive_id(file_path: str) -> bool:
    """
    Check if a string is likely to be a Google Drive file ID.

    Args:
        file_path: The string to check

    Returns:
        True if the string looks like a Drive ID, False otherwise
    """
    if not isinstance(file_path, str):
        return False

    # Drive IDs are typically 25-45 chars and don't contain path separators or dots
    return (len(file_path) >= 25 and len(file_path) <= 45 and
            "/" not in file_path and "\\" not in file_path and
            "." not in file_path)


def run(file_path: str, output_path: str | None = None,
        options: dict[str, Any] | None = None) -> dict[str, Any]:
    """
    Main entry point for the QuackMetadata tool.

    This function is called by ducktyper or other consumers.

    Args:
        file_path: Path to the file to process
        output_path: Optional path for the output metadata
        options: Optional processing options

    Returns:
        Dictionary containing the processing results
    """
    # Initialize logging
    logger.info("Starting QuackMetadata tool")

    # Process the file
    result = process_file(file_path, output_path, options)

    # Return the result content or error
    if result.success:
        return {
            "success": True,
            "metadata": result.content.get("metadata", {}),
            "metadata_path": result.content.get("metadata_path", ""),
            "card": result.content.get("card", ""),
            "message": result.message
        }
    else:
        return {
            "success": False,
            "error": str(result.error),
            "message": result.message
        }


if __name__ == "__main__":
    # This section allows running the tool directly for testing
    import sys

    if len(sys.argv) < 2:
        print("Usage: python tool.py <file_path> [output_path]")
        sys.exit(1)

    file_to_process = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None

    result = run(file_to_process, output_file, {"verbose": True})

    if result["success"]:
        print(result["card"])
        print(f"\nMetadata saved to: {result['metadata_path']}")
    else:
        print(f"Error: {result['error']}")
