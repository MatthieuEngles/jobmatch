"""CV-related interfaces for inter-service communication."""

from pydantic import BaseModel

from ..constants import ContentType


class ExperienceData(BaseModel):
    """Structured data for a professional experience entry."""

    entity: str  # Company/organization name
    dates: str  # Date range or single date (e.g., "2020-2023", "Jan 2020 - Present")
    position: str  # Job title/role
    description: str  # Description of responsibilities/achievements


class EducationData(BaseModel):
    """Structured data for an education entry."""

    entity: str  # School/university/institution name
    dates: str  # Date range or graduation year
    position: str  # Degree/diploma/certification name
    description: str  # Field of study, honors, or additional details


class PersonalInfoData(BaseModel):
    """Structured data for personal information extracted from CV."""

    first_name: str = ""
    last_name: str = ""
    email: str = ""
    phone: str = ""
    location: str = ""


class SocialLinkData(BaseModel):
    """Structured data for a social link extracted from CV."""

    link_type: str  # linkedin, github, portfolio, blog, medium, other
    url: str


class ExtractedLine(BaseModel):
    """A single extracted line from a CV with its content type."""

    content_type: ContentType
    content: str  # Simple string for most types, JSON string for experience/education
    order: int = 0

    # Structured data fields (optional, only for experience/education)
    entity: str | None = None  # Company/school name
    dates: str | None = None  # Date range
    position: str | None = None  # Job title/diploma
    description: str | None = None  # Description

    # Structured data fields for personal_info
    first_name: str | None = None
    last_name: str | None = None
    email: str | None = None
    phone: str | None = None
    location: str | None = None

    # Structured data fields for social_link
    link_type: str | None = None
    url: str | None = None

    def is_structured(self) -> bool:
        """Check if this line has structured data (experience/education)."""
        return self.entity is not None or self.position is not None

    def get_experience_data(self) -> ExperienceData | None:
        """Get structured experience data if available."""
        if self.content_type != ContentType.EXPERIENCE or not self.is_structured():
            return None
        return ExperienceData(
            entity=self.entity or "",
            dates=self.dates or "",
            position=self.position or "",
            description=self.description or "",
        )

    def get_education_data(self) -> EducationData | None:
        """Get structured education data if available."""
        if self.content_type != ContentType.EDUCATION or not self.is_structured():
            return None
        return EducationData(
            entity=self.entity or "",
            dates=self.dates or "",
            position=self.position or "",
            description=self.description or "",
        )


class CVData(BaseModel):
    """Complete CV data extracted from a document."""

    success: bool
    extracted_lines: list[ExtractedLine] = []
    raw_text: str | None = None
    error: str | None = None

    def get_by_type(self, content_type: ContentType) -> list[str]:
        """Get all content items of a specific type."""
        return [line.content for line in self.extracted_lines if line.content_type == content_type]

    @property
    def skills_hard(self) -> list[str]:
        """Get all hard skills."""
        return self.get_by_type(ContentType.SKILL_HARD)

    @property
    def skills_soft(self) -> list[str]:
        """Get all soft skills."""
        return self.get_by_type(ContentType.SKILL_SOFT)

    @property
    def experiences(self) -> list[str]:
        """Get all experiences as strings (legacy)."""
        return self.get_by_type(ContentType.EXPERIENCE)

    @property
    def experiences_structured(self) -> list[ExperienceData]:
        """Get all experiences as structured data objects."""
        result = []
        for line in self.extracted_lines:
            if line.content_type == ContentType.EXPERIENCE:
                exp_data = line.get_experience_data()
                if exp_data:
                    result.append(exp_data)
        return result

    @property
    def education(self) -> list[str]:
        """Get all education entries as strings (legacy)."""
        return self.get_by_type(ContentType.EDUCATION)

    @property
    def education_structured(self) -> list[EducationData]:
        """Get all education entries as structured data objects."""
        result = []
        for line in self.extracted_lines:
            if line.content_type == ContentType.EDUCATION:
                edu_data = line.get_education_data()
                if edu_data:
                    result.append(edu_data)
        return result

    @property
    def languages(self) -> list[str]:
        """Get all languages."""
        return self.get_by_type(ContentType.LANGUAGE)
