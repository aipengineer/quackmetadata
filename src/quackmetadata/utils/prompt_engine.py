# src/quackmetadata/utils/prompt_engine.py
"""
Prompt rendering utilities for QuackMetadata.

This module provides functions for loading and rendering Mustache templates
used for generating prompts for LLM interactions.
"""

from collections.abc import Mapping
from pathlib import Path

import pystache

# Import FS service and Paths service
from quackcore.fs.service import get_service

fs = get_service()
from quackcore.logging import get_logger
from quackcore.paths import service as paths

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
        # Normalize and convert path to string.
        template_path_str = str(fs.normalize_path(template_path))

        # Use FS to check if the file exists.
        file_info = fs.get_file_info(template_path_str)
        if not file_info.success or not file_info.exists:
            raise FileNotFoundError(f"Template file not found: {template_path_str}")

        # Read the file using FS.
        read_result = fs.read_text(template_path_str, encoding="utf-8")
        if not read_result.success:
            raise FileNotFoundError(
                f"Failed to read template file: {read_result.error}"
            )

        template = read_result.content
        rendered = pystache.render(template, context)
        logger.debug(f"Successfully rendered template: {template_path_str}")
        return rendered

    except FileNotFoundError as e:
        logger.error(f"Template file not found: {template_path_str}")
        raise e
    except KeyError as e:
        logger.error(f"Missing context key in template: {e}")
        raise ValueError(f"Missing required context key: {e}") from e
    except Exception as e:
        logger.error(f"Error rendering template: {e}")
        raise ValueError(f"Failed to render template: {e}") from e


def get_template_path(template_name: str, category: str = "metadata") -> str:
    """
    Get the path to a template by name and category.

    Args:
        template_name: Name of the template file (without .mustache extension).
        category: Category folder name (default: "metadata").

    Returns:
        A string path to the template file.
    """
    # Try to find templates in package resources.
    try:
        from importlib import resources

        try:
            # First try with quacktool.prompts
            with resources.files(f"quacktool.prompts.{category}") as pkg_path:
                template_path = pkg_path / f"{template_name}.mustache"
                template_path_str = str(template_path)
                file_info = fs.get_file_info(template_path_str)
                if file_info.success and file_info.exists:
                    return template_path_str
        except (ImportError, ModuleNotFoundError):
            # Then try with quackmetadata.prompts
            try:
                with resources.files(f"quackmetadata.prompts.{category}") as pkg_path:
                    template_path = pkg_path / f"{template_name}.mustache"
                    template_path_str = str(template_path)
                    file_info = fs.get_file_info(template_path_str)
                    if file_info.success and file_info.exists:
                        return template_path_str
            except (ImportError, ModuleNotFoundError):
                pass
    except (ImportError, ModuleNotFoundError):
        pass

    # Fallback: Attempt to resolve template path relative to project structure.
    fallback_candidates = [
        f"prompts/{category}/{template_name}.mustache",
        f"./prompts/{category}/{template_name}.mustache",
    ]
    for candidate in fallback_candidates:
        # Use the Paths to resolve candidate paths relative to the project root.
        candidate_path = paths.resolve_project_path(candidate)
        candidate_str = str(candidate_path)
        file_info = fs.get_file_info(candidate_str)
        if file_info.success and file_info.exists:
            return candidate_str

    # As a last resort, manually build a fallback path using the current module's directory.
    current_file = Path(__file__)
    current_dir = current_file.parent
    default_path = str(
        current_dir.parent / "prompts" / category / f"{template_name}.mustache"
    )
    logger.warning(
        f"Could not find template: {template_name}. Using fallback path: {default_path}"
    )
    return default_path
