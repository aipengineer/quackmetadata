# src/quackmetadata/quackcore_candidate/workflow/file_processor.py
"""
Standard file processing workflow for QuackCore tools.

This module provides a standardized workflow for processing files that
handles both local files and files from Google Drive, reducing boilerplate
in tool implementations.
"""

import os
from typing import Any, Protocol, TypeVar

from quackcore.fs.service import get_service
from quackcore.integrations.core.results import IntegrationResult
from quackcore.integrations.google.drive import GoogleDriveService
from quackcore.logging import get_logger

T = TypeVar('T')  # Return type for processor functions

# Get filesystem service and logger
fs = get_service()
logger = get_logger(__name__)


class FileProcessor(Protocol):
    """
    Protocol for file content processor functions.

    This protocol defines the expected signature for functions that process
    file content and return a tuple with success status, result, and error message.
    """

    def __call__(self, content: str, options: dict[str, Any]) -> tuple[bool, T, str]:
        """
        Process file content and return results.

        Args:
            content: File content to process
            options: Processing options

        Returns:
            Tuple containing:
              - success: Boolean indicating success or failure
              - result: Processing result (if successful)
              - error_message: Error message (if failed)
        """
        ...


def is_likely_drive_id(path: str) -> bool:
    """
    Check if a string is likely to be a Google Drive file ID.

    Args:
        path: The string to check

    Returns:
        True if the string looks like a Drive ID, False otherwise
    """
    if not isinstance(path, str):
        return False

    # Drive IDs are typically 25-45 chars and don't contain path separators or dots
    return (len(path) >= 25 and len(path) <= 45 and
            "/" not in path and "\\" not in path and
            "." not in path)


