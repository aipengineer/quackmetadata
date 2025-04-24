# src/quackmetadata/integrations/drive_handler.py
"""
Google Drive integration handler for QuackMetadata.

This module provides functions for working with files in Google Drive,
including downloading, uploading, and getting file information.
"""

import tempfile
from typing import Any

from quackcore.fs.service import get_service
from quackcore.integrations.core.results import IntegrationResult
from quackcore.integrations.google.drive import GoogleDriveService
from quackcore.logging import get_logger

fs = get_service()
logger = get_logger(__name__)


def process_drive_file(
        file_id: str, output_path: str | None = None,
        options: dict[str, Any] | None = None
) -> IntegrationResult:
    """
    Process a file from Google Drive.

    Args:
        file_id: Google Drive file ID
        output_path: Optional path for output
        options: Processing options

    Returns:
        IntegrationResult containing the metadata extraction result
    """
    options = options or {}
    logger.info(f"Processing Google Drive file with ID: {file_id}")

    # Create a temporary directory
    temp_dir = tempfile.mkdtemp(prefix="quackmetadata_")

    try:
        # Initialize Google Drive service
        drive_service = GoogleDriveService()
        init_result = drive_service.initialize()
        if not init_result.success:
            return IntegrationResult.error_result(
                f"Failed to initialize Google Drive: {init_result.error}"
            )

        # Download the file
        logger.info(f"Downloading file from Google Drive with ID: {file_id}")
        download_result = drive_service.download_file(
            remote_id=file_id, local_path=temp_dir
        )
        if not download_result.success:
            return IntegrationResult.error_result(
                f"Failed to download file from Google Drive: {download_result.error}"
            )

        # Get the local path to the downloaded file
        local_path = str(download_result.content)
        logger.info(f"Downloaded file to: {local_path}")

        # Get file info from Google Drive
        file_info_result = drive_service.get_file_info(remote_id=file_id)
        if not file_info_result.success:
            return IntegrationResult.error_result(
                f"Failed to get file info from Google Drive: {file_info_result.error}"
            )

        file_info = file_info_result.content
        file_name = file_info.get("name", "unknown")

        # Process the downloaded file
        from quackmetadata.tool import process_file
        result = process_file(local_path, output_path, options)

        # Upload metadata file back to Google Drive if successful and not in dry run mode
        if result.success and not options.get("dry_run", False):
            metadata_path = result.content.get("metadata_path")
            if metadata_path:
                parent_id = file_info.get("parents", [None])[0]
                upload_result = drive_service.upload_file(
                    file_path=metadata_path, parent_folder_id=parent_id
                )
                if upload_result.success:
                    result.content["drive_file_id"] = upload_result.content
                    logger.info(
                        f"Uploaded metadata file to Google Drive with ID: {upload_result.content}"
                    )
                else:
                    logger.error(
                        f"Failed to upload metadata file to Google Drive: {upload_result.error}"
                    )

        # Add original file name to result
        if result.success:
            result.content["original_file_name"] = file_name

        return result

    except Exception as e:
        logger.exception(f"Error processing Google Drive file: {e}")
        return IntegrationResult.error_result(
            f"Failed to process Google Drive file: {str(e)}")

    finally:
        # Clean up the temporary directory
        try:
            fs.delete_directory(temp_dir, recursive=True)
        except Exception as e:
            logger.warning(f"Failed to clean up temporary directory: {e}")
