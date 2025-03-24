# tests/test_headless_api.py
"""
Tests for the headless API usage pattern.

This module tests how QuackBuddy would interact with QuackTool,
ensuring the public API is clean and properly defined.
"""

import os
import tempfile
from pathlib import Path

import pytest

# Import directly from the quacktool package (as QuackBuddy would)
from quacktool import process_asset
from quacktool.models import AssetConfig, AssetType, ProcessingMode, ProcessingOptions


@pytest.fixture
def sample_file():
    """Create a temporary sample file for testing."""
    with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as temp:
        temp.write(b"This is a test file for the headless API")
        temp_path = temp.name

    yield Path(temp_path)

    # Clean up
    if os.path.exists(temp_path):
        os.unlink(temp_path)


def test_headless_api_usage(sample_file):
    """
    Test QuackTool's headless API as QuackBuddy would use it.

    This test verifies that the process_asset function can be imported
    and used directly, as would be expected in QuackBuddy.
    """
    # Create a temporary output directory
    with tempfile.TemporaryDirectory() as temp_dir:
        output_path = Path(temp_dir) / "output.txt"

        # Create asset configuration
        asset_config = AssetConfig(
            input_path=sample_file,
            output_path=output_path,
            asset_type=AssetType.DOCUMENT,
            options=ProcessingOptions(
                mode=ProcessingMode.OPTIMIZE,
                quality=85,
            ),
        )

        # Process the asset using the headless API
        result = process_asset(asset_config)

        # Verify the result
        assert result.success, f"Processing failed: {result.error}"
        assert result.output_path == output_path
        assert result.output_path.exists()
        assert "input_size" in result.metrics
        assert "output_size" in result.metrics
        assert "size_ratio" in result.metrics


def test_headless_api_with_defaults(sample_file):
    """
    Test QuackTool's headless API with minimal configuration.

    This test verifies that the process_asset function works with
    minimal options, relying on defaults when possible.
    """
    # Create asset configuration with minimal options
    asset_config = AssetConfig(
        input_path=sample_file,
    )

    # Process the asset using the headless API
    result = process_asset(asset_config)

    # Verify the result
    assert result.success, f"Processing failed: {result.error}"
    assert result.output_path is not None
    assert result.output_path.exists()
    # The duration should be non-zero now due to our fixes
    assert result.duration_ms > 0, f"Duration was {result.duration_ms} but should be positive"