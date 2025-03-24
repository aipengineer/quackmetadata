# tests/test_cli.py
"""
Tests for the command-line interface.

This module contains tests for the QuackTool CLI functionality.
"""

import os
from pathlib import Path
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from quacktool.demo_cli import cli


@pytest.fixture
def runner():
    """Create a CLI runner for testing."""
    return CliRunner()


def test_cli_version(runner):
    """Test the version command directly instead of the --version flag."""
    # For testing the version command, patch the display_version_info function
    with patch("quacktool.version.display_version_info") as mock_display:
        # Ensure the function doesn't exit
        mock_display.return_value = None

        # Use the isolated_filesystem to avoid log file issues
        with runner.isolated_filesystem():
            # Use the dedicated version command
            result = runner.invoke(cli, ["version"])

            # Check the result
            assert result.exit_code == 0, f"Version command failed with output: {result.output}"
            assert mock_display.called, "display_version_info was not called"


@patch("quacktool.core.process_asset")
def test_process_command(mock_process, runner, sample_file):
    """Test the process command."""
    # Mock the process_asset function to return a successful result
    from quacktool.models import ProcessingResult

    mock_process.return_value = ProcessingResult(
        success=True,
        output_path=Path("/mock/output.png"),
        metrics={"input_size": 100, "output_size": 80, "size_ratio": 0.8},
        duration_ms=150,
    )

    # Run the CLI command in isolated filesystem to avoid log file issues
    with runner.isolated_filesystem():
        # Add environment variables to avoid filesystem issues
        custom_env = {**os.environ, "QUACK_CONFIG": ""}

        result = runner.invoke(
            cli,
            [
                "process",
                str(sample_file),
                "--output",
                "output.png",
                "--quality",
                "85",
                "--format",
                "png",
                "--mode",
                "optimize",
            ],
            catch_exceptions=False,
            env=custom_env,
            obj={},  # Ensure obj is provided
        )

        # Verify the command executed successfully
        assert result.exit_code == 0, f"CLI command failed with output: {result.output}"
        assert mock_process.called, "process_asset was not called"

        # Check the output
        assert "Successfully processed" in result.output
        assert "output.png" in result.output


@patch("quacktool.core.process_asset")
def test_process_command_error(mock_process, runner, sample_file):
    """Test the process command with an error."""
    # Mock the process_asset function to return an error result
    from quacktool.models import ProcessingResult

    mock_process.return_value = ProcessingResult(
        success=False,
        error="Processing failed",
        duration_ms=50,
    )

    # Ensure our mock works with direct patching
    with patch("quacktool.demo_cli.process_asset",
               return_value=mock_process.return_value):
        # Run the CLI command in isolated filesystem
        with runner.isolated_filesystem():
            # Add environment variables to avoid filesystem issues
            custom_env = {**os.environ, "QUACK_CONFIG": ""}

            result = runner.invoke(
                cli,
                [
                    "process",
                    str(sample_file),
                    "--mode",
                    "optimize",
                ],
                catch_exceptions=False,
                env=custom_env,
                obj={},  # Ensure obj is provided
            )

    # Now check that the error message is in the output
    assert result.exit_code == 1, "Expected error exit code"
    assert "Processing failed" in result.output or "Failed to process" in result.output


@patch("quacktool.core.process_asset")
def test_batch_command(mock_process, runner, temp_dir, sample_file):
    """Test the batch command."""
    # Create a second sample file
    second_file = temp_dir / "second.txt"
    second_file.write_text("Second test file")

    # Mock the process_asset function to return a successful result
    from quacktool.models import ProcessingResult

    mock_process.return_value = ProcessingResult(
        success=True,
        output_path=Path("/mock/output.png"),
        metrics={"input_size": 100, "output_size": 80, "size_ratio": 0.8},
        duration_ms=150,
    )

    # Create output directory
    output_dir = temp_dir / "batch_output"
    output_dir.mkdir(exist_ok=True)

    # Use direct patching of the function in demo_cli.py
    with patch("quacktool.demo_cli.process_asset",
               return_value=mock_process.return_value):
        # Run the CLI command in isolated filesystem
        with runner.isolated_filesystem():
            # Add environment variables to avoid filesystem issues
            custom_env = {**os.environ, "QUACK_CONFIG": ""}

            result = runner.invoke(
                cli,
                [
                    "batch",
                    str(sample_file),
                    str(second_file),
                    "--output-dir",
                    str(output_dir),
                    "--format",
                    "png",
                    "--mode",
                    "optimize",
                ],
                catch_exceptions=False,
                env=custom_env,
                obj={},  # Ensure obj is provided
            )

    # Verify the command executed successfully
    assert result.exit_code == 0, f"CLI command failed with output: {result.output}"

    # Check the output
    assert "processed" in result.output.lower()