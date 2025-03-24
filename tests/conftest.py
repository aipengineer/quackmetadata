# tests/conftest.py
"""
Test configuration for pytest.

This module contains shared fixtures and configurations for testing.
"""

import os
import tempfile
from pathlib import Path

import pytest


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


@pytest.fixture
def config_dir(temp_dir):
    """Create a temporary config directory with base configuration."""
    config_dir = temp_dir / "config"
    config_dir.mkdir()

    # Create a basic config file
    config_file = config_dir / "quack_config.yaml"
    config_content = """
general:
  project_name: "QuackToolTest"
  environment: "test"
  debug: true

logging:
  level: "DEBUG"
  console: true

custom:
  quacktool:
    default_quality: 85
    default_format: "png"
    output_dir: "./test_output"
    temp_dir: "./test_temp"
    log_level: "DEBUG"
"""
    config_file.write_text(config_content)

    # Create output and temp directories
    (temp_dir / "test_output").mkdir()
    (temp_dir / "test_temp").mkdir()

    # Set environment variable for testing
    os.environ["QUACK_CONFIG"] = str(config_file)

    yield config_dir

    # Clean up
    if "QUACK_CONFIG" in os.environ:
        del os.environ["QUACK_CONFIG"]


@pytest.fixture
def sample_file():
    """Create a sample file for testing."""
    with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as temp:
        temp.write(b"This is a test file for testing.")
        temp_path = temp.name

    yield Path(temp_path)

    # Clean up
    if os.path.exists(temp_path):
        os.unlink(temp_path)


@pytest.fixture
def sample_image(temp_dir):
    """Create a sample image file for testing."""
    # Create a simple image file (just text content for testing)
    image_path = temp_dir / "sample.png"
    with open(image_path, "wb") as f:
        f.write(b"PNG\r\n\x1a\n" + b"\x00" * 100)  # Fake PNG header + content

    yield image_path


@pytest.fixture
def sample_document(temp_dir):
    """Create a sample document file for testing."""
    # Create a simple text document
    doc_path = temp_dir / "sample.txt"
    doc_path.write_text("This is a sample document for testing.")

    yield doc_path
