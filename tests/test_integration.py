# tests/test_integration.py
"""
Integration tests for QuackTool.

These tests verify that QuackTool components work together correctly.
"""
import logging
import os
from pathlib import Path
from unittest import mock

import pytest

# Import function directly to avoid lazy loading
from quackmetadata.core import process_asset
from quackmetadata.models import AssetConfig, ProcessingMode, ProcessingOptions
from quackmetadata.plugin import create_plugin


class TestQuackToolIntegration:
    """Integration tests between components."""

    def test_api_and_plugin_consistency(self, test_file: Path) -> None:
        """Test that direct API and plugin interface provide consistent results."""
        # Create a common output path
        output_path = Path("output/test_processed.txt")

        # Using the API directly
        with mock.patch("quackmetadata.core._copy_file") as mock_copy_file:
            # Set up mock for the copy operation to avoid actual file operations
            mock_copy_file.return_value = mock.MagicMock(
                success=True,
                output_path=output_path,
                metrics={"test_metric": 42},
            )

            # Process via API
            api_config = AssetConfig(
                input_path=test_file,
                output_path=output_path,
                options=ProcessingOptions(quality=95, format="txt"),
            )
            # Use process_asset directly from core to avoid lazy loading issues
            api_result = process_asset(api_config)

            # Process via plugin
            plugin = create_plugin()
            plugin.initialize()
            plugin_result = plugin.process_file(
                str(test_file),
                str(output_path),
                {"quality": 95, "format": "txt"},
            )

        # Both should have succeeded
        assert api_result.success is True
        assert plugin_result.success is True

        # Plugin result should contain the output path as content
        assert str(api_result.output_path) in plugin_result.content

    @mock.patch("quacktool.core._copy_file")
    def test_end_to_end_workflow(
            self, mock_copy_file: mock.MagicMock, test_file: Path
    ) -> None:
        """Test entire workflow from input to output."""
        # Set up mock for the copy operation
        output_path = Path("output/result.txt")
        mock_copy_file.return_value = mock.MagicMock(
            success=True,
            output_path=output_path,
            metrics={"size_ratio": 0.8},
        )

        # Create an asset config with various options
        config = AssetConfig(
            input_path=test_file,
            output_path=output_path,
            options=ProcessingOptions(
                mode=ProcessingMode.TRANSFORM,
                quality=90,
                format="txt",
                metadata={"author": "Test Author"},
            ),
            tags=["test", "integration"],
        )

        # Process the asset - use directly from core
        result = process_asset(config)

        # Verify the result
        assert result.success is True
        assert result.output_path == output_path
        assert "size_ratio" in result.metrics
        assert result.duration_ms > 0

        # Verify correct parameters were passed to copy function
        mock_copy_file.assert_called_once_with(test_file, output_path)

    @pytest.mark.skipif(os.environ.get("SKIP_QUACKCORE_TESTS") == "1",
                        reason="QuackCore dependency not available")
    def test_quackcore_integration(self, test_file: Path) -> None:
        """
        Test integration with QuackCore components.

        This test is skipped if SKIP_QUACKCORE_TESTS is set to avoid
        failing when QuackCore is not available.
        """
        try:
            # These imports are in the test to avoid failing if QuackCore
            # is not available
            from quackcore.fs import service as fs
            from quackcore.plugins import registry

            # Check if QuackTool plugin is registered with QuackCore
            plugin = registry.get_plugin("QuackTool")
            if plugin is None:
                pytest.skip("QuackTool plugin not registered with QuackCore")

            # Initialize plugin and test basic operations
            plugin.initialize()
            assert plugin.is_available() is True
            assert plugin.name == "QuackTool"

            # Test file operations with QuackCore's fs service
            file_info = fs.get_file_info(test_file)
            assert file_info.success is True
            assert file_info.exists is True

            # Test processing a file through QuackCore's plugin system
            with mock.patch("quackmetadata.plugin.process_asset") as mock_process:
                mock_process.return_value = mock.MagicMock(
                    success=True,
                    output_path=Path("output/result.txt"),
                )

                result = plugin.process_file(str(test_file))
                assert result.success is True

        except ImportError:
            pytest.skip("QuackCore dependency not available")


class TestCliIntegration:
    """Integration tests for the CLI component."""

    @mock.patch("quacktool.demo_cli.process_asset")
    def test_cli_to_core_integration(
            self, mock_process_asset: mock.MagicMock, test_file: Path
    ) -> None:
        """Test that CLI correctly interfaces with core processing."""
        from quackmetadata.demo_cli import cli  # Import the CLI group, not the function
        from click.testing import CliRunner

        # Set up the mock return value
        mock_process_asset.return_value = mock.MagicMock(
            success=True,
            output_path=Path("output/test.webp"),
            metrics={"size_ratio": 0.8},
            duration_ms=42,
        )

        # Run the CLI command with proper environment
        runner = CliRunner()

        with mock.patch("quackcore.cli.init_cli_env") as mock_init:
            # Create a proper mock context
            mock_logger = mock.MagicMock(spec=logging.Logger)
            mock_config = mock.MagicMock()
            mock_ctx = mock.MagicMock()
            mock_ctx.logger = mock_logger
            mock_ctx.config = mock_config
            mock_init.return_value = mock_ctx

            # Mock Path.exists to avoid file system checks
            with mock.patch("pathlib.Path.exists", return_value=True):
                # Mock the Click path conversion
                with mock.patch("click.Path.convert") as mock_convert:
                    mock_convert.return_value = str(test_file)

                    # Run the command using the CLI group with the process command name
                    result = runner.invoke(cli, [
                        "process",  # Command name
                        str(test_file),
                        "--mode", "transform",
                        "--quality", "95",
                    ], obj={
                        "logger": mock_logger,
                        "quack_ctx": mock_ctx,
                        "config": {},
                    })

        # Check that the command succeeded
        assert result.exit_code == 0

        # Verify the core function was called with correct arguments
        mock_process_asset.assert_called_once()
        config = mock_process_asset.call_args[0][0]
        assert config.input_path == test_file
        assert config.options.mode == ProcessingMode.TRANSFORM
        assert config.options.quality == 95