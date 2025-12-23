"""Content type definitions for CV and job offer extraction."""

from enum import Enum


class ContentType(str, Enum):
    """Types of content that can be extracted from CVs and job offers."""

    # CV-specific types
    SUMMARY = "summary"
    EXPERIENCE = "experience"
    EDUCATION = "education"
    CERTIFICATION = "certification"
    SKILL_HARD = "skill_hard"
    SKILL_SOFT = "skill_soft"
    LANGUAGE = "language"
    INTEREST = "interest"
    CONTACT = "contact"
    OTHER = "other"

    # Job offer-specific types (for future use)
    JOB_TITLE = "job_title"
    JOB_DESCRIPTION = "job_description"
    REQUIRED_SKILL = "required_skill"
    PREFERRED_SKILL = "preferred_skill"
    SALARY = "salary"
    LOCATION = "location"
    CONTRACT_TYPE = "contract_type"
    COMPANY = "company"
