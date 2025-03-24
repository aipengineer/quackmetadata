#!/usr/bin/env python
# examples/headless_api_usage.py
"""
Example demonstrating how QuackBuddy would use QuackTool's headless API.

This example shows the recommended way to integrate QuackTool within
the QuackVerse ecosystem, particularly from QuackBuddy.
"""

import logging
import time
from pathlib import Path

# Import directly from the package (the proper headless way)
from quacktool import AssetConfig, ProcessingOptions, process_asset
from quacktool.models import ProcessingMode


def example_direct_api_usage(input_path: Path) -> None:
    """
    Example of using QuackTool directly via its public API.

    Args:
        input_path: Path to the input file
    """
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("quackbuddy-example")

    logger.info(f"Processing {input_path} using QuackTool's headless API")

    # Set up options programmatically (as QuackBuddy would)
    options = ProcessingOptions(
        mode=ProcessingMode.OPTIMIZE,
        quality=85,
        format="webp",
    )

    # Create asset configuration
    config = AssetConfig(
        input_path=input_path,
        output_path=Path(f"./output/{input_path.stem}_processed.webp"),
        options=options,
    )

    # Process the asset using the headless API
    logger.info("Calling QuackTool's process_asset...")
    start_time = time.time()
    result = process_asset(config)
    elapsed = time.time() - start_time

    # Handle the result (as QuackBuddy would)
    if result.success:
        logger.info(f"Success! Output saved to: {result.output_path}")
        logger.info(
            f"Processing time: {elapsed:.3f}s (API reported: {result.duration_ms}ms)"
        )
        logger.info(f"Metrics: {result.metrics}")
    else:
        logger.error(f"Processing failed: {result.error}")


def example_plugin_usage(input_path: Path) -> None:
    """
    Example of using QuackTool via the QuackCore plugin system.

    Args:
        input_path: Path to the input file
    """
    from quackcore.plugins import registry

    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("quackbuddy-example")

    logger.info(f"Processing {input_path} using QuackTool via plugin")

    # Get the QuackTool plugin from the registry
    # This is how QuackBuddy would discover and use the plugin
    plugin = registry.get_plugin("QuackTool")

    if not plugin or not plugin.is_available():
        logger.error("QuackTool plugin not available")
        return

    # Process the file using the plugin interface
    result = plugin.process_file(
        file_path=str(input_path),
        output_path=f"./output/{input_path.stem}_processed.webp",
        options={
            "mode": "optimize",
            "quality": 85,
            "format": "webp",
        },
    )

    # Handle the result (as QuackBuddy would)
    if result.success:
        logger.info(f"Success! Output saved to: {result.content}")
    else:
        logger.error(f"Processing failed: {result.error}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="QuackTool Headless API Example")
    parser.add_argument("file", help="File to process")
    parser.add_argument(
        "--method",
        choices=["api", "plugin"],
        default="api",
        help="Method to use (direct API or plugin)",
    )

    args = parser.parse_args()
    input_file = Path(args.file)

    if not input_file.exists():
        print(f"Error: File not found: {input_file}")
        exit(1)

    if args.method == "api":
        example_direct_api_usage(input_file)
    else:
        example_plugin_usage(input_file)
