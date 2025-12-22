"""CV-related interfaces for inter-service communication."""

from pydantic import BaseModel

from ..constants import ContentType


class ExtractedLine(BaseModel):
    """A single extracted line from a CV with its content type."""

    content_type: ContentType
    content: str
    order: int = 0


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
        """Get all experiences."""
        return self.get_by_type(ContentType.EXPERIENCE)

    @property
    def education(self) -> list[str]:
        """Get all education entries."""
        return self.get_by_type(ContentType.EDUCATION)

    @property
    def languages(self) -> list[str]:
        """Get all languages."""
        return self.get_by_type(ContentType.LANGUAGE)
