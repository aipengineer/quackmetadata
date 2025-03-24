# tests/test_core.py
"""
Tests for core functionality.

This module contains tests for the core functionality of QuackTool.
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from quacktool.core import process_asset
from quacktool.models import (
    AssetConfig,
    AssetType,
    ProcessingMode,
    ProcessingOptions,
    ProcessingResult,
)


@pytest.fixture
def sample_file():
    """Create a temporary sample file for testing."""
    with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as temp:
        temp.write(b"This is a test file")
        temp_path = temp.name

    yield Path(temp_path)

    # Clean up
    if os.path.exists(temp_path):
        os.unlink(temp_path)


def test_process_asset_basic(sample_file):
    """Test basic asset processing."""
    # Create a temporary output directory
    with tempfile.TemporaryDirectory() as temp_dir:
        output_path = Path(temp_dir) / "output.txt"

        # Create asset configuration
        asset_config = AssetConfig(
            input_path=sample_file,
            output_path=output_path,
            asset_type=AssetType.OTHER,
            options=ProcessingOptions(
                mode=ProcessingMode.OPTIMIZE,
                quality=80,
            ),
        )

        # Process the asset
        result = process_asset(asset_config)

        # Verify the result
        assert result.success
        assert result.output_path == output_path
        assert result.output_path.exists()
        assert result.duration_ms > 0
        assert "input_size" in result.metrics
        assert "output_size" in result.metrics
        assert "size_ratio" in result.metrics


def test_process_asset_nonexistent_file():
    """Test processing a nonexistent file."""
    # Create a temporary directory to use as base
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create a nonexistent file path within the temp dir
        input_path = Path(temp_dir) / "nonexistent" / "file.txt"

        # Create asset configuration with direct file validation check
        with patch("quacktool.models.Path.exists", return_value=False):
            # This should fail gracefully with a proper error message
            result = process_asset(AssetConfig(
                input_path=input_path,
                asset_type=AssetType.OTHER,
            ))

            # Check that it failed with the appropriate error
            assert not result.success
            assert "Input file not found" in result.error


@patch("quacktool.core._detect_asset_type")
def test_process_asset_with_auto_detection(mock_detect, sample_file):
    """Test asset processing with automatic type detection."""
    # Mock the asset type detection to return IMAGE
    mock_detect.return_value = AssetType.IMAGE

    # Create a temporary output directory
    with tempfile.TemporaryDirectory() as temp_dir:
        output_path = Path(temp_dir) / "output.png"

        # Create asset configuration with auto-detection
        asset_config = AssetConfig(
            input_path=sample_file,
            output_path=output_path,
            asset_type=AssetType.OTHER,  # This should be overridden by the mock
            options=ProcessingOptions(
                mode=ProcessingMode.OPTIMIZE,
                quality=80,
            ),
        )

        # Process the asset
        result = process_asset(asset_config)

        # Verify the result
        assert result.success
        assert mock_detect.called
        assert result.output_path == output_path


@patch("quacktool.core._process_image")
def test_process_asset_by_type(mock_process_image, sample_file):
    """Test processing assets by specific types."""
    # Mock the image processing function
    mock_process_image.return_value = ProcessingResult(
        success=True,
        output_path=Path("/mock/output.png"),
        metrics={"test": "value"},
    )

    # Create asset configuration with explicit IMAGE type
    asset_config = AssetConfig(
        input_path=sample_file,
        asset_type=AssetType.IMAGE,
        options=ProcessingOptions(
            mode=ProcessingMode.OPTIMIZE,
            quality=80,
        ),
    )

    # Process the asset
    result = process_asset(asset_config)

    # Verify that the image processing function was called
    assert mock_process_image.called
    assert result.success
    assert result.metrics.get("test") == "value"