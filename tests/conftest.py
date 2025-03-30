# tests/conftest.py
"""
Test fixtures and configuration for QuackTool tests.
"""

import os
import tempfile
from pathlib import Path
from typing import Generator

import pytest
from quackcore.config.models import QuackConfig
from quackcore.integrations.core.results import IntegrationResult
from quackcore.plugins.protocols import QuackPluginProtocol

from quacktool.config import QuackToolConfig
from quacktool.models import AssetConfig, ProcessingOptions, ProcessingResult


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Provide a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as temp_dir_path:
        yield Path(temp_dir_path)


@pytest.fixture
def test_file(temp_dir: Path) -> Path:
    """Create a temporary test file for testing."""
    test_file_path = temp_dir / "test_file.txt"
    with open(test_file_path, "w") as f:
        f.write("Test content for QuackTool unit tests")
    return test_file_path


@pytest.fixture
def test_image(temp_dir: Path) -> Path:
    """Create a fake image file for testing."""
    test_image_path = temp_dir / "test_image.jpg"
    with open(test_image_path, "wb") as f:
        # Write a minimal valid JPG header (not a real image, just for detection)
        f.write(b"\xff\xd8\xff\xe0\x00\x10\x4a\x46\x49\x46\x00")
        f.write(b"\x01\x01\x01\x00\x48\x00\x48\x00\x00\xff\xdb")
        f.write(b"\x00\x43\x00\x08\x06\x06\x07\x06\x05\x08\x07")
    return test_image_path


@pytest.fixture
def test_config() -> QuackConfig:
    """Create a test configuration."""
    config = QuackConfig(
        general={
            "project_name": "QuackToolTest",
            "environment": "test",
            "debug": True,
        },
        paths={
            "base_dir": "./",
            "output_dir": "./output",
            "temp_dir": "./temp",
        },
        custom={
            "quacktool": QuackToolConfig(
                default_quality=85,
                default_format="webp",
                temp_dir="./temp_test",
                output_dir="./output_test",
                log_level="DEBUG",
            ).model_dump()
        },
    )
    return config


@pytest.fixture
def test_asset_config(test_file: Path) -> AssetConfig:
    """Create a test asset configuration."""
    return AssetConfig(
        input_path=test_file,
        options=ProcessingOptions(quality=90),
    )


@pytest.fixture
def mock_quackcore_plugin() -> QuackPluginProtocol:
    """Create a mock QuackCore plugin for testing."""
    class MockPlugin(QuackPluginProtocol):
        def __init__(self) -> None:
            self._initialized = True

        @property
        def name(self) -> str:
            return "MockPlugin"

        @property
        def version(self) -> str:
            return "0.1.0"

        def initialize(self) -> IntegrationResult:
            return IntegrationResult.success_result("Initialized")

        def is_available(self) -> bool:
            return self._initialized

        def process_file(
                self,
                file_path: str,
                output_path: str | None = None,
                options: dict[str, object] | None = None,
        ) -> IntegrationResult:
            # Use the output_path if provided
            content = output_path if output_path else "mock_processed_output.txt"

            # Use options if provided to customize the message
            quality = options.get("quality", "default") if options else "default"
            message = f"Mock processing successful with quality: {quality}"

            return IntegrationResult.success_result(
                content=content,
                message=message,
            )

    return MockPlugin()


@pytest.fixture
def patch_env_for_test() -> Generator[None, None, None]:
    """Set environment variables for testing."""
    # Ensure tests run in test mode
    os.environ["PYTEST_CURRENT_TEST"] = "yes"
    yield
    # Clean up
    if "PYTEST_CURRENT_TEST" in os.environ:
        del os.environ["PYTEST_CURRENT_TEST"]


@pytest.fixture
def mock_processing_result() -> ProcessingResult:
    """Create a mock processing result."""
    return ProcessingResult(
        success=True,
        output_path=Path("output/processed.txt"),
        metrics={"size_ratio": 0.85, "process_time": 42},
        duration_ms=100,
    )