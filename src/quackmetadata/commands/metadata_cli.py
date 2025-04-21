# src/quackmetadata/commands/metadata_cli.py
"""
Command-line interface for the QuackMetadata tool.

This module provides a CLI for the QuackMetadata tool, allowing users
to extract metadata from text files using LLMs and interact with Google Drive.
"""

import json

import click
from quackcore.cli import (
    handle_errors,
    init_cli_env,
    print_error,
    print_info,
    print_success,
)
from quackcore.fs import service as fs  # Use QuackCore FS for all file operations
from quackcore.logging import get_logger

from quackmetadata.plugins.metadata import MetadataPlugin

# Create a logger for this module
logger = get_logger(__name__)


# Create the metadata command group
@click.group(name="metadata")
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
@click.pass_context
def metadata_cli(
    ctx: click.Context,
    config: str | None,
    verbose: bool,
    debug: bool,
) -> None:
    """
    QuackMetadata - Extract structured metadata from text files.

    This tool can download files from Google Drive, extract metadata using LLMs,
    and upload the results back to Google Drive.
    """
    # Normalize the config file path using quackcore.fs if provided
    config_path = fs.normalize_path(config) if config else None
    # Initialize QuackCore CLI environment
    quack_ctx = init_cli_env(
        config_path=str(config_path) if config_path else None,
        verbose=verbose,
        debug=debug,
        app_name="quackmetadata",
    )

    # Store the context for use in subcommands
    ctx.ensure_object(dict)
    ctx.obj.update(
        {
            "quack_ctx": quack_ctx,
            "logger": quack_ctx.logger,
            "config": quack_ctx.config,
            "verbose": verbose,
        }
    )


@metadata_cli.command("extract")
@click.argument(
    "input",
    type=str,
)
@click.option(
    "--output",
    "-o",
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
    "--verbose",
    is_flag=True,
    help="Print detailed processing information",
)
@click.pass_context
@handle_errors(exit_code=1)
def extract_command(
    ctx: click.Context,
    input: str,
    output: str | None,
    prompt_template: str | None,
    retries: int,
    dry_run: bool,
    verbose: bool,
) -> None:
    """
    Extract metadata from a text file.

    INPUT can be a local file path or a Google Drive file ID.

    Examples:
        quackmetadata metadata extract myfile.txt
        quackmetadata metadata extract 1abc2defg3hij --dry-run
    """
    # Use the logger from the context or the module logger
    ctx_logger = ctx.obj.get("logger", logger) if ctx.obj else logger
    ctx_logger.info(f"Extracting metadata from: {input}")

    print_info("🕵️ Extracting metadata...")

    # Normalize the input file path using quackcore.fs (this ensures consistent path style)
    normalized_input = fs.normalize_path(input)
    # If an output path was provided, normalize it as well
    normalized_output = fs.normalize_path(output) if output else None

    # Process optional prompt template file using quackcore.fs
    options: dict[str, object] = {
        "retries": retries,
        "dry_run": dry_run,
        "verbose": verbose,
    }
    if prompt_template:
        normalized_template = fs.normalize_path(prompt_template)
        # Verify that the prompt template file exists
        prompt_info = fs.get_file_info(normalized_template)
        if not (prompt_info.success and prompt_info.exists):
            print_error(
                f"Prompt template file not found: {normalized_template}",
                exit_code=1,
            )
        options["prompt_template"] = str(normalized_template)

    # Create and initialize the metadata plugin
    plugin = MetadataPlugin()
    init_result = plugin.initialize()
    if not init_result.success:
        print_error(
            f"Failed to initialize metadata plugin: {init_result.error}",
            exit_code=1,
        )

    # Process the file using the normalized paths (all file handling is done via quackcore.fs)
    result = plugin.process_file(
        file_path=str(normalized_input),
        output_path=str(normalized_output) if normalized_output else None,
        options=options,
    )
    if not result.success:
        print_error(f"Failed to extract metadata: {result.error}", exit_code=1)

    # Display results
    content = result.content
    metadata_path = content.get("metadata_path", "")
    card = content.get("card", "")

    print_success("🎉 Metadata extracted successfully!")
    print_info(f"Metadata saved to: {metadata_path}")

    # Print the metadata card
    print("\n" + card + "\n")

    # If this is a Google Drive file and not a dry run, show upload status
    if "drive_file_id" in content and not dry_run:
        print_success(
            f"✅ Metadata uploaded to Google Drive with ID: {content['drive_file_id']}"
        )
    elif not dry_run and "original_file_name" in content:
        print_info("📤 Metadata file ready for upload to Google Drive")

    # Ask if the user wants to see the full metadata
    if not verbose:
        if click.confirm("Would you like to see the full metadata?", default=False):
            metadata = content.get("metadata", {})
            print(json.dumps(metadata, indent=2))


def main() -> None:
    """Entry point for the metadata CLI."""
    metadata_cli(obj={})


if __name__ == "__main__":
    main()
