# src/quackmetadata/utils/rarity.py
"""
Rarity calculation utilities for QuackMetadata.

This module provides functions for determining the rarity of documents
based on content analysis.
"""


def calculate_rarity(summary: str) -> str:
    """
    Calculate the rarity of a document based on its summary.

    Uses heuristics to determine if a document is common, rare, or legendary.

    Args:
        summary: The document summary text

    Returns:
        A rarity classification string (🟢 Common, 🔴 Rare, 🟣 Legendary)
    """
    # Simple heuristics for demonstration purposes
    if not summary:
        return "🟢 Common"

    summary_lower = summary.lower()

    # Legendary criteria
    legendary_terms = ["groundbreaking", "revolutionary", "unprecedented",
                       "extraordinary", "remarkable", "absurd", "paradoxical"]

    if len(summary) > 500 and any(term in summary_lower for term in legendary_terms):
        return "🟣 Legendary"

    # Rare criteria
    rare_terms = ["innovative", "unique", "uncommon", "unusual",
                  "specialized", "technical", "complex"]

    if len(summary) > 300 or any(term in summary_lower for term in rare_terms):
        return "🔴 Rare"

    # Default to common
    return "🟢 Common"