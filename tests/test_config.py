# tests/test_config.py
"""
Tests for QuackTool's configuration management.
"""

import logging
import os
from pathlib import Path
from typing import Generator
from unittest import mock

import pytest

from quacktool.config import (
    QuackToolConfig,
    _close_file_handlers,
    get_config,
    get_logger,
    get_tool_config,
    initialize_config,
    update_tool_config,
)


@pytest.fixture
def patch_log_handlers() -> Generator[None, None, None]:
    """Reset log handlers after test."""
    # Store original handlers
    root_logger = logging.getLogger()
    original_handlers = list(root_logger.handlers)

    yield

    # Restore original handlers
    root_logger.handlers = original_handlers


@pytest.fixture
def test_config_path(temp_dir: Path) -> str:
    """Create a test configuration file."""
    config_path = temp_dir / "test_config.yaml"
    with open(config_path, "w") as f:
        f.write("""
general:
  project_name: TestProject
  environment: test

custom:
  quacktool:
    default_quality: 90
    default_format: test_format
    temp_dir: ./test_temp
    output_dir: ./test_output
    log_level: DEBUG
""")
    return str(config_path)


class TestConfigManagement:
    """Tests for configuration management functions."""

    def test_quacktool_config_model(self) -> None:
        """Test QuackToolConfig model defaults and validation."""
        config = QuackToolConfig()

        # Check default values
        assert config.default_quality == 80
        assert config.default_format == "webp"
        assert config.temp_dir == "./temp"
        assert config.output_dir == "./output"
        assert config.log_level == "INFO"

        # Test with custom values
        custom_config = QuackToolConfig(
            default_quality=95,
            default_format="jpg",
            temp_dir="./custom_temp",
            output_dir="./custom_output",
            log_level="DEBUG",
        )
        assert custom_config.default_quality == 95
        assert custom_config.default_format == "jpg"
        assert custom_config.temp_dir == "./custom_temp"
        assert custom_config.output_dir == "./custom_output"
        assert custom_config.log_level == "DEBUG"

    def test_initialize_config_with_file(self, test_config_path: str) -> None:
        """Test initializing configuration with a file."""
        # We don't use the return value, just call the function for its side effects
        initialize_config(test_config_path)

        # Check loaded values from the file
        tool_config = get_tool_config()

        if isinstance(tool_config, dict):
            assert tool_config.get("default_quality") == 90
            assert tool_config.get("default_format") == "test_format"
            assert tool_config.get("temp_dir") == "./test_temp"
            assert tool_config.get("output_dir") == "./test_output"
            assert tool_config.get("log_level") == "DEBUG"
        else:
            assert getattr(tool_config, "default_quality", None) == 90
            assert getattr(tool_config, "default_format", None) == "test_format"
            assert getattr(tool_config, "temp_dir", None) == "./test_temp"
            assert getattr(tool_config, "output_dir", None) == "./test_output"
            assert getattr(tool_config, "log_level", None) == "DEBUG"

    def test_initialize_config_default(self) -> None:
        """Test initializing configuration with defaults."""
        config = initialize_config()

        # Make sure quacktool config is created with defaults
        if hasattr(config.custom, "get"):
            assert "quacktool" in config.custom
            quacktool_config = config.custom.get("quacktool", {})
        else:
            assert hasattr(config.custom, "quacktool")
            quacktool_config = getattr(config.custom, "quacktool", {})

        # Config could be dict or object depending on QuackCore implementation
        if isinstance(quacktool_config, dict):
            assert quacktool_config.get("default_quality") == 80
            assert quacktool_config.get("default_format") == "webp"
        else:
            assert getattr(quacktool_config, "default_quality", None) == 80
            assert getattr(quacktool_config, "default_format", None) == "webp"

    def test_get_config(self) -> None:
        """Test get_config function."""
        # First call initializes the config
        config1 = get_config()
        assert config1 is not None

        # Second call should return the same object (cached)
        config2 = get_config()
        assert config2 is config1

    def test_get_tool_config(self) -> None:
        """Test get_tool_config function."""
        tool_config = get_tool_config()
        assert tool_config is not None

        # Should contain default values
        if isinstance(tool_config, dict):
            assert "default_quality" in tool_config
            assert "default_format" in tool_config
        else:
            assert hasattr(tool_config, "default_quality")
            assert hasattr(tool_config, "default_format")

    def test_update_tool_config(self) -> None:
        """Test update_tool_config function."""
        # Get original config - no need to store it since we don't compare later
        # Just retrieve it to ensure it's initialized
        get_tool_config()

        # Update with new values
        new_values = {
            "default_quality": 95,
            "custom_option": "test_value",
        }
        update_tool_config(new_values)

        # Get updated config
        updated_config = get_tool_config()

        # Check that values were updated
        if isinstance(updated_config, dict):
            assert updated_config.get("default_quality") == 95
            assert updated_config.get("custom_option") == "test_value"
        else:
            assert getattr(updated_config, "default_quality", None) == 95
            assert getattr(updated_config, "custom_option", None) == "test_value"

    @mock.patch("logging.FileHandler")
    @mock.patch("pathlib.Path.mkdir")
    def test_initialize_logging(self, mock_mkdir: mock.MagicMock,
                                mock_file_handler: mock.MagicMock,
                                patch_log_handlers: None) -> None:
        """Test initializing logging configuration."""
        # Set up mocks
        mock_file_handler.return_value = mock.MagicMock()

        # Initialize config which sets up logging
        initialize_config()

        # Directory should be created for logs
        mock_mkdir.assert_called()

        # File handler should be created (unless PYTEST_CURRENT_TEST is set)
        if "PYTEST_CURRENT_TEST" not in os.environ:
            mock_file_handler.assert_called()

    def test_get_logger(self) -> None:
        """Test get_logger function."""
        logger = get_logger()
        assert isinstance(logger, logging.Logger)
        assert logger.name == "quacktool"

    def test_close_file_handlers(self) -> None:
        """Test _close_file_handlers function."""
        # Create a mock handler
        mock_handler = mock.MagicMock(spec=logging.FileHandler)

        # Add it to the module-level list
        from quacktool.config import _file_handlers
        _file_handlers.append(mock_handler)

        # Call the close function
        _close_file_handlers()

        # Verify handler was closed
        mock_handler.close.assert_called_once()

        # List should be cleared
        assert len(_file_handlers) == 0