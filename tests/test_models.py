# tests/test_models.py
"""
Tests for the data models.

This module contains tests for the data models used in QuackTool.
"""

import os
import tempfile
from pathlib import Path

import pytest
from pydantic import ValidationError

from quacktool.models import (
    AssetConfig,
    AssetType,
    ProcessingMode,
    ProcessingOptions,
    ProcessingResult,
)


def test_processing_options_defaults():
    """Test ProcessingOptions with default values."""
    options = ProcessingOptions()
    assert options.mode == ProcessingMode.OPTIMIZE
    assert options.quality == 80
    assert options.dimensions is None
    assert options.format is None
    assert options.metadata == {}
    assert options.advanced_options == {}


def test_processing_options_validation():
    """Test ProcessingOptions validation."""
    # Test valid dimensions
    options = ProcessingOptions(dimensions=(100, 100))
    assert options.dimensions == (100, 100)

    # Test invalid dimensions (negative values)
    with pytest.raises(ValidationError):
        ProcessingOptions(dimensions=(0, -1))

    # Test invalid quality (out of range)
    with pytest.raises(ValidationError):
        ProcessingOptions(quality=101)


def test_asset_config_validation():
    """Test AssetConfig validation."""
    # Instead of testing with nonexistent path, create a temp file
    with tempfile.NamedTemporaryFile(delete=False) as temp:
        temp_path = Path(temp.name)

    try:
        # Test with valid input path
        asset_config = AssetConfig(input_path=temp_path)
        assert asset_config.input_path == temp_path
        assert asset_config.output_path is None
        assert asset_config.asset_type == AssetType.OTHER
        assert isinstance(asset_config.options, ProcessingOptions)
        assert asset_config.tags == []

        # Test with nonexistent path should be handled by the model
        # This will only work outside of test mode, so we'll temporarily
        # remove the test marker from the environment
        if 'PYTEST_CURRENT_TEST' in os.environ:
            test_marker = os.environ.pop('PYTEST_CURRENT_TEST')

            # Now try with a nonexistent path
            non_existent = Path(tempfile.gettempdir()) / "nonexistent_file.txt"
            if non_existent.exists():
                os.unlink(non_existent)

            with pytest.raises(ValueError):
                AssetConfig(input_path=non_existent)

            # Restore the test marker
            os.environ['PYTEST_CURRENT_TEST'] = test_marker
    finally:
        # Clean up
        if os.path.exists(temp_path):
            os.unlink(temp_path)


def test_processing_result_init():
    """Test ProcessingResult initialization."""
    # Test success result
    result = ProcessingResult(
        success=True,
        output_path=Path("/path/to/output.txt"),
        metrics={"size_ratio": 0.8},
        duration_ms=150,
    )
    assert result.success
    assert result.output_path == Path("/path/to/output.txt")
    assert result.error is None
    assert result.metrics["size_ratio"] == 0.8
    assert result.duration_ms == 150

    # Test error result
    result = ProcessingResult(
        success=False,
        error="Processing failed",
        duration_ms=50,
    )
    assert not result.success
    assert result.output_path is None
    assert result.error == "Processing failed"
    assert result.metrics == {}
    assert result.duration_ms == 50


def test_asset_type_enum():
    """Test AssetType enum values."""
    assert AssetType.IMAGE.value == "image"
    assert AssetType.VIDEO.value == "video"
    assert AssetType.AUDIO.value == "audio"
    assert AssetType.DOCUMENT.value == "document"
    assert AssetType.OTHER.value == "other"


def test_processing_mode_enum():
    """Test ProcessingMode enum values."""
    assert ProcessingMode.OPTIMIZE.value == "optimize"
    assert ProcessingMode.TRANSFORM.value == "transform"
    assert ProcessingMode.ANALYZE.value == "analyze"
    assert ProcessingMode.GENERATE.value == "generate"