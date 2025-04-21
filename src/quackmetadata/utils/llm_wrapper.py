# src/quackmetadata/utils/llm_wrapper.py
"""
LLM wrapper utilities for QuackMetadata.

This module provides wrappers for LLM clients to handle import errors
and ensure graceful fallbacks. It now also leverages QuackCore FS and
QuackCore Paths for configuration and file resolution when needed.
"""

import os
from typing import Any, Tuple

# Import QuackCore FS and Paths.
from quackcore.fs import service as fs
from quackcore.integrations.llms import MockLLMClient
from quackcore.logging import get_logger
from quackcore.paths import service as paths

logger = get_logger(__name__)


def get_llm_integration(force_mock: bool = False) -> Tuple[Any, bool]:
    """
    Get an LLM integration with fallback to MockLLMClient.

    This function first checks environment variables for API keys.
    If none are found, it attempts to load a configuration file (e.g. "config/quack_config.yaml")
    using QuackCore Paths and FS to set the keys from configuration.
    Finally, if keys are still missing or force_mock is True, it falls back to a MockLLMClient.

    Args:
        force_mock: Whether to force the use of MockLLMClient

    Returns:
        A tuple containing:
          - The LLM integration instance.
          - A boolean indicating whether the mock was used.
    """
    # If forcing mock, return immediately.
    if force_mock:
        logger.info("Forcing use of MockLLMClient as requested")
        return create_mock_llm(), True

    # Check if we have any API keys in the environment.
    has_openai_key = "OPENAI_API_KEY" in os.environ
    has_anthropic_key = "ANTHROPIC_API_KEY" in os.environ

    if not (has_openai_key or has_anthropic_key):
        logger.warning(
            "No LLM API keys found in environment. Attempting to load from configuration."
        )
        # Use QuackCore Paths to resolve the configuration file relative to the project root.
        config_file = paths.resolve_project_path("config/quack_config.yaml")
        config_info = fs.get_file_info(str(config_file))
        if config_info.success and config_info.exists:
            config_result = fs.read_yaml(str(config_file))
            if config_result.success:
                config_data = config_result.data
                # Attempt to load API keys from configuration and set them in the environment.
                openai_key = (
                    config_data.get("integrations", {})
                    .get("llm", {})
                    .get("openai", {})
                    .get("api_key")
                )
                anthropic_key = (
                    config_data.get("integrations", {})
                    .get("llm", {})
                    .get("anthropic", {})
                    .get("api_key")
                )
                if openai_key:
                    os.environ["OPENAI_API_KEY"] = openai_key
                    has_openai_key = True
                if anthropic_key:
                    os.environ["ANTHROPIC_API_KEY"] = anthropic_key
                    has_anthropic_key = True
            else:
                logger.error(
                    f"Could not read configuration from {config_file}: {config_result.error}"
                )

    if not (has_openai_key or has_anthropic_key):
        logger.warning(
            "No LLM API keys available after configuration lookup, using MockLLMClient"
        )
        return create_mock_llm(), True

    # Try to create a real LLM integration.
    try:
        try:
            from quackcore.integrations.llms import create_integration
        except ImportError as e:
            logger.error(f"Failed to import create_integration: {e}")
            return create_mock_llm(), True

        llm_service = create_integration()
        init_result = llm_service.initialize()
        if not init_result.success:
            logger.error(f"Failed to initialize LLM service: {init_result.error}")
            return create_mock_llm(), True

        return llm_service, False

    except Exception as e:
        logger.exception(f"Error creating LLM integration: {e}")
        return create_mock_llm(), True


def create_mock_llm() -> MockLLMClient:
    """
    Create a MockLLMClient with reasonable responses for testing.

    Returns:
        MockLLMClient: A mock LLM client.
    """
    mock_responses = [
        """```json
        {
            "title": "Mock Document",
            "summary": "This is a mock summary generated because the LLM service is unavailable.",
            "author_style": "N/A (MockLLM)",
            "tone": "Neutral",
            "language": "English",
            "domain": "Testing",
            "estimated_date": null,
            "rarity": "🟢 Common",
            "author_profile": {
                "name": "Mock Author",
                "profession": "Test Writer",
                "writing_style": "Automated",
                "possible_age_range": "N/A",
                "location_guess": "Virtual Environment"
            }
        }
        ```"""
    ]
    return MockLLMClient(script=mock_responses)


def check_llm_availability() -> Tuple[bool, str]:
    """
    Check if real LLM services are available.

    Returns:
        A tuple containing:
         - A boolean indicating if real LLMs are available.
         - A status message.
    """
    openai_available = False
    anthropic_available = False

    try:
        import openai

        openai_available = True
    except ImportError:
        pass

    try:
        import anthropic

        anthropic_available = True
    except ImportError:
        pass

    has_openai_key = "OPENAI_API_KEY" in os.environ
    has_anthropic_key = "ANTHROPIC_API_KEY" in os.environ

    available_providers = []
    missing_components = []

    if openai_available and has_openai_key:
        available_providers.append("OpenAI")
    else:
        if not openai_available:
            missing_components.append("OpenAI package not installed")
        elif not has_openai_key:
            missing_components.append("OPENAI_API_KEY not set")

    if anthropic_available and has_anthropic_key:
        available_providers.append("Anthropic")
    else:
        if not anthropic_available:
            missing_components.append("Anthropic package not installed")
        elif not has_anthropic_key:
            missing_components.append("ANTHROPIC_API_KEY not set")

    if available_providers:
        return True, f"Available LLM providers: {', '.join(available_providers)}"
    else:
        return (
            False,
            f"No LLM providers available. Issues: {', '.join(missing_components)}",
        )


def ensure_llm_packages() -> bool:
    """
    Ensure LLM packages are installed.

    Returns:
        True if at least one package is installed.
    """
    openai_available = False
    anthropic_available = False

    try:
        import openai

        openai_available = True
    except ImportError:
        logger.warning(
            "OpenAI package not available - some functionality may be limited"
        )

    try:
        import anthropic

        anthropic_available = True
    except ImportError:
        logger.warning(
            "Anthropic package not available - some functionality may be limited"
        )

    return openai_available or anthropic_available
