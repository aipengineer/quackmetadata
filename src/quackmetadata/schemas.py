# src/quackmetadata/schemas.py
"""
Metadata schema definitions for QuackMetadata.

This module contains Pydantic models that define the structure of metadata
extracted from documents by the QuackMetadata tool.
"""

from pydantic import BaseModel, Field


class AuthorProfile(BaseModel):
    """
    Profile information about the author of a document.

    This is generated based on analysis of the document content
    and represents a fictional profile of the likely author.
    """

    name: str = Field(description="Author's name")
    profession: str = Field(description="Author's profession or occupation")
    writing_style: str = Field(description="Characteristic writing style")
    possible_age_range: str = Field(description="Estimated age range of the author")
    location_guess: str = Field(
        description="Possible geographic location of the author"
    )


class Metadata(BaseModel):
    """
    Structured metadata extracted from document content.

    This model defines the complete set of metadata that can be
    extracted from a document by the QuackMetadata tool.
    """

    title: str = Field(description="Title of the document")
    summary: str = Field(description="Brief summary of the document content")
    author_style: str = Field(
        description="Style of writing (e.g., concise, academic, poetic)"
    )
    tone: str = Field(description="Emotional tone (e.g., serious, humorous, critical)")
    language: str = Field(description="Primary language of the document")
    domain: str = Field(description="Subject domain (e.g., politics, philosophy, food)")
    estimated_date: str | None = Field(
        default=None, description="Estimated date of creation if detectable"
    )
    rarity: str = Field(
        description="Rarity classification (🟢 Common, 🔴 Rare, 🟣 Legendary)"
    )
    author_profile: AuthorProfile = Field(
        description="Generated profile of the likely author"
    )