def ensure_clean_path(path_or_result: Any) -> str:
    """
    Extract a clean path string from various input types.

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
    elif hasattr(path_or_result, "content") and path_or_result.content is not None:
        # Handle ContentResult objects
        return str(path_or_result.content)
    else:
        # For strings and Path objects
        return str(path_or_result)


def extract_path_from_path_result_string(path_string: str) -> str:
    """
    Extract a path from a string representation of a PathResult.

    Args:
        path_string: A string that may be a string representation of a PathResult

    Returns:
        The extracted path if found, or the original string
    """
    import re
    if isinstance(path_string, str) and path_string.startswith("success="):
        # Try to extract the path using regex
        match = re.search(r"path=PosixPath\('([^']+)'\)", path_string)
        if match:
            return match.group(1)
    return path_string


def process_file_workflow(
        file_path: str,
        processor_func: FileProcessor,
        output_path: str | None = None,
        options: dict[str, Any] | None = None,
        drive_service: GoogleDriveService | None = None,
        temp_dir: str | None = None,
        output_dir: str | None = None,
        output_extension: str = ".json"
) -> IntegrationResult:
    """
    Process a file with standard workflow handling.

    This function handles both local files and Google Drive files, downloading
    if needed and optionally uploading results back to Google Drive.

    Args:
        file_path: Path to the file or Google Drive ID
        processor_func: Function to process the file content
        output_path: Optional path to save the output
        options: Optional processing options
        drive_service: Optional Google Drive service to use
        temp_dir: Optional temporary directory for downloads
        output_dir: Optional directory for output files
        output_extension: Extension for output files

    Returns:
        IntegrationResult containing the processing result
    """
    options = options or {}

    # Extract the raw input string
    raw_input = str(file_path)
    logger.debug(f"Raw input: {raw_input}")

    # Check if it looks like a Drive ID first
    is_drive_id_val = is_likely_drive_id(raw_input)

    # Process output path
    output_path_str = ensure_clean_path(
        output_path) if output_path is not None else None

    # If it looks like a Drive ID, process as Google Drive file
    if is_drive_id_val:
        logger.info(f"Detected Google Drive file ID: {raw_input}")
        return _process_drive_file(
            file_id=raw_input,
            processor_func=processor_func,
            output_path=output_path_str,
            options=options,
            drive_service=drive_service,
            temp_dir=temp_dir,
            output_extension=output_extension
        )

    # Process as local file, with fallback to Drive ID if not found
    try:
        # Extract the path from various input types
        file_path_str = extract_path_from_path_result_string(raw_input)

        # Check if file exists
        file_info = fs.get_file_info(file_path_str)

        # If file not found, check if it might be a Drive ID
        if not file_info.success or not file_info.exists:
            secondary_drive_check = (
                    "/" not in file_path_str and
                    "\\" not in file_path_str and
                    len(file_path_str) >= 25 and
                    len(file_path_str) <= 45
            )

            if secondary_drive_check and drive_service:
                potential_id = os.path.basename(file_path_str)

                if is_likely_drive_id(potential_id):
                    logger.info(
                        f"File not found locally, extracted Drive ID: {potential_id}")
                    return _process_drive_file(
                        file_id=potential_id,
                        processor_func=processor_func,
                        output_path=output_path_str,
                        options=options,
                        drive_service=drive_service,
                        temp_dir=temp_dir,
                        output_extension=output_extension
                    )
                else:
                    logger.info(
                        f"File not found locally, trying as Drive ID: {file_path_str}")
                    return _process_drive_file(
                        file_id=file_path_str,
                        processor_func=processor_func,
                        output_path=output_path_str,
                        options=options,
                        drive_service=drive_service,
                        temp_dir=temp_dir,
                        output_extension=output_extension
                    )

        # Process as local file
        logger.info(f"Processing as local file: {file_path_str}")
        return _process_local_file(
            file_path=file_path_str,
            processor_func=processor_func,
            output_path=output_path_str,
            options=options,
            output_dir=output_dir,
            output_extension=output_extension
        )

    except Exception as e:
        logger.exception(f"Failed to process file: {e}")
        return IntegrationResult.error_result(f"Failed to process file: {str(e)}")


def _process_drive_file(
        file_id: str,
        processor_func: FileProcessor,
        output_path: str | None,
        options: dict[str, Any],
        drive_service: GoogleDriveService | None,
        temp_dir: str | None,
        output_extension: str = ".json"
) -> IntegrationResult:
    """
    Process a file from Google Drive.

    Args:
        file_id: Google Drive file ID
        processor_func: Function to process the file content
        output_path: Optional path for output file
        options: Processing options
        drive_service: Google Drive service
        temp_dir: Temporary directory for downloads
        output_extension: Extension for output files

    Returns:
        IntegrationResult containing the processing result
    """
    # Check if Drive service is available
    if not drive_service:
        return IntegrationResult.error_result(
            "Google Drive integration is not available. Please configure it in quack_config.yaml."
        )

    import tempfile
    logger.info(f"Downloading file from Google Drive with ID: {file_id}")

    # Create a temporary directory if none is provided
    if temp_dir is None:
        temp_dir = tempfile.mkdtemp(prefix="quacktool_")
        should_cleanup = True
    else:
        should_cleanup = False

    try:
        # Download the file
        download_result = drive_service.download_file(
            remote_id=file_id,
            local_path=temp_dir
        )
        if not download_result.success:
            return IntegrationResult.error_result(
                f"Failed to download file from Google Drive: {download_result.error}"
            )

        # Get the local path
        local_path = ensure_clean_path(download_result.content)
        logger.info(f"Downloaded file to: {local_path}")

        # Get file info from Drive
        file_info_result = drive_service.get_file_info(remote_id=file_id)
        if not file_info_result.success:
            return IntegrationResult.error_result(
                f"Failed to get file info from Google Drive: {file_info_result.error}"
            )

        file_info = file_info_result.content
        file_name = file_info.get("name", "unknown")

        # Process the downloaded file
        result = _process_local_file(
            file_path=local_path,
            processor_func=processor_func,
            output_path=output_path,
            options=options,
            output_extension=output_extension
        )

        # Upload result if successful and not in dry run mode
        if result.success and not options.get("dry_run", False):
            try:
                result_path = result.content.get("result_path")
                if result_path:
                    parent_id = file_info.get("parents", [None])[0]
                    upload_result = drive_service.upload_file(
                        file_path=result_path,
                        parent_folder_id=parent_id
                    )
                    if upload_result.success:
                        result.content["drive_file_id"] = upload_result.content
                        logger.info(
                            f"Uploaded result to Google Drive with ID: {upload_result.content}")
                    else:
                        logger.error(
                            f"Failed to upload to Google Drive: {upload_result.error}")
            except Exception as e:
                logger.error(f"Error during upload to Google Drive: {e}")

        # Add original filename to result
        if result.success:
            result.content["original_file_name"] = file_name

        return result

    except Exception as e:
        logger.exception(f"Error processing Google Drive file: {e}")
        return IntegrationResult.error_result(
            f"Failed to process Google Drive file: {str(e)}")

    finally:
        # Clean up the temporary directory if we created it
        if should_cleanup and temp_dir:
            try:
                fs.delete_directory(temp_dir, recursive=True)
            except Exception as e:
                logger.warning(f"Failed to clean up temporary directory: {e}")


def _process_local_file(
        file_path: str,
        processor_func: FileProcessor,
        output_path: str | None,
        options: dict[str, Any],
        output_dir: str | None = None,
        output_extension: str = ".json"
) -> IntegrationResult:
    """
    Process a local file.

    Args:
        file_path: Path to the local file
        processor_func: Function to process the file content
        output_path: Optional path for output file
        options: Processing options
        output_dir: Output directory
        output_extension: Extension for output files

    Returns:
        IntegrationResult containing the processing result
    """
    # Ensure we're using a clean string path
    file_path_str = str(file_path)

    # Check if file exists
    file_info = fs.get_file_info(file_path_str)
    if not file_info.success or not file_info.exists:
        return IntegrationResult.error_result(f"File not found: {file_path_str}")
    if not file_info.is_file:
        return IntegrationResult.error_result(f"Not a file: {file_path_str}")

    try:
        # Read the file
        logger.info(f"Reading file: {file_path_str}")
        read_result = fs.read_text(file_path_str, encoding="utf-8")
        if not read_result.success:
            return IntegrationResult.error_result(
                f"Failed to read file: {read_result.error}")

        content = read_result.content

        # Process the content
        success, result, error = processor_func(content, options)
        if not success:
            return IntegrationResult.error_result(f"Failed to process content: {error}")

        # Determine output path
        result_path = output_path
        if not result_path:
            basename = os.path.basename(file_path_str)
            stem = os.path.splitext(basename)[0]
            result_path = os.path.join(output_dir or ".", f"{stem}{output_extension}")

        # Create the output directory if it doesn't exist
        output_parent = os.path.dirname(result_path)
        if output_parent:
            fs.create_directory(output_parent, exist_ok=True)

        # Write the result
        logger.info(f"Writing result to: {result_path}")

        # The write method depends on the result type
        if hasattr(result, "model_dump"):
            # Pydantic model
            result_dict = result.model_dump()
            write_result = fs.write_json(result_path, result_dict, atomic=True,
                                         indent=2)
        elif isinstance(result, dict):
            # Dictionary
            write_result = fs.write_json(result_path, result, atomic=True, indent=2)
        else:
            # String or other type
            write_result = fs.write_text(result_path, str(result), encoding="utf-8",
                                         atomic=True)

        if not write_result.success:
            return IntegrationResult.error_result(
                f"Failed to write result: {write_result.error}")

        # Get the filename for the message
        filename = os.path.basename(file_path_str)

        # Return success result
        return IntegrationResult.success_result(
            content={
                "result": result,
                "result_path": result_path,
            },
            message=f"Successfully processed {filename}"
        )

    except Exception as e:
        logger.exception(f"Failed to process local file: {e}")
        return IntegrationResult.error_result(f"Failed to process file: {str(e)}")
