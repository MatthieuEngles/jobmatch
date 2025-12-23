"""Pydantic schemas for API request/response models.

Re-exports shared interfaces and adds service-specific schemas.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

# Re-export shared interfaces
from shared.constants import ContentType
from shared.interfaces import ExtractedLine

__all__ = [
    "ContentType",
    "ExtractedLine",
    "ExtractionResponse",
    "ExtractionRequest",
    "HealthResponse",
    "TaskSubmitResponse",
    "TaskStatusResponse",
    "LLMConfigRequest",
]


class LLMConfigRequest(BaseModel):
    """Optional LLM configuration that overrides environment settings."""

    llm_endpoint: str | None = Field(None, description="Custom LLM API endpoint")
    llm_model: str | None = Field(None, description="Model name (e.g., gpt-4o)")
    llm_api_key: str | None = Field(None, description="API key for the LLM")


class ExtractionResponse(BaseModel):
    """Response from the extraction endpoint (sync mode)."""

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


class TaskSubmitResponse(BaseModel):
    """Response when submitting a CV for async processing."""

    task_id: str
    status: Literal["pending"] = "pending"
    message: str = "CV submitted for processing"


class TaskStatusResponse(BaseModel):
    """Response for task status check."""

    task_id: str
    status: Literal["pending", "processing", "completed", "failed"]
    created_at: datetime
    updated_at: datetime
    # Present only when completed
    success: bool | None = None
    extracted_lines: list[ExtractedLine] | None = None
    raw_text: str | None = None
    # Present only when failed
    error: str | None = None
