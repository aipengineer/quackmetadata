# src/quackmetadata/config.py
"""
Configuration management for QuackMetadata.

This module uses QuackCore's configuration system to manage settings
for the QuackMetadata application.
"""

import atexit
import logging
import os
from typing import Any

from pydantic import BaseModel, Field
from quackcore.config import load_config
from quackcore.config.models import QuackConfig

# Import QuackCore FS service and helper function.
from quackcore.fs.service import get_service

fs = get_service()

# Keep track of open file handlers to ensure they get closed.
_file_handlers: list[logging.FileHandler] = []


@atexit.register
def _close_file_handlers() -> None:
    """
    Close all file handlers when the program exits.

    This helps avoid resource warnings during test runs.
    """
    for handler in _file_handlers:
        if handler:
            handler.close()
    _file_handlers.clear()


class QuackMetadataConfig(BaseModel):
    """
    QuackMetadata-specific configuration model.

    This model defines the configuration structure specific to QuackMetadata,
    which will be stored in the 'custom' section of the QuackCore config.
    """

    default_prompt_template: str = Field(
        default="generic",
        description="Default prompt template for metadata extraction",
    )

    max_retries: int = Field(
        default=3,
        description="Maximum retries for LLM calls",
        ge=1,
        le=10,
    )

    output_format: str = Field(
        default="json",
        description="Default output format for metadata",
    )

    temp_dir: str = Field(
        default="./temp",
        description="Directory for temporary files",
    )

    output_dir: str = Field(
        default="./output",
        description="Default directory for output files",
    )

    log_level: str = Field(
        default="INFO",
        description="Logging level for QuackMetadata",
    )


def initialize_config(config_path: str | None = None) -> QuackConfig:
    """
    Initialize configuration from a file and set up defaults.

    Args:
        config_path: Optional path to configuration file

    Returns:
        QuackConfig object with QuackMetadata-specific configuration
    """
    global _config
    _config = None

    # Load configuration from file or defaults.
    quack_config = load_config(config_path)

    # Initialize QuackMetadata-specific configuration if not present.
    if hasattr(quack_config.custom, "get"):
        if "quackmetadata" not in quack_config.custom:
            quack_config.custom["quackmetadata"] = QuackMetadataConfig().model_dump()
        metadata_config = quack_config.custom.get("quackmetadata", {})
    else:
        if not hasattr(quack_config.custom, "quackmetadata"):
            setattr(
                quack_config.custom, "quackmetadata", QuackMetadataConfig().model_dump()
            )
        metadata_config = getattr(quack_config.custom, "quackmetadata", {})

    # Get the log level from metadata_config.
    log_level_name = (
        metadata_config.get("log_level", "INFO")
        if isinstance(metadata_config, dict)
        else getattr(metadata_config, "log_level", "INFO")
    )
    log_level = getattr(logging, log_level_name, logging.INFO)

    # When running tests, use minimal logging configuration to avoid file handle issues.
    if "PYTEST_CURRENT_TEST" in os.environ:
        logging.basicConfig(level=log_level, force=True)
        logs_dir = "./logs"  # Default value
        fs.create_directory(logs_dir, exist_ok=True)
        return quack_config

    # In normal operation, use full logging configuration.
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    has_console_handler = any(
        isinstance(h, logging.StreamHandler) and not isinstance(h, logging.FileHandler)
        for h in root_logger.handlers
    )
    if not has_console_handler:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(log_level)
        root_logger.addHandler(console_handler)

    for handler in list(root_logger.handlers):
        if isinstance(handler, logging.FileHandler):
            root_logger.removeHandler(handler)
            handler.close()

    global _file_handlers

    # Use default fallback for logs_dir.
    logs_dir = "./logs"
    if hasattr(quack_config.paths, "logs_dir"):
        logs_dir = quack_config.paths.logs_dir

    # Ensure the logs directory exists using FS.
    fs.create_directory(logs_dir, exist_ok=True)

    try:
        log_file = fs.join_path(logs_dir, "quackmetadata.log")
        file_handler = logging.FileHandler(str(log_file), mode="a")
        file_handler.setLevel(log_level)
        root_logger.addHandler(file_handler)
        _file_handlers.append(file_handler)  # Track for cleanup.
    except (OSError, PermissionError):
        pass

    return quack_config


_config = None


def get_config() -> QuackConfig:
    """
    Get the QuackMetadata configuration.

    Uses lazy initialization to avoid resource issues during testing.

    Returns:
        QuackConfig instance
    """
    global _config
    if _config is None:
        _config = initialize_config()
    return _config


def get_tool_config() -> dict[str, Any]:
    """
    Get the QuackMetadata-specific configuration.

    Returns:
        Dictionary containing QuackMetadata configuration
    """
    config = get_config()
    if hasattr(config.custom, "get"):
        metadata_config = config.custom.get("quackmetadata", {})
    else:
        metadata_config = getattr(config.custom, "quackmetadata", {})
    return metadata_config


def update_tool_config(new_config: dict[str, Any]) -> None:
    """
    Update the QuackMetadata-specific configuration.

    Args:
        new_config: Dictionary containing new configuration values
    """
    config = get_config()
    tool_config = get_tool_config()

    if isinstance(tool_config, dict):
        updated_config = dict(tool_config)
        updated_config.update(new_config)
    else:
        updated_config = new_config

    if hasattr(config.custom, "get"):
        config.custom["quackmetadata"] = updated_config
    else:
        setattr(config.custom, "quackmetadata", updated_config)


def get_logger() -> logging.Logger:
    """
    Get the QuackMetadata logger.

    Returns:
        Logger instance for QuackMetadata
    """
    from quackcore.logging import get_logger

    return get_logger("quackmetadata")
