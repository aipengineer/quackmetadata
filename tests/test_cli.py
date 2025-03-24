# tests/test_cli.py
"""
Tests for QuackTool's CLI functionality.
"""
import logging
from pathlib import Path
from unittest import mock

import pytest
from click.testing import CliRunner

from quacktool.demo_cli import (
    cli,  # This is the click.Group we need to use
)
from quacktool.models import AssetType, ProcessingMode, ProcessingResult


@pytest.fixture
def cli_runner() -> CliRunner:
    """Create a CLI test runner."""
    return CliRunner()


@pytest.fixture
def mock_logging_setup():
    """Mock logging setup to avoid ResourceWarning for unclosed files."""
    with mock.patch("quackcore.cli.boostrap.setup_logging") as mock_setup:
        # Return a mock logger that won't create real file handlers
        mock_logger = mock.MagicMock(spec=logging.Logger)  # Add spec for type checks
        mock_setup.return_value = (mock_logger, lambda: mock_logger)
        yield mock_setup


class TestQuackToolCli:
    """Tests for the QuackTool CLI commands."""

    def test_main_command(self, cli_runner: CliRunner,
                          mock_logging_setup: mock.MagicMock) -> None:
        """Test the main command."""
        with mock.patch("quackcore.cli.init_cli_env") as mock_init:
            # Create a proper mock context
            mock_logger = mock.MagicMock(spec=logging.Logger)
            mock_config = mock.MagicMock()
            mock_ctx = mock.MagicMock()
            mock_ctx.logger = mock_logger
            mock_ctx.config = mock_config
            mock_init.return_value = mock_ctx

            # Test without arguments
            result = cli_runner.invoke(cli, ["main"])
            assert result.exit_code == 0

            # Test with --verbose flag
            result = cli_runner.invoke(cli, ["main", "--verbose"])
            assert result.exit_code == 0

            # Test with --debug flag
            result = cli_runner.invoke(cli, ["main", "--debug"])
            assert result.exit_code == 0

            # Test with --quiet flag
            result = cli_runner.invoke(cli, ["main", "--quiet"])
            assert result.exit_code == 0

    @mock.patch("quacktool.demo_cli.process_asset")
    def test_process_command(
            self, mock_process_asset: mock.MagicMock, cli_runner: CliRunner,
            test_file: Path
    ) -> None:
        """Test the process command."""
        # Set up mock to return success
        mock_process_asset.return_value = ProcessingResult(
            success=True,
            output_path=Path("output/processed.webp"),
            metrics={"size_ratio": 0.8},
            duration_ms=42,
        )

        # Mock init_cli_env to prevent actual environment setup
        with mock.patch("quackcore.cli.init_cli_env") as mock_init:
            # Create a mock context with needed objects
            mock_ctx = mock.MagicMock()
            mock_logger = mock.MagicMock(spec=logging.Logger)
            mock_ctx.logger = mock_logger
            mock_init.return_value = mock_ctx

            # Mock Path.exists to avoid file system checks
            with mock.patch("pathlib.Path.exists", return_value=True):
                # Run command with minimal arguments - provide obj dictionary for context
                result = cli_runner.invoke(cli, ["process", str(test_file)], obj={
                    "logger": mock_logger,
                    "quack_ctx": mock_ctx,
                    "config": {},
                })

        # Check command succeeded
        assert result.exit_code == 0
        assert mock_process_asset.called

        # Run with all options
        with mock.patch("quackcore.cli.init_cli_env") as mock_init:
            mock_ctx = mock.MagicMock()
            mock_logger = mock.MagicMock(spec=logging.Logger)
            mock_ctx.logger = mock_logger
            mock_init.return_value = mock_ctx

            with mock.patch("pathlib.Path.exists", return_value=True):
                result = cli_runner.invoke(cli, [
                    "process",
                    str(test_file),
                    "--output", "output.webp",
                    "--mode", "transform",
                    "--quality", "95",
                    "--format", "webp",
                    "--width", "800",
                    "--height", "600",
                    "--type", "image",
                ], obj={
                    "logger": mock_logger,
                    "quack_ctx": mock_ctx,
                    "config": {},
                })

        # Check command succeeded
        assert result.exit_code == 0
        assert mock_process_asset.called

        # Check AssetConfig was created with correct values
        config = mock_process_asset.call_args[0][0]
        assert config.input_path == test_file
        assert config.options.mode == ProcessingMode.TRANSFORM
        assert config.options.quality == 95
        assert config.options.format == "webp"
        assert config.options.dimensions == (800, 600)
        assert config.asset_type == AssetType.IMAGE

    @mock.patch("quacktool.demo_cli.process_asset")
    def test_process_command_failure(
            self, mock_process_asset: mock.MagicMock, cli_runner: CliRunner,
            test_file: Path
    ) -> None:
        """Test the process command handling failures."""
        # Set up mock to return failure
        mock_process_asset.return_value = ProcessingResult(
            success=False,
            error="Test processing error",
        )

        # Run command with proper mocking
        with mock.patch("quackcore.cli.init_cli_env") as mock_init:
            # Create a mock context with needed objects
            mock_ctx = mock.MagicMock()
            mock_logger = mock.MagicMock(spec=logging.Logger)
            mock_ctx.logger = mock_logger
            mock_init.return_value = mock_ctx

            with mock.patch("pathlib.Path.exists", return_value=True):
                # Mock print_error to raise SystemExit(1) when called
                with mock.patch("quacktool.demo_cli.print_error",
                                side_effect=SystemExit(1)) as mock_print_error:
                    # Use the CLI runner with catch_exceptions=False to let the SystemExit propagate
                    with pytest.raises(SystemExit) as excinfo:
                        # We don't need to capture the result since we're checking for the exception
                        cli_runner.invoke(cli, ["process", str(test_file)],
                                          obj={
                                              "logger": mock_logger,
                                              "quack_ctx": mock_ctx,
                                              "config": {},
                                          }, catch_exceptions=False)

                    # Verify the exit code
                    assert excinfo.value.code == 1

                    # Verify print_error was called
                    mock_print_error.assert_called_once()

    @mock.patch("quacktool.demo_cli.process_asset")
    def test_batch_command(
            self, mock_process_asset: mock.MagicMock, cli_runner: CliRunner,
            temp_dir: Path, test_file: Path
    ) -> None:
        """Test the batch command."""
        # Set up mock to return success
        mock_process_asset.return_value = ProcessingResult(
            success=True,
            output_path=Path("output/processed.webp"),
        )

        # Create output directory
        output_dir = temp_dir / "output"
        output_dir.mkdir(exist_ok=True)

        # We'll mock everything needed for the batch command to run properly
        with mock.patch("quackcore.cli.init_cli_env") as mock_init:
            mock_ctx = mock.MagicMock()
            mock_logger = mock.MagicMock(spec=logging.Logger)
            mock_ctx.logger = mock_logger
            mock_init.return_value = mock_ctx

            # Mock the Path.exists check
            with mock.patch("pathlib.Path.exists", return_value=True):
                # Mock the Path.mkdir to avoid filesystem operations
                with mock.patch("pathlib.Path.mkdir", return_value=None):
                    # Mock the click.Path conversion more directly
                    with mock.patch("click.Path.__call__", return_value=str(test_file)):
                        # Set up custom path conversion for output_dir vs test_file
                        with mock.patch("click.Path.convert") as mock_convert:
                            # Set up parameters with direct values to avoid lambda with multiple arguments
                            mock_convert.return_value = str(
                                output_dir)  # Default to output_dir

                            # Run the command with pre-initialized context
                            result = cli_runner.invoke(cli, [
                                "batch",
                                str(test_file),
                                "--output-dir", str(output_dir),
                                "--mode", "transform",
                                "--quality", "95",
                                "--format", "webp",
                            ], obj={
                                "logger": mock_logger,
                                "quack_ctx": mock_ctx,
                                "config": {},
                            })

                            # After the invoke, set a different return value for the next check
                            mock_convert.return_value = str(test_file)

        # Check command succeeded
        assert result.exit_code == 0
        assert mock_process_asset.called

    @mock.patch("quacktool.demo_cli.process_asset")
    def test_batch_command_failure(
            self, mock_process_asset: mock.MagicMock, cli_runner: CliRunner,
            temp_dir: Path, test_file: Path
    ) -> None:
        """Test the batch command handling failures."""
        # Set up mock to return failure
        mock_process_asset.return_value = ProcessingResult(
            success=False,
            error="Test processing error",
        )

        # Create output directory
        output_dir = temp_dir / "output"
        output_dir.mkdir(exist_ok=True)

        # Set up the CLI runner with the mocks needed
        with mock.patch("quackcore.cli.init_cli_env") as mock_init:
            mock_ctx = mock.MagicMock()
            mock_logger = mock.MagicMock(spec=logging.Logger)
            mock_ctx.logger = mock_logger
            mock_init.return_value = mock_ctx

            # Mock other dependencies
            with mock.patch("pathlib.Path.exists", return_value=True):
                with mock.patch("pathlib.Path.mkdir", return_value=None):
                    # Fix the Click.Path.convert issue
                    with mock.patch("click.Path.convert", return_value=str(test_file)):
                        # Use a separate sys.exit mock to verify it's called
                        with mock.patch("sys.exit") as mock_exit:
                            # Run the batch command through the CLI
                            result = cli_runner.invoke(cli, [
                                "batch",
                                str(test_file),
                                "--output-dir", str(output_dir),
                            ], obj={
                                "logger": mock_logger,
                                "quack_ctx": mock_ctx,
                                "config": {},
                            })

                            # Verify sys.exit was called with code 1
                            mock_exit.assert_called_with(1)

        # Also verify the result exit code for double confirmation
        assert result.exit_code == 1
        
    @mock.patch("quacktool.demo_cli.display_version_info")
    def test_version_command(self, mock_display_version: mock.MagicMock,
                             cli_runner: CliRunner) -> None:
        """Test the version command."""
        # Run command
        result = cli_runner.invoke(cli, ["version"])

        # Check command succeeded and called the version display function
        assert result.exit_code == 0
        mock_display_version.assert_called_once_with(None, None, True)

    def test_cli_group(self) -> None:
        """Test the CLI group structure."""
        # Test that all commands are in the CLI group
        command_names = {cmd.name for cmd in cli.commands.values()}
        assert "main" in command_names
        assert "process" in command_names
        assert "batch" in command_names
        assert "version" in command_names