"""
Prompt rendering utilities for QuackMetadata.

This module provides functions for loading and rendering Mustache templates
used for generating prompts for LLM interactions.
"""

from collections.abc import Mapping
import pystache
from quackcore.logging import get_logger

# Import FS service and helpers
from quackcore.fs import service as fs

logger = get_logger(__name__)


def render_prompt(template_path: str, context: Mapping[str, str]) -> str:
    """
    Render a Mustache template with the provided context.

    Args:
        template_path: Path to the Mustache template file.
        context: Dictionary of context variables to render in the template.

    Returns:
        The rendered prompt string.

    Raises:
        FileNotFoundError: If the template file doesn't exist.
        ValueError: If the template is invalid or context is missing required values.
    """
    try:
        file_info = fs.get_file_info(template_path)
        if not (file_info.success and file_info.exists):
            raise FileNotFoundError(f"Template file not found: {template_path}")

        read_result = fs.read_text(template_path, encoding="utf-8")
        if not read_result.success:
            raise FileNotFoundError(f"Failed to read template file: {read_result.error}")

        template = read_result.content
        rendered = pystache.render(template, context)
        logger.debug(f"Successfully rendered template: {template_path}")
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


def get_template_path(template_name: str, category: str = "metadata"):
    """
    Get the path to a template by name and category.

    Args:
        template_name: Name of the template file (without .mustache extension).
        category: Category folder name (default: "metadata").

    Returns:
        A Path-like object pointing to the template file.
    """
    from importlib import resources
    try:
        with resources.files(f"quacktool.prompts.{category}") as path:
            template_path = path / f"{template_name}.mustache"
            # Use fs.get_file_info to check for existence.
            if fs.get_file_info(str(template_path)).success and fs.get_file_info(str(template_path)).exists:
                return template_path
    except (ImportError, ModuleNotFoundError):
        pass

    # Fallback: construct the path using fs.join_path
    # Here we still use Path to compute the base directory from __file__
    from pathlib import Path
    base_dir = Path(__file__).parent.parent
    fallback = fs.join_path(str(base_dir), "prompts", category, f"{template_name}.mustache")
    # Optionally cast fallback to Path, if needed:
    return fallback
