"""Shared Pydantic schemas for inter-service communication."""

from .common import ServiceHealth
from .cv import (
    CVData,
    EducationData,
    ExperienceData,
    ExtractedLine,
    PersonalInfoData,
    SocialLinkData,
)

__all__ = [
    "ExtractedLine",
    "CVData",
    "ExperienceData",
    "EducationData",
    "PersonalInfoData",
    "SocialLinkData",
    "ServiceHealth",
]
