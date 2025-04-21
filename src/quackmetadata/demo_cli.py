# src/quackmetadata/demo_cli.py
"""
Demo command-line interface for QuackMetadata.

This module provides a CLI for demonstration and testing purposes only.
In production environments, QuackBuddy should be used as the user-facing CLI.
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

# Dogfood FS and Paths to normalize and resolve file paths.
from quackcore.fs.service import get_service

fs = get_service()
from quackcore.logging import get_logger
from quackcore.paths import service as paths

from quackmetadata.commands.metadata_cli import metadata_cli
from quackmetadata.config import get_config
from quackmetadata.plugins.metadata import MetadataPlugin
from quackmetadata.version import __version__, display_version_info

# Get project name from config or use default.
try:
    config = get_config()
    PROJECT_NAME = getattr(config.general, "project_name", "QuackMetadata")
except Exception:
    PROJECT_NAME = "QuackMetadata"  # Fallback to default.

# Create an actual Click group object (not a decorated function).
cli = click.Group(name=PROJECT_NAME.lower())


# Main command decorator.
@cli.command("main")
@click.option(
    "--config",
    "-c",
    help="Path to configuration file",
    type=str,
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
    prog_name=PROJECT_NAME,
    callback=display_version_info,
    message=f"{PROJECT_NAME} version %(version)s",
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
    Demo CLI - For development/testing purposes only.

    In production, use QuackBuddy as the user-facing CLI instead.
    This CLI is included only as a reference implementation and for teaching.
    """
    # Dogfood FS to normalize the config file path, and use Paths to resolve it relative to the project.
    norm_config = fs.normalize_path(config) if config else None
    # Initialize QuackCore CLI environment.
    quack_ctx = init_cli_env(
        config_path=str(norm_config) if norm_config else None,
        verbose=verbose,
        debug=debug,
        quiet=quiet,
        app_name=PROJECT_NAME.lower(),
    )

    # Store the context for use in subcommands.
    ctx.ensure_object(dict)
    ctx.obj.update(
        {
            "quack_ctx": quack_ctx,
            "logger": quack_ctx.logger,
            "config": quack_ctx.config,
        }
    )


@cli.command("extract")
@click.argument(
    "input_file",
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
    input_file: str,
    output: str | None,
    prompt_template: str | None,
    retries: int,
    dry_run: bool,
    verbose: bool,
) -> None:
    """
    Extract metadata from a text file.

    INPUT_FILE can be a local file path or a Google Drive file ID.

    Examples:
        extract myfile.txt
        extract 1abc2defg3hij --dry-run
    """
    logger_ = ctx.obj.get("logger") if ctx.obj else get_logger(__name__)
    logger_.info(f"Extracting metadata from: {input_file}")

    print_info("🕵️ Extracting metadata...")

    # Normalize input, output and prompt_template using QuackCore FS.
    norm_input = fs.normalize_path(input_file)
    norm_output = fs.normalize_path(output) if output else None
    norm_prompt = fs.normalize_path(prompt_template) if prompt_template else None

    # Create and initialize the metadata plugin.
    plugin = MetadataPlugin()
    init_result = plugin.initialize()
    if not init_result.success:
        print_error(
            f"Failed to initialize {PROJECT_NAME.lower()} plugin: {init_result.error}",
            exit_code=1,
        )

    # Process options.
    options: dict[str, object] = {
        "retries": retries,
        "dry_run": dry_run,
        "verbose": verbose,
    }
    if norm_prompt:
        options["prompt_template"] = str(norm_prompt)

    # Process the file using the normalized paths.
    result = plugin.process_file(
        file_path=str(norm_input),
        output_path=str(norm_output) if norm_output else None,
        options=options,
    )

    if not result.success:
        print_error(f"Failed to extract metadata: {result.error}", exit_code=1)

    # Display results.
    content = result.content
    metadata_path = content.get("metadata_path", "")
    card = content.get("card", "")

    print_success("🎉 Metadata extracted successfully!")
    print_info(f"Metadata saved to: {metadata_path}")

    # Print the metadata card.
    print("\n" + card + "\n")

    # If this is a Google Drive file and not a dry run, show upload status.
    if "drive_file_id" in content and not dry_run:
        print_success(
            f"✅ Metadata uploaded to Google Drive with ID: {content['drive_file_id']}"
        )
    elif not dry_run and "original_file_name" in content:
        print_info("📤 Metadata file ready for upload to Google Drive")

    # Ask if the user wants to see the full metadata.
    if not verbose:
        if click.confirm("Would you like to see the full metadata?", default=False):
            # For demo purposes, using json.dumps is acceptable.
            print(json.dumps(content.get("metadata", {}), indent=2))


@cli.command("version")
def version_command():
    """Display version information."""
    # Call the version function directly.
    return display_version_info(None, None, True)


# Add the metadata_cli command group from the main metadata commands.
cli.add_command(metadata_cli)


def main() -> None:
    """
    Entry point for the demo CLI (for development/testing only).

    NOTE: This main function is for testing/development only.
    In production, QuackBuddy should be used instead.
    """
    print(f"📝 {PROJECT_NAME} - Extract structured metadata from documents")
    print("NOTE: This CLI is for development/teaching purposes only.")
    print("")
    cli(obj={})


if __name__ == "__main__":
    main()
