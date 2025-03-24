# tests/test_cli.py
"""
Tests for QuackTool's CLI functionality.
"""

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


class TestQuackToolCli:
    """Tests for the QuackTool CLI commands."""

    def test_main_command(self, cli_runner: CliRunner) -> None:
        """Test the main command."""
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

        # Run command with minimal arguments
        with mock.patch("click.Path.convert") as mock_convert:
            mock_convert.return_value = str(test_file)
            result = cli_runner.invoke(cli, ["process", str(test_file)])

        # Check command succeeded and used the mock
        assert result.exit_code == 0
        assert mock_process_asset.called

        # Run with all options
        with mock.patch("click.Path.convert") as mock_convert:
            mock_convert.side_effect = lambda _, __, ___, **kw: str(test_file)
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
            ])

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

        # Run command
        with mock.patch("click.Path.convert") as mock_convert:
            mock_convert.return_value = str(test_file)
            # Replace sys.exit with a custom exception to capture exit code
            with mock.patch("quacktool.demo_cli.print_error") as mock_print_error:
                mock_print_error.side_effect = SystemExit(1)
                with pytest.raises(SystemExit) as excinfo:
                    cli_runner.invoke(cli, ["process", str(test_file)])
                assert excinfo.value.code == 1

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

        # Run command with minimal arguments
        with mock.patch("click.Path.convert") as mock_convert:
            # Handle multiple path conversions
            mock_convert.side_effect = lambda x, **kw: str(
                test_file if 'file_okay=False' not in str(kw) else output_dir
            )
            result = cli_runner.invoke(cli, [
                "batch",
                str(test_file),
                "--output-dir", str(output_dir),
            ])

        # Check command succeeded and used the mock
        assert result.exit_code == 0
        assert mock_process_asset.called

        # Run with all options
        with mock.patch("click.Path.convert") as mock_convert:
            # Handle multiple path conversions
            mock_convert.side_effect = lambda x, **kw: str(
                test_file if 'file_okay=False' not in str(kw) else output_dir
            )
            result = cli_runner.invoke(cli, [
                "batch",
                str(test_file),
                "--output-dir", str(output_dir),
                "--mode", "transform",
                "--quality", "95",
                "--format", "webp",
            ])

        # Check command succeeded
        assert result.exit_code == 0
        assert mock_process_asset.called

        # Check AssetConfig was created with correct values
        config = mock_process_asset.call_args[0][0]
        assert config.input_path == test_file
        assert config.options.mode == ProcessingMode.TRANSFORM
        assert config.options.quality == 95
        assert config.options.format == "webp"

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

        # Run command
        with mock.patch("click.Path.convert") as mock_convert:
            # Handle multiple path conversions
            mock_convert.side_effect = lambda x, **kw: str(
                test_file if 'file_okay=False' not in str(kw) else output_dir
            )
            # Replace sys.exit with a custom exception to capture exit code
            with mock.patch("sys.exit") as mock_exit:
                cli_runner.invoke(cli, [
                    "batch",
                    str(test_file),
                    "--output-dir", str(output_dir),
                ])
                mock_exit.assert_called_with(1)

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