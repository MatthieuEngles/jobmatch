"""Shared Pydantic schemas for inter-service communication."""

from .common import ServiceHealth
from .cv import CVData, EducationData, ExperienceData, ExtractedLine

__all__ = [
    "ExtractedLine",
    "CVData",
    "ExperienceData",
    "EducationData",
    "ServiceHealth",
]
