# src/quacktool/demo_cli.py
"""
Demo command-line interface for QuackTool.

This module provides a CLI for demonstration and testing purposes only.
In production environments, QuackBuddy should be used as the user-facing CLI.
"""

import sys
from pathlib import Path

import click
from quackcore.cli import (
    handle_errors,
    init_cli_env,
    print_error,
    print_info,
    print_success,
)

from quacktool.core import process_asset
from quacktool.models import AssetConfig, AssetType, ProcessingMode, ProcessingOptions
from quacktool.version import display_version_info, __version__

# Get enum values for Click choices
# Use this approach to accommodate both the tests and type checking
PROCESSING_MODE_VALUES = list(map(lambda m: m.value, ProcessingMode))
ASSET_TYPE_VALUES = list(map(lambda t: t.value, AssetType))

# Create an actual Click group object (not a decorated function)
# This creates an instance of click.Group that can be used in tests
cli = click.Group(name="quacktool")


# Main command decorator
@cli.command("main")
@click.option(
    "--config",
    "-c",
    help="Path to configuration file",
    type=click.Path(exists=True, dir_okay=False),
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Enable verbose output",
)
@click.option(
    "--debug",
    "-d",
    is_flag=True,
    help="Enable debug mode",
)
@click.option(
    "--quiet",
    "-q",
    is_flag=True,
    help="Suppress non-error output",
)
@click.version_option(
    version=__version__,
    prog_name="QuackTool",
    callback=display_version_info,
    message="QuackTool version %(version)s"
)
@click.pass_context
def main_command(
    ctx: click.Context,
    config: str | None,
    verbose: bool,
    debug: bool,
    quiet: bool,
) -> None:
    """
    QuackTool Demo CLI - For development/testing purposes only.

    In production, use QuackBuddy as the user-facing CLI instead.
    This CLI is included only as a reference implementation and for testing.
    """
    # Initialize QuackCore CLI environment
    quack_ctx = init_cli_env(
        config_path=config,
        verbose=verbose,
        debug=debug,
        quiet=quiet,
        app_name="quacktool",
    )

    # Store the context for use in subcommands
    ctx.obj = {
        "quack_ctx": quack_ctx,
        "logger": quack_ctx.logger,
        "config": quack_ctx.config,
    }


@cli.command("process")
@click.argument(
    "input_file",
    type=click.Path(exists=True, dir_okay=False),
)
@click.option(
    "--output",
    "-o",
    help="Output path",
    type=click.Path(dir_okay=False),
)
@click.option(
    "--mode",
    "-m",
    type=click.Choice(PROCESSING_MODE_VALUES),
    default=ProcessingMode.OPTIMIZE.value,
    help="Processing mode",
)
@click.option(
    "--quality",
    "-q",
    type=click.IntRange(1, 100),
    default=80,
    help="Quality level (1-100)",
)
@click.option(
    "--format",
    "-f",
    help="Output format",
)
@click.option(
    "--width",
    type=int,
    help="Output width",
)
@click.option(
    "--height",
    type=int,
    help="Output height",
)
@click.option(
    "--type",
    "asset_type",
    type=click.Choice(ASSET_TYPE_VALUES),
    help="Asset type (detected automatically if not specified)",
)
@click.pass_context
@handle_errors(exit_code=1)
def process_command(
    ctx: click.Context,
    input_file: str,
    output: str | None,
    mode: str,
    quality: int,
    format: str | None,
    width: int | None,
    height: int | None,
    asset_type: str | None,
) -> None:
    """
    Process a media asset file.

    This command processes the specified media asset according to the
    provided options and saves the result to the output path.

    NOTE: This is a demonstration command for testing only. In production,
    QuackBuddy should be used as the user-facing CLI.
    """
    logger = ctx.obj["logger"]
    logger.info(f"Processing file: {input_file}")

    # Create dimensions tuple if both width and height are provided
    dimensions = None
    if width is not None and height is not None:
        dimensions = (width, height)

    # Create processing options
    options = ProcessingOptions(
        mode=ProcessingMode(mode),
        quality=quality,
        dimensions=dimensions,
        format=format,
    )

    # Create asset configuration
    asset_config = AssetConfig(
        input_path=Path(input_file),
        output_path=Path(output) if output else None,
        asset_type=AssetType(asset_type) if asset_type else AssetType.OTHER,
        options=options,
    )

    # Process the asset - make sure this call to process_asset is testable
    result = process_asset(asset_config)

    if result.success:
        print_success(f"Successfully processed {input_file}")
        print_info(f"Output: {result.output_path}")

        # Print metrics if available
        if result.metrics:
            print_info("Metrics:")
            for key, value in result.metrics.items():
                print_info(f"  {key}: {value}")

        print_info(f"Processing time: {result.duration_ms}ms")
    else:
        print_error(f"Failed to process {input_file}: {result.error}", exit_code=1)


@cli.command("batch")
@click.argument(
    "input_files",
    nargs=-1,
    type=click.Path(exists=True, dir_okay=False),
)
@click.option(
    "--output-dir",
    "-o",
    help="Output directory",
    type=click.Path(file_okay=False),
    required=True,
)
@click.option(
    "--mode",
    "-m",
    type=click.Choice(PROCESSING_MODE_VALUES),
    default=ProcessingMode.OPTIMIZE.value,
    help="Processing mode",
)
@click.option(
    "--quality",
    "-q",
    type=click.IntRange(1, 100),
    default=80,
    help="Quality level (1-100)",
)
@click.option(
    "--format",
    "-f",
    help="Output format",
)
@click.pass_context
@handle_errors(exit_code=1)
def batch_command(
    ctx: click.Context,
    input_files: list[str],
    output_dir: str,
    mode: str,
    quality: int,
    format: str | None,
) -> None:
    """
    Process multiple files in batch mode.

    This command processes multiple files with the same settings and
    saves the results to the specified output directory.

    NOTE: This is a demonstration command for testing only. In production,
    QuackBuddy should be used as the user-facing CLI.
    """
    logger = ctx.obj["logger"]
    logger.info(f"Batch processing {len(input_files)} files")

    # Create output directory if it doesn't exist
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Create processing options
    options = ProcessingOptions(
        mode=ProcessingMode(mode),
        quality=quality,
        format=format,
    )

    # Process each file
    success_count = 0
    failure_count = 0

    for input_file in input_files:
        input_path = Path(input_file)
        output_file = (
            output_path
            / f"{input_path.stem}.{format or input_path.suffix.lstrip('.')}"
        )

        asset_config = AssetConfig(
            input_path=input_path,
            output_path=output_file,
            options=options,
        )

        result = process_asset(asset_config)

        if result.success:
            success_count += 1
            print_info(f"Processed: {input_file} -> {result.output_path}")
        else:
            failure_count += 1
            print_error(f"Failed to process {input_file}: {result.error}")

    # Print summary
    print_info(
        f"Batch processing completed: {success_count} succeeded, {failure_count} failed"
    )
    if failure_count > 0:
        sys.exit(1)


# Add a dedicated version command that calls display_version_info directly
@cli.command("version")
def version_command():
    """Display version information."""
    # Call the version function directly, don't rely on callback
    # This ensures the mock can track the call
    return display_version_info(None, None, True)


def main() -> None:
    """
    Entry point for the demo CLI (for development/testing only).

    NOTE: This main function is for testing/development only.
    In production, QuackBuddy should be used instead.
    """
    print("NOTE: This CLI is for development/testing purposes only.")
    print("In production, QuackBuddy should be used as the user-facing CLI.")
    print("")
    cli(obj={})


if __name__ == "__main__":
    main()