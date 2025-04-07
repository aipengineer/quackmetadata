# src/quackmetadata/utils/llm_wrapper.py
"""
LLM wrapper utilities for QuackMetadata.

This module provides wrappers for LLM clients to handle import errors
and ensure graceful fallbacks.
"""

import logging
import os
from typing import Any

from quackcore.integrations.llms import (
    MockLLMClient,
)

logger = logging.getLogger(__name__)


def get_llm_integration(force_mock: bool = False) -> Any:
    """
    Get an LLM integration with fallback to MockLLMClient.

    This function tries to create a real LLM integration, but falls back
    to a MockLLMClient if the real integration fails.

    Args:
        force_mock: Whether to force the use of MockLLMClient

    Returns:
        Any: An LLM integration instance
    """
    # If forcing mock, return it directly
    if force_mock:
        logger.info("Forcing use of MockLLMClient as requested")
        return create_mock_llm(), True

    # First, check if we have any API keys in the environment
    has_openai_key = "OPENAI_API_KEY" in os.environ
    has_anthropic_key = "ANTHROPIC_API_KEY" in os.environ

    if not has_openai_key and not has_anthropic_key:
        logger.warning("No LLM API keys found in environment, using MockLLMClient")
        return create_mock_llm(), True

    # Try to create a real LLM integration
    try:
        # Import within the function to handle import errors
        try:
            from quackcore.integrations.llms import create_integration
        except ImportError as e:
            logger.error(f"Failed to import create_integration: {e}")
            return create_mock_llm(), True

        # Try to create the integration
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
        MockLLMClient: A mock LLM client
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


def check_llm_availability() -> tuple[bool, str]:
    """
    Check if real LLM services are available.

    Returns:
        tuple[bool, str]: A tuple containing a boolean indicating
                         if real LLMs are available and a message
    """
    # Check for installed packages
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

    # Check for API keys
    has_openai_key = "OPENAI_API_KEY" in os.environ
    has_anthropic_key = "ANTHROPIC_API_KEY" in os.environ

    # Build status message
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

    # Build result
    if available_providers:
        return True, f"Available LLM providers: {', '.join(available_providers)}"
    else:
        return False, f"No LLM providers available. Issues: {', '.join(missing_components)}"


def ensure_llm_packages() -> bool:
    """
    Ensure LLM packages are installed.

    Returns:
        bool: True if at least one package is installed
    """
    # Try importing packages directly
    openai_available = False
    anthropic_available = False

    try:
        import openai
        openai_available = True
    except ImportError:
        logger.warning(
            "OpenAI package not available - some functionality may be limited")

    try:
        import anthropic
        anthropic_available = True
    except ImportError:
        logger.warning(
            "Anthropic package not available - some functionality may be limited")

    return openai_available or anthropic_available