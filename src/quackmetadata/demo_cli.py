# src/quackmetadata/demo_cli.py
"""
Demo command-line interface for QuackMetadata.

This module provides a CLI for demonstration and testing purposes only.
In production environments, QuackBuddy should be used as the user-facing CLI.
"""

import click
from quackcore.cli import (
    handle_errors,
    init_cli_env,
    print_error,
    print_info,
    print_success,
)

from quackmetadata.plugins.metadata import MetadataPlugin
from quackmetadata.version import display_version_info, __version__
from quackmetadata.commands.metadata_cli import metadata_cli

# Create an actual Click group object (not a decorated function)
# This creates an instance of click.Group that can be used in tests
cli = click.Group(name="quackmetadata")


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
    prog_name="QuackMetadata",
    callback=display_version_info,
    message="QuackMetadata version %(version)s"
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
    QuackMetadata Demo CLI - For development/testing purposes only.

    In production, use QuackBuddy as the user-facing CLI instead.
    This CLI is included only as a reference implementation and for teaching.
    """
    # Initialize QuackCore CLI environment
    quack_ctx = init_cli_env(
        config_path=config,
        verbose=verbose,
        debug=debug,
        quiet=quiet,
        app_name="quackmetadata",
    )

    # Store the context for use in subcommands
    ctx.obj = {
        "quack_ctx": quack_ctx,
        "logger": quack_ctx.logger,
        "config": quack_ctx.config,
    }


@cli.command("extract")
@click.argument(
    "input_file",
    type=str,
)
@click.option(
    "--output",
    "-o",
    help="Output path for metadata JSON file",
    type=click.Path(dir_okay=False),
)
@click.option(
    "--prompt-template",
    help="Path to custom prompt template (.mustache file)",
    type=click.Path(exists=True, dir_okay=False),
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
        quackmetadata extract myfile.txt
        quackmetadata extract 1abc2defg3hij --dry-run
    """
    logger = ctx.obj["logger"]
    logger.info(f"Extracting metadata from: {input_file}")

    print_info("🕵️ Extracting metadata...")

    # Create and initialize the metadata plugin
    plugin = MetadataPlugin()
    init_result = plugin.initialize()

    if not init_result.success:
        print_error(f"Failed to initialize metadata plugin: {init_result.error}",
                    exit_code=1)

    # Process options
    options = {
        "retries": retries,
        "dry_run": dry_run,
        "verbose": verbose
    }

    if prompt_template:
        options["prompt_template"] = prompt_template

    # Process the file
    result = plugin.process_file(
        file_path=input_file,
        output_path=output,
        options=options
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
            f"✅ Metadata uploaded to Google Drive with ID: {content['drive_file_id']}")
    elif not dry_run and "original_file_name" in content:
        print_info("📤 Metadata file ready for upload to Google Drive")

    # Ask if the user wants to see the full metadata
    if not verbose:
        if click.confirm("Would you like to see the full metadata?", default=False):
            metadata = content.get("metadata", {})
            import json
            print(json.dumps(metadata, indent=2))


# Add a dedicated version command that calls display_version_info directly
@cli.command("version")
def version_command():
    """Display version information."""
    # Call the version function directly, don't rely on callback
    # This ensures the mock can track the call
    return display_version_info(None, None, True)


# Add the metadata_cli command group
cli.add_command(metadata_cli)


def main() -> None:
    """
    Entry point for the demo CLI (for development/testing only).

    NOTE: This main function is for testing/development only.
    In production, QuackBuddy should be used instead.
    """
    print("📝 QuackMetadata - Extract structured metadata from documents")
    print("NOTE: This CLI is for development/teaching purposes only.")
    print("")
    cli(obj={})


if __name__ == "__main__":
    main()