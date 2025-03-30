# tests/test_property_based.py
"""
Property-based tests for QuackTool using Hypothesis.

These tests verify that QuackTool behaves correctly for a wide range of inputs.
"""

import os
import tempfile
from pathlib import Path
from typing import Any
from unittest import mock

import hypothesis
from hypothesis import given, strategies as st

from quacktool.core import _detect_by_extension, _generate_output_path, process_asset
from quacktool.models import (
    AssetConfig,
    AssetType,
    ProcessingMode,
    ProcessingOptions,
    ProcessingResult,
)


# Define custom strategies
@st.composite
def asset_type_strategy(draw: Any) -> AssetType:
    """Strategy for generating AssetType values."""
    return draw(st.sampled_from(list(AssetType)))


@st.composite
def processing_mode_strategy(draw: Any) -> ProcessingMode:
    """Strategy for generating ProcessingMode values."""
    return draw(st.sampled_from(list(ProcessingMode)))


@st.composite
def valid_file_path_strategy(draw: Any) -> Path:
    """Strategy for generating valid file paths."""
    # Generate a random file extension from common types
    extension = draw(st.sampled_from([
        ".jpg", ".png", ".webp", ".mp4", ".mp3", ".pdf", ".txt", ".md",
        ".doc", ".zip", ".json", ".xml", ".csv", ".html", ".css", ".js",
    ]))

    # Generate a random file name (1-3 parts, each 1-10 characters)
    parts = draw(st.lists(
        st.text(st.characters(
            whitelist_categories=["Lu", "Ll", "Nd"],
            whitelist_characters="_-"),
            min_size=1, max_size=10),
        min_size=1, max_size=3)
    )
    filename = "_".join(parts) + extension

    # Generate a random directory depth (0-3 levels)
    dir_depth = draw(st.integers(min_value=0, max_value=3))

    # Generate random directory names
    if dir_depth > 0:
        dirs = draw(st.lists(
            st.text(st.characters(
                whitelist_categories=["Lu", "Ll", "Nd"],
                whitelist_characters="_-"),
                min_size=1, max_size=10),
            min_size=dir_depth, max_size=dir_depth)
        )
        path = Path(*dirs) / filename
    else:
        path = Path(filename)

    return path


@st.composite
def processing_options_strategy(draw: Any) -> ProcessingOptions:
    """Strategy for generating ProcessingOptions."""
    mode = draw(processing_mode_strategy())
    quality = draw(st.integers(min_value=1, max_value=100))

    # Randomly decide whether to include dimensions
    include_dimensions = draw(st.booleans())
    dimensions = None
    if include_dimensions:
        width = draw(st.integers(min_value=1, max_value=5000))
        height = draw(st.integers(min_value=1, max_value=5000))
        dimensions = (width, height)

    # Randomly decide whether to include format
    include_format = draw(st.booleans())
    format_str = None
    if include_format:
        format_str = draw(
            st.sampled_from(["jpg", "png", "webp", "mp4", "mp3", "pdf", "txt"]))

    # Generate random metadata
    metadata_count = draw(st.integers(min_value=0, max_value=5))
    metadata = {}
    for _ in range(metadata_count):
        key = draw(st.text(st.characters(
            whitelist_categories=["Lu", "Ll", "Nd"],
            whitelist_characters="_-"),
            min_size=1, max_size=10))
        value = draw(st.text(st.characters(
            whitelist_categories=["Lu", "Ll", "Nd"],
            whitelist_characters=" _-:."),
            min_size=1, max_size=20))
        metadata[key] = value

    return ProcessingOptions(
        mode=mode,
        quality=quality,
        dimensions=dimensions,
        format=format_str,
        metadata=metadata,
    )


@st.composite
def asset_config_strategy(draw: Any) -> AssetConfig:
    """Strategy for generating AssetConfig."""
    input_path = draw(valid_file_path_strategy())

    # Randomly decide whether to include output path
    include_output = draw(st.booleans())
    output_path = None
    if include_output:
        output_path = draw(valid_file_path_strategy())

    asset_type = draw(asset_type_strategy())
    options = draw(processing_options_strategy())

    # Generate random tags
    tag_count = draw(st.integers(min_value=0, max_value=5))
    tags = []
    for _ in range(tag_count):
        tag = draw(st.text(st.characters(
            whitelist_categories=["Lu", "Ll", "Nd"],
            whitelist_characters="_-"),
            min_size=1, max_size=10))
        tags.append(tag)

    return AssetConfig(
        input_path=input_path,
        output_path=output_path,
        asset_type=asset_type,
        options=options,
        tags=tags,
    )


