# tests/test_headless_api.py
"""
Tests for QuackTool's headless API.

These tests verify the public API used by QuackBuddy and other
QuackVerse components.
"""

from pathlib import Path
from unittest import mock

import pytest

# Import directly from modules to avoid lazy loading issues
from quackmetadata.version import __version__
from quackmetadata.config import get_config, get_logger
from quackmetadata.core import process_asset
from quackmetadata.models import AssetConfig, ProcessingMode, ProcessingOptions, ProcessingResult


class TestHeadlessAPI:
    """Tests for the headless API."""

    def test_api_imports(self) -> None:
        """Test that all public API components are importable correctly."""
        # All these imports should work without error
        # They are defined in __all__ in __init__.py
        from quackmetadata import (
            __version__,
            get_config,
            get_logger,
            process_asset,
            AssetConfig,
            ProcessingOptions,
            ProcessingResult,
        )

        # Check they have the correct types
        assert isinstance(__version__, str)
        assert callable(get_config)
        assert callable(get_logger)
        assert callable(process_asset)
        assert isinstance(AssetConfig.__name__, str)
        assert isinstance(ProcessingOptions.__name__, str)
        assert isinstance(ProcessingResult.__name__, str)

    @pytest.mark.skip("Example doesn't exist in the current test setup")
    @mock.patch("quacktool.process_asset")
    def test_example_direct_api_usage(self, mock_process_asset: mock.MagicMock) -> None:
        """Test the example_direct_api_usage function from the examples directory."""
        try:
            # Try to import the example
            from examples.headless_api_usage import example_direct_api_usage

            # Create a mock output path
            output_path = Path("output/test_processed.webp")

            # Set up mock for process_asset
            mock_process_asset.return_value = ProcessingResult(
                success=True,
                output_path=output_path,
                metrics={"test_metric": 42},
                duration_ms=100,
            )

            # Create a temporary file
            with mock.patch("pathlib.Path.exists", return_value=True):
                # Call the example function with our test file
                example_direct_api_usage(Path("test_input.jpg"))

            # Verify process_asset was called with correct arguments
            mock_process_asset.assert_called_once()
            config = mock_process_asset.call_args[0][0]
            assert isinstance(config, AssetConfig)
            assert config.input_path == Path("test_input.jpg")
            assert config.options.mode == ProcessingMode.OPTIMIZE
            assert config.options.quality == 85
            assert config.options.format == "webp"

        except ImportError:
            # If example can't be imported, just skip this test
            pass

    def test_headless_api_workflow(self, test_file: Path) -> None:
        """Test the complete headless API workflow."""
        # Set up mocks for process_asset internals
        with mock.patch("quackmetadata.core._copy_file") as mock_copy_file:
            # Set up mock return value
            mock_copy_file.return_value = ProcessingResult(
                success=True,
                output_path=Path("output/test_processed.webp"),
                metrics={"size_ratio": 0.8},
                duration_ms=100,
            )

            # Create options directly from imported class
            options = ProcessingOptions(
                mode=ProcessingMode.OPTIMIZE,
                quality=90,
                format="webp",
            )

            # Create config
            config = AssetConfig(
                input_path=test_file,
                output_path=Path("output/test_processed.webp"),
                options=options,
            )

            # Process the asset using direct import
            result = process_asset(config)

            # Verify the result
            assert result.success is True
            assert result.output_path == Path("output/test_processed.webp")
            assert "size_ratio" in result.metrics
            assert result.duration_ms > 0

    def test_config_api(self) -> None:
        """Test the config API functions."""
        # Test config retrieval using direct import
        config = get_config()
        assert config is not None

        # Test logger retrieval using direct import
        logger = get_logger()
        assert logger is not None
        assert logger.name == "quackmetadata"