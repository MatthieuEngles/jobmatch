from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models

# Choices for CV extraction status
EXTRACTION_STATUS_CHOICES = [
    ("pending", "En attente"),
    ("processing", "En cours"),
    ("completed", "Termine"),
    ("failed", "Echec"),
]

# Choices for subscription tiers
SUBSCRIPTION_TIER_CHOICES = [
    ("free", "Gratuit"),
    ("basic", "Basic"),
    ("premium", "Premium"),
    ("headhunter", "Head Hunter"),
    ("enterprise", "Entreprise"),
]

# Choices for ExtractedLine content type
CONTENT_TYPE_CHOICES = [
    ("summary", "Resume / Accroche"),
    ("experience", "Experience professionnelle"),
    ("education", "Formation"),
    ("skill_hard", "Competence technique"),
    ("skill_soft", "Soft skill"),
    ("language", "Langue"),
    ("certification", "Certification"),
    ("interest", "Centre d'interet"),
    ("other", "Autre"),
]


class User(AbstractUser):
    """Custom user model for JobMatch."""

    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=20, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Subscription tier
    subscription_tier = models.CharField(
        max_length=20,
        choices=SUBSCRIPTION_TIER_CHOICES,
        default="free",
    )

    # Job search preferences
    is_job_seeker = models.BooleanField(default=True)
    availability = models.CharField(
        max_length=50,
        choices=[
            ("immediate", "Immédiate"),
            ("1_month", "1 mois"),
            ("3_months", "3 mois"),
            ("other", "Autre"),
        ],
        blank=True,
    )
    salary_min = models.IntegerField(null=True, blank=True)
    salary_max = models.IntegerField(null=True, blank=True)
    remote_preference = models.CharField(
        max_length=20,
        choices=[
            ("onsite", "Sur site"),
            ("hybrid", "Hybride"),
            ("remote", "Full remote"),
            ("any", "Peu importe"),
        ],
        default="any",
    )

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    class Meta:
        verbose_name = "Utilisateur"
        verbose_name_plural = "Utilisateurs"

    def __str__(self):
        return self.email

    # Methods for consolidated profile (used by matching service)
    def get_consolidated_profile(self):
        """
        Return all active extracted lines, grouped by content_type.
        Used for matching and consolidated profile display.
        Returns: dict {content_type: [ExtractedLine, ...]}
        """
        lines = self.extracted_lines.filter(is_active=True).select_related("source_cv")
        result = {}
        for line in lines:
            if line.content_type not in result:
                result[line.content_type] = []
            result[line.content_type].append(line)
        return result

    def get_lines_by_cv(self, cv_id):
        """
        Return all extracted lines from a specific CV.
        Used for display by source.
        Returns: QuerySet[ExtractedLine]
        """
        return self.extracted_lines.filter(source_cv_id=cv_id)

    def get_active_lines_count(self):
        """
        Return the count of active lines.
        Used for profile completion indicators.
        Returns: int
        """
        return self.extracted_lines.filter(is_active=True).count()


class CV(models.Model):
    """Represents an uploaded CV file."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="cvs",
    )
    file = models.FileField(upload_to="cvs/")
    original_filename = models.CharField(max_length=255)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    extraction_status = models.CharField(
        max_length=20,
        choices=EXTRACTION_STATUS_CHOICES,
        default="pending",
    )
    extracted_at = models.DateTimeField(null=True, blank=True)
    task_id = models.CharField(max_length=100, blank=True, null=True, db_index=True)

    class Meta:
        verbose_name = "CV"
        verbose_name_plural = "CVs"
        ordering = ["-uploaded_at"]

    def __str__(self):
        return f"{self.original_filename} ({self.user.email})"

    def get_extracted_lines(self):
        """Return all lines extracted from this CV."""
        return self.extracted_lines.all()

    def get_active_lines(self):
        """Return only active lines from this CV."""
        return self.extracted_lines.filter(is_active=True)


class CoverLetter(models.Model):
    """Represents an uploaded cover letter file."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="cover_letters",
    )
    file = models.FileField(upload_to="cover_letters/")
    original_filename = models.CharField(max_length=255)
    title = models.CharField(max_length=255, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Lettre de motivation"
        verbose_name_plural = "Lettres de motivation"
        ordering = ["-uploaded_at"]

    def __str__(self):
        return f"{self.title or self.original_filename} ({self.user.email})"


class ExtractedLine(models.Model):
    """
    Central model. Each line represents a unit of information extracted from a CV.
    Granularity by type:
    - experience: 1 position = 1 line (with structured data: entity, dates, position, description)
    - education: 1 diploma = 1 line (with structured data: entity, dates, position, description)
    - skill_hard/skill_soft: 1 skill = 1 line
    - language: 1 language = 1 line
    - certification: 1 certification = 1 line
    - summary: 1 paragraph = 1 line
    - interest: 1 interest = 1 line
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="extracted_lines",
    )
    source_cv = models.ForeignKey(
        CV,
        on_delete=models.CASCADE,
        related_name="extracted_lines",
    )
    content_type = models.CharField(
        max_length=20,
        choices=CONTENT_TYPE_CHOICES,
        db_index=True,
    )
    content = models.TextField()

    # Structured fields for experience/education
    entity = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Company/school/organization name",
    )
    dates = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Date range (e.g., '2020-2023', 'Jan 2020 - Present')",
    )
    position = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Job title or diploma name",
    )
    description = models.TextField(
        blank=True,
        null=True,
        help_text="Description of responsibilities/achievements or field of study",
    )

    is_active = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    modified_by_user = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Ligne extraite"
        verbose_name_plural = "Lignes extraites"
        ordering = ["content_type", "order", "-created_at"]
        indexes = [
            models.Index(fields=["user", "content_type"]),
            models.Index(fields=["user", "is_active"]),
            models.Index(fields=["source_cv"]),
        ]

    def __str__(self):
        return f"{self.get_content_type_display()}: {self.content[:50]}..."

    def toggle_active(self):
        """Toggle the is_active status."""
        self.is_active = not self.is_active
        self.save(update_fields=["is_active", "modified_at"])

    def mark_as_modified(self):
        """Mark the line as modified by user. Call when content is manually edited."""
        self.modified_by_user = True
        self.save(update_fields=["modified_by_user", "modified_at"])

    def is_structured(self):
        """Check if this line has structured data (experience/education)."""
        return self.entity is not None or self.position is not None

    def get_display_title(self):
        """Get a display title for the line (position for experience/education, content for others)."""
        if self.position:
            return self.position
        return self.content[:50] + "..." if len(self.content) > 50 else self.content

    def get_display_subtitle(self):
        """Get a display subtitle (entity + dates for experience/education)."""
        if self.entity and self.dates:
            return f"{self.entity} ({self.dates})"
        elif self.entity:
            return self.entity
        elif self.dates:
            return self.dates
        return None


class UserLLMConfig(models.Model):
    """
    Custom LLM configuration for power users.
    Allows users to use their own LLM API instead of the server default.
    """

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="llm_config",
    )
    is_enabled = models.BooleanField(
        default=False,
        help_text="Enable custom LLM configuration",
    )
    llm_endpoint = models.URLField(
        blank=True,
        help_text="Custom LLM API endpoint (e.g., https://api.openai.com/v1)",
    )
    llm_model = models.CharField(
        max_length=100,
        blank=True,
        help_text="Model name (e.g., gpt-4o, claude-3-sonnet)",
    )
    llm_api_key = models.CharField(
        max_length=255,
        blank=True,
        help_text="API key (stored encrypted in production)",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Configuration LLM utilisateur"
        verbose_name_plural = "Configurations LLM utilisateurs"

    def __str__(self):
        return f"LLM Config for {self.user.email}"

    def get_config_dict(self):
        """Return config as dict for cv-ingestion service."""
        if not self.is_enabled:
            return None
        return {
            "endpoint": self.llm_endpoint,
            "model": self.llm_model,
            "api_key": self.llm_api_key,
        }