class TestPropertyBased:
    """Property-based tests for QuackTool."""

    @given(st.sampled_from([
        "test.jpg", "test.jpeg", "test.png", "test.gif", "test.webp",
        "test.mp4", "test.avi", "test.mov", "test.wmv",
        "test.mp3", "test.wav", "test.ogg", "test.flac",
        "test.pdf", "test.doc", "test.docx", "test.txt", "test.md",
        "test.unknown", "test", "test.123", ".hidden",
    ]))
    def test_extension_detection_properties(self, filename: str) -> None:
        """Test that extension detection works for all file types."""
        # Convert string to Path
        path = Path(filename)

        # Get detected type
        detected_type = _detect_by_extension(path)

        # Every path should return a valid AssetType
        assert isinstance(detected_type, AssetType)

        # Check expected types for known extensions
        suffix = path.suffix.lower()
        if suffix in {".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg"}:
            assert detected_type == AssetType.IMAGE
        elif suffix in {".mp4", ".avi", ".mov", ".wmv", ".mkv"}:
            assert detected_type == AssetType.VIDEO
        elif suffix in {".mp3", ".wav", ".ogg", ".flac"}:
            assert detected_type == AssetType.AUDIO
        elif suffix in {".pdf", ".doc", ".docx", ".txt", ".md", ".html"}:
            assert detected_type == AssetType.DOCUMENT

    @given(processing_options_strategy())
    def test_processing_options_properties(self, options: ProcessingOptions) -> None:
        """Test that ProcessingOptions behaves correctly for all inputs."""
        # Mode must be a valid ProcessingMode
        assert isinstance(options.mode, ProcessingMode)
        assert options.mode.value in ProcessingMode.get_values()  # Use get_values() instead of values

        # Quality must be within range
        assert 0 <= options.quality <= 100

        # If dimensions are provided, they must be a tuple of two positive integers
        if options.dimensions is not None:
            assert isinstance(options.dimensions, tuple)
            assert len(options.dimensions) == 2
            assert all(isinstance(d, int) and d > 0 for d in options.dimensions)

        # Format must be a string if provided
        if options.format is not None:
            assert isinstance(options.format, str)

        # Metadata must be a dictionary
        assert isinstance(options.metadata, dict)

        # Advanced options must be a dictionary
        assert isinstance(options.advanced_options, dict)

    @mock.patch("pathlib.Path.exists")
    @given(st.text(min_size=1, max_size=10).map(lambda s: f"test_{s}.txt"))
    def test_output_path_generation_properties(
            self,
            mock_exists: mock.MagicMock,
            filename: str,
    ) -> None:
        """Test that output path generation works correctly for all inputs."""
        # Set up mock for path existence check
        # First call returns False (path doesn't exist)
        mock_exists.return_value = False

        # Create input path
        input_path = Path(filename)

        # Test with proper mocking for generate_output_path
        with mock.patch("quacktool.core.resolver.resolve_project_path") as mock_resolve:
            with mock.patch("quacktool.core.get_tool_config") as mock_config:
                mock_config.return_value = {"output_dir": "./output"}
                mock_resolve.return_value = Path("./output")

                # Skip the actual exists() call by controlling the return value
                with mock.patch("pathlib.Path.exists") as mock_path_exists:
                    mock_path_exists.return_value = False  # Path doesn't exist, no counter needed

                    # Now test the function
                    output_path = _generate_output_path(input_path)

                    # Output path should have the same extension as input
                    assert output_path.suffix == input_path.suffix
                    # Output path should have the input stem in its name
                    assert input_path.stem in output_path.stem
                    # Output path should be in the output directory
                    assert output_path.parent == Path("./output")

    def test_process_asset_type_properties(self) -> None:
        """Test that process_asset handles all asset types correctly."""
        # Using simpler approach without mixing Hypothesis and mock.patch
        for asset_type in list(AssetType):
            # Set up mocks
            with mock.patch("pathlib.Path.exists", return_value=True):
                with mock.patch("quacktool.core._generate_output_path") as mock_generate_output:
                    with mock.patch("quacktool.core._process_by_type_and_mode") as mock_process:
                        # Configure mocks
                        output_path = Path("output/test.txt")
                        mock_generate_output.return_value = output_path
                        mock_process.return_value = ProcessingResult(
                            success=True,
                            output_path=output_path,
                        )

                        # Create test config with the given asset type
                        # Create a temporary file for the input_path
                        with tempfile.NamedTemporaryFile() as temp_file:
                            input_path = Path(temp_file.name)
                            config = AssetConfig(
                                input_path=input_path,
                                asset_type=asset_type,
                            )

                            # Process the asset
                            result = process_asset(config)

                            # Result should be successful
                            assert result.success is True
                            assert result.output_path == output_path

                            # The process function should be called with the correct asset type
                            mock_process.assert_called_once()
                            args = mock_process.call_args[0]
                            assert args[1] == asset_type

    def test_process_asset_mode_properties(self) -> None:
        """Test that process_asset handles all processing modes correctly."""
        # Using simpler approach without mixing Hypothesis and mock.patch
        for mode in list(ProcessingMode):
            # Skip test if running in CI
            if os.environ.get("CI") == "true":
                continue

            # Set up mocks
            with mock.patch("quacktool.core.fs.get_file_info") as mock_file_info:
                with mock.patch("quacktool.core.fs.copy") as mock_copy:
                    # Configure mocks
                    mock_file_info.return_value = mock.MagicMock(
                        success=True,
                        exists=True,
                        size=1024,
                    )
                    mock_copy.return_value = mock.MagicMock(success=True)

                    # Create a temporary file for testing
                    with tempfile.NamedTemporaryFile() as temp_file:
                        input_path = Path(temp_file.name)
                        output_path = Path("output/test.txt")

                        # Mock _generate_output_path to avoid config issues
                        with mock.patch("quacktool.core._generate_output_path") as mock_generate:
                            mock_generate.return_value = output_path

                            # Create config with the given mode
                            config = AssetConfig(
                                input_path=input_path,
                                output_path=output_path,
                                options=ProcessingOptions(mode=mode),
                            )

                            # Mock additional functions to avoid actual processing
                            with mock.patch("quacktool.core._process_by_type_and_mode") as mock_process:
                                mock_process.return_value = ProcessingResult(
                                    success=True,
                                    output_path=output_path,
                                )

                                # Process the asset
                                with mock.patch("pathlib.Path.exists", return_value=True):
                                    result = process_asset(config)

                            # Result should be successful
                            assert result.success is True
                            assert result.output_path == output_path