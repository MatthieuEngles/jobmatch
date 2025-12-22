"""Shared Pydantic schemas for inter-service communication."""

from .common import ServiceHealth
from .cv import CVData, ExtractedLine

__all__ = ["ExtractedLine", "CVData", "ServiceHealth"]
