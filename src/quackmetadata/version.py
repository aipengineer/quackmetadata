# src/quackmetadata/version.py
"""
Version information for QuackMetadata.

This module provides version information and related utilities.
"""

import platform
from typing import Any, TypeVar

from rich.console import Console

# Define version here directly
__version__ = "0.1.0"

# Type variable for generic context and parameter types
T = TypeVar("T")


def display_version_info(
    ctx: Any | None = None, param: Any | None = None, value: bool | None = None
) -> None:
    """
    Display detailed version information when --version is used.

    Args:
        ctx: Click context
        param: Click parameter that triggered this callback
        value: Whether the option is provided
    """
    # Early return if value is False or None, or if resilient_parsing is enabled
    if not value or (
        ctx and hasattr(ctx, "resilient_parsing") and ctx.resilient_parsing
    ):
        return

    try:
        # Import here to avoid circular imports
        import quackcore

        console = Console()

        # Get parameter name if available
        param_name = getattr(param, "name", "version") if param else "version"

        console.print(
            "\n[bold green]QuackMetadata[/bold green] - A QuackVerse Automation Tool"
        )
        console.print(f"Version: [cyan]{__version__}[/cyan]")
        console.print(f"QuackCore Version: [cyan]{quackcore.__version__}[/cyan]")
        console.print(f"Python Version: [cyan]{platform.python_version()}[/cyan]")
        console.print(f"Platform: [cyan]{platform.platform()}[/cyan]")

        # Use the param to customize output based on which parameter triggered the callback
        console.print(f"Requested via: [yellow]--{param_name}[/yellow] flag")

        console.print("\nDeveloped as part of the QuackVerse ecosystem")
        console.print(
            "For more information, visit: "
            "[link]https://github.com/yourusername/quacktool[/link]"
        )
    except Exception as e:
        # Gracefully handle errors during version display
        print(f"QuackTool version {__version__}")
        print(f"Error displaying full version info: {e}")

    # Exit the application if context is provided
    if ctx:
        ctx.exit()
