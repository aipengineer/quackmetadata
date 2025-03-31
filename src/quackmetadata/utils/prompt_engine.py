# src/quackmetadata/utils/prompt_engine.py
"""
Prompt rendering utilities for QuackMetadata.

This module provides functions for loading and rendering Mustache templates
used for generating prompts for LLM interactions.
"""

from collections.abc import Mapping
from pathlib import Path
import pystache
import logging

logger = logging.getLogger(__name__)


def render_prompt(template_path: str | Path, context: Mapping[str, str]) -> str:
    """
    Render a Mustache template with the provided context.

    Args:
        template_path: Path to the Mustache template file
        context: Dictionary of context variables to render in the template

    Returns:
        The rendered prompt string

    Raises:
        FileNotFoundError: If the template file doesn't exist
        ValueError: If the template is invalid or context is missing required values
    """
    try:
        path = Path(template_path)
        if not path.exists():
            raise FileNotFoundError(f"Template file not found: {template_path}")

        with open(path, "r", encoding="utf-8") as f:
            template = f.read()

        rendered = pystache.render(template, context)
        logger.debug(f"Successfully rendered template: {path.name}")
        return rendered

    except FileNotFoundError as e:
        logger.error(f"Template file not found: {template_path}")
        raise e
    except KeyError as e:
        logger.error(f"Missing context key in template: {e}")
        raise ValueError(f"Missing required context key: {e}") from e
    except Exception as e:
        logger.error(f"Error rendering template: {e}")
        raise ValueError(f"Failed to render template: {e}") from e


def get_template_path(template_name: str, category: str = "metadata") -> Path:
    """
    Get the path to a template by name and category.

    Args:
        template_name: Name of the template file (without .mustache extension)
        category: Category folder name (default: "metadata")

    Returns:
        Path object pointing to the template file
    """
    # Resolve relative to the quackmetadata package
    from importlib import resources
    try:
        # Try to use the modern API first
        with resources.files(f"quacktool.prompts.{category}") as path:
            template_path = path / f"{template_name}.mustache"
            if template_path.exists():
                return template_path
    except (ImportError, ModuleNotFoundError):
        # Fall back to manually resolving the path
        base_dir = Path(__file__).parent.parent
        return base_dir / "prompts" / category / f"{template_name}.mustache"

    # If we get here, try one more fallback approach
    base_dir = Path(__file__).parent.parent
    return base_dir / "prompts" / category / f"{template_name}.mustache"