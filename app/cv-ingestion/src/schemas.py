"""Pydantic schemas for API request/response models.

Re-exports shared interfaces and adds service-specific schemas.
"""

from pydantic import BaseModel, Field

# Re-export shared interfaces
from shared.constants import ContentType
from shared.interfaces import ExtractedLine

__all__ = ["ContentType", "ExtractedLine", "ExtractionResponse", "ExtractionRequest", "HealthResponse"]


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
