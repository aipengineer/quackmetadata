# tests/test_plugin.py
"""
Tests for the QuackCore plugin interface.

This module contains tests for the QuackTool plugin functionality.
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from quacktool.plugin import QuackToolPlugin, create_plugin


def test_create_plugin():
    """Test the create_plugin function."""
    plugin = create_plugin()
    assert isinstance(plugin, QuackToolPlugin)
    assert plugin.name == "QuackTool"
    assert plugin.version == "0.1.0"
    assert not plugin._initialized


def test_initialize_plugin():
    """Test plugin initialization."""
    plugin = QuackToolPlugin()
    result = plugin.initialize()
    assert result.success
    assert plugin._initialized
    assert "QuackTool plugin initialized successfully" in result.message


def test_is_available():
    """Test is_available method."""
    plugin = QuackToolPlugin()
    assert not plugin.is_available()  # Not initialized yet

    plugin._initialized = True
    assert plugin.is_available()  # Now initialized


@patch("quacktool.core.process_asset")
def test_process_file(mock_process_asset):
    """Test process_file method."""
    # Create a real temporary file for the test
    with tempfile.NamedTemporaryFile(delete=False) as temp_file:
        temp_file.write(b"Test content")
        temp_path = temp_file.name

    try:
        # Create a mock for the processing result
        mock_result = Mock()
        mock_result.success = True
        mock_result.output_path = Path(temp_path + ".out")
        mock_process_asset.return_value = mock_result

        # Create a plugin instance
        plugin = QuackToolPlugin()
        plugin._initialized = True

        # Test processing the temporary file
        result = plugin.process_file(
            file_path=temp_path,
            output_path=temp_path + ".out",
            options={"quality": 85, "format": "txt"},
        )

        # Verify the result
        assert result.success, f"Expected success but got: {result.error}"
        assert result.content == str(mock_result.output_path)
        assert mock_process_asset.called

        # Check that options were correctly created
        called_args = mock_process_asset.call_args[0][0]
        assert str(called_args.input_path) == temp_path
        assert str(called_args.output_path) == temp_path + ".out"
        assert called_args.options.quality == 85
        assert called_args.options.format == "txt"
    finally:
        # Clean up the temporary file
        if os.path.exists(temp_path):
            os.unlink(temp_path)


@patch("quacktool.core.process_asset")
def test_process_file_error(mock_process_asset):
    """Test process_file method with error."""
    # Create a real temporary file for the test
    with tempfile.NamedTemporaryFile(delete=False) as temp_file:
        temp_file.write(b"Test content")
        temp_path = temp_file.name

    try:
        # Create a mock for an error result
        mock_result = Mock()
        mock_result.success = False
        mock_result.error = "Processing failed"
        mock_process_asset.return_value = mock_result

        # Create a plugin instance
        plugin = QuackToolPlugin()
        plugin._initialized = True

        # Test processing a file that fails
        result = plugin.process_file(
            file_path=temp_path,
        )

        # Verify the result
        assert not result.success
        assert "Processing failed" in result.error
        assert mock_process_asset.called
    finally:
        # Clean up the temporary file
        if os.path.exists(temp_path):
            os.unlink(temp_path)


def test_create_options():
    """Test the _create_options helper method."""
    plugin = QuackToolPlugin()

    # Test with no options
    options = plugin._create_options(None)
    assert options.mode == "optimize"
    assert options.quality == 80

    # Test with mode and quality
    options = plugin._create_options(
        {
            "mode": "transform",
            "quality": 90,
        }
    )
    assert options.mode == "transform"
    assert options.quality == 90

    # Test with dimensions
    options = plugin._create_options(
        {
            "width": 100,
            "height": 200,
        }
    )
    assert options.dimensions == (100, 200)

    # Test with invalid mode (should fall back to default)
    options = plugin._create_options(
        {
            "mode": "invalid",
        }
    )
    assert options.mode == "optimize"