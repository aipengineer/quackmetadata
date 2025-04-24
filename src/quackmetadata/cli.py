# src/quackmetadata/cli.py
"""
Command-line interface for QuackMetadata.

This module provides a streamlined CLI for QuackMetadata, leveraging
QuackCore's CLI utilities for consistent behavior across QuackTools.
"""

import click
from quackcore.cli import (
    handle_errors,
    init_cli_env,
    print_error,
    print_info,
    print_success,
)
from quackcore.logging import get_logger

from quackmetadata.tool import run

logger = get_logger(__name__)


@click.command()
@click.argument("input_file", type=str)
@click.option(
    "--output", "-o",
    help="Output path for metadata JSON file",
    type=str,
)
@click.option(
    "--prompt-template",
    help="Path to custom prompt template (.mustache file)",
    type=str,
)
@click.option(
    "--retries",
    type=int,
    default=3,
    help="Number of retries for LLM calls",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Don't upload metadata to Google Drive, just extract and print",
)
@click.option(
    "--verbose", "-v",
    is_flag=True,
    help="Print detailed processing information",
)
@click.option(
    "--config", "-c",
    help="Path to configuration file",
    type=str,
)
@click.option(
    "--debug", "-d",
    is_flag=True,
    help="Enable debug mode",
)
@handle_errors(exit_code=1)
def cli(
        input_file: str,
        output: str = None,
        prompt_template: str = None,
        retries: int = 3,
        dry_run: bool = False,
        verbose: bool = False,
        config: str = None,
        debug: bool = False,
) -> None:
    """
    Extract metadata from a text file.

    INPUT_FILE can be a local file path or a Google Drive file ID.

    Examples:
        quackmetadata myfile.txt
        quackmetadata 1abc2defg3hij --dry-run
    """
    # Initialize QuackCore CLI environment
    ctx = init_cli_env(
        config_path=config,
        verbose=verbose,
        debug=debug,
        app_name="quackmetadata",
    )

    logger = ctx.logger
    logger.info(f"Processing file: {input_file}")

    print_info("🕵️ Extracting metadata...")

    # Prepare options
    options = {
        "retries": retries,
        "dry_run": dry_run,
        "verbose": verbose,
    }

    if prompt_template:
        options["prompt_template"] = prompt_template

    # Process the file
    result = run(input_file, output, options)

    if not result["success"]:
        print_error(f"Failed to extract metadata: {result['error']}", exit_code=1)

    # Display results
    print_success("🎉 Metadata extracted successfully!")

    if "metadata_path" in result:
        print_info(f"Metadata saved to: {result['metadata_path']}")

    # Print the metadata card
    if "card" in result:
        print("\n" + result["card"] + "\n")

    # If this is a Google Drive file and not a dry run, show upload status
    if "drive_file_id" in result and not dry_run:
        print_success(
            f"✅ Metadata uploaded to Google Drive with ID: {result['drive_file_id']}"
        )
    elif not dry_run and "original_file_name" in result:
        print_info("📤 Metadata file ready for upload to Google Drive")

    # Ask if the user wants to see the full metadata
    if not verbose and click.confirm("Would you like to see the full metadata?",
                                     default=False):
        import json
        print(json.dumps(result.get("metadata", {}), indent=2))


def main() -> None:
    """Entry point for the command-line interface."""
    cli()


if __name__ == "__main__":
    main()
