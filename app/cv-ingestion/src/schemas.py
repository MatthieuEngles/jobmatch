"""Pydantic schemas for API request/response models."""

from enum import Enum

from pydantic import BaseModel, Field


class ContentType(str, Enum):
    """Types of content that can be extracted from a CV."""

    SUMMARY = "summary"
    EXPERIENCE = "experience"
    EDUCATION = "education"
    SKILL_HARD = "skill_hard"
    SKILL_SOFT = "skill_soft"
    LANGUAGE = "language"
    CERTIFICATION = "certification"
    INTEREST = "interest"
    OTHER = "other"


class ExtractedLine(BaseModel):
    """A single extracted line from the CV."""

    content_type: ContentType
    content: str
    order: int = 0


class ExtractionResponse(BaseModel):
    """Response from the extraction endpoint."""

    success: bool
    extracted_lines: list[ExtractedLine] = Field(default_factory=list)
    raw_text: str | None = None
    error: str | None = None


class ExtractionRequest(BaseModel):
    """Request body for extraction (when sending file URL instead of upload)."""

    file_url: str | None = None


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    service: str
