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
from quackcore.logging import get_logger
from quackcore.paths import service as paths

fs = get_service()
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
        # Check if template_path is a string representation of a PathResult
        if isinstance(template_path, str) and template_path.startswith("success="):
            logger.warning(
                "Detected template_path as string representation of PathResult")
            # Extract the actual path using regex
            import re
            path_match = re.search(r"path=PosixPath\('([^']+)'\)", template_path)
            if path_match:
                template_path_str = path_match.group(1)
                logger.debug(f"Extracted path: {template_path_str}")
            else:
                # Use as is if we can't extract the path
                template_path_str = template_path
        else:
            # Normalize and convert path to string.
            template_path_str = str(template_path)

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

        # Provide a default template when the file is not found
        default_template = """
        # Metadata Extraction Task

        You are a metadata extraction assistant. Please analyze the content below and extract metadata in a structured format.

        ## Content to Analyze:

        {{content}}

        ## Extraction Instructions:

        Please extract the following metadata in JSON format:

        ```json
        {
          "title": "A descriptive title for the content",
          "domain": "The subject domain or category",
          "tone": "The writing tone (formal, informal, academic, etc.)",
          "summary": "A brief summary of the content (2-3 sentences)",
          "keywords": ["keyword1", "keyword2", "keyword3", "etc"],
          "rarity": "common|uncommon|rare|legendary"
        }
        ```

        Please ensure the JSON is well-formed with no syntax errors.
        """

        logger.info("Using default template as fallback")
        try:
            return pystache.render(default_template, context)
        except Exception as render_error:
            raise ValueError(
                f"Failed to render fallback template: {render_error}") from e

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
                # Convert PosixPath to string before using it
                template_path_str = str(template_path)
                file_info = fs.get_file_info(template_path_str)
                if file_info.success and file_info.exists:
                    return template_path_str
        except (ImportError, ModuleNotFoundError, TypeError):
            # Then try with quackmetadata.prompts
            try:
                with resources.files(f"quackmetadata.prompts.{category}") as pkg_path:
                    template_path = pkg_path / f"{template_name}.mustache"
                    # Convert PosixPath to string before using it
                    template_path_str = str(template_path)
                    file_info = fs.get_file_info(template_path_str)
                    if file_info.success and file_info.exists:
                        return template_path_str
            except (ImportError, ModuleNotFoundError, TypeError):
                pass
    except (ImportError, ModuleNotFoundError, TypeError):
        pass

    # Fallback: Attempt to resolve template path relative to project structure.
    fallback_candidates = [
        f"prompts/{category}/{template_name}.mustache",
        f"./prompts/{category}/{template_name}.mustache",
    ]
    for candidate in fallback_candidates:
        # Use the Paths to resolve candidate paths relative to the project root.
        candidate_path = paths.resolve_project_path(candidate)
        # Convert the result to string
        candidate_str = str(candidate_path.path) if hasattr(candidate_path,
                                                            "path") else str(
            candidate_path)
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

    # Normalize the default_path to ensure it's clean
    # This is important because this path will be passed to render_prompt
    try:
        path_result = fs.normalize_path(default_path)
        if path_result.success:
            default_path = str(path_result.path)
    except Exception as e:
        logger.warning(f"Could not normalize default path: {e}")

    return default_path
