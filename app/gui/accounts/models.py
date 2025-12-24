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

# Choices for seniority level
SENIORITY_CHOICES = [
    ("intern", "Stagiaire"),
    ("apprentice", "Alternant"),
    ("junior", "Junior (0-2 ans)"),
    ("confirmed", "Confirme (2-5 ans)"),
    ("senior", "Senior (5-10 ans)"),
    ("expert", "Expert / Lead (10+ ans)"),
]

# Choices for availability
AVAILABILITY_CHOICES = [
    ("immediate", "Immediate"),
    ("1_month", "1 mois"),
    ("2_months", "2 mois"),
    ("3_months", "3 mois"),
    ("more", "Plus de 3 mois"),
]

# Choices for contract type
CONTRACT_TYPE_CHOICES = [
    ("cdi", "CDI"),
    ("cdd", "CDD"),
    ("freelance", "Freelance"),
    ("alternance", "Alternance"),
]

# Choices for remote preference
REMOTE_PREFERENCE_CHOICES = [
    ("onsite", "Sur site"),
    ("hybrid", "Hybride"),
    ("remote", "Full remote"),
    ("any", "Peu importe"),
]

# Choices for geographic mobility
MOBILITY_CHOICES = [
    ("city", "Ville uniquement"),
    ("region", "Region"),
    ("france", "France entiere"),
    ("europe", "Europe"),
    ("international", "International"),
]

# Choices for social link type
SOCIAL_LINK_TYPE_CHOICES = [
    ("linkedin", "LinkedIn"),
    ("github", "GitHub"),
    ("portfolio", "Portfolio"),
    ("blog", "Blog personnel"),
    ("medium", "Medium"),
    ("other", "Autre"),
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
    ("personal_info", "Informations personnelles"),
    ("social_link", "Lien social"),
    ("other", "Autre"),
]

# Choices for chat conversation status
CONVERSATION_STATUS_CHOICES = [
    ("active", "Active"),
    ("completed", "Terminee"),
    ("abandoned", "Abandonnee"),
]

# Choices for chat message role
MESSAGE_ROLE_CHOICES = [
    ("user", "Utilisateur"),
    ("assistant", "Assistant"),
    ("system", "Systeme"),
]

# Choices for chat message status
MESSAGE_STATUS_CHOICES = [
    ("pending", "En attente"),
    ("processing", "En cours"),
    ("completed", "Terminee"),
    ("failed", "Echec"),
]

# Choices for coaching type
COACHING_TYPE_CHOICES = [
    ("star", "Succes professionnel (STAR)"),
    ("pitch", "Pitch (30s et 3min)"),
]


class User(AbstractUser):
    """Custom user model for JobMatch."""

    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=20, blank=True)
    location = models.CharField(
        max_length=100,
        blank=True,
        help_text="City/location",
    )
    photo = models.ImageField(
        upload_to="profile_photos/",
        blank=True,
        null=True,
        help_text="Profile photo",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Subscription tier
    subscription_tier = models.CharField(
        max_length=20,
        choices=SUBSCRIPTION_TIER_CHOICES,
        default="free",
    )

    # Professional info
    seniority = models.CharField(
        max_length=20,
        choices=SENIORITY_CHOICES,
        blank=True,
    )

    # Job search preferences
    is_job_seeker = models.BooleanField(default=True)
    availability = models.CharField(
        max_length=20,
        choices=AVAILABILITY_CHOICES,
        blank=True,
    )
    contract_types = models.JSONField(
        default=list,
        blank=True,
        help_text="List of desired contract types (cdi, cdd, freelance, alternance)",
    )
    salary_min = models.IntegerField(
        null=True,
        blank=True,
        help_text="Minimum salary in k€ gross/year",
    )
    salary_max = models.IntegerField(
        null=True,
        blank=True,
        help_text="Maximum salary in k€ gross/year",
    )
    remote_preference = models.CharField(
        max_length=20,
        choices=REMOTE_PREFERENCE_CHOICES,
        default="any",
    )
    mobility = models.CharField(
        max_length=20,
        choices=MOBILITY_CHOICES,
        blank=True,
    )
    personal_notes = models.TextField(
        blank=True,
        help_text="Personal notes or additional information",
    )

    # AI Assistant preferences
    ai_autonomy_level = models.PositiveSmallIntegerField(
        default=3,
        help_text="AI autonomy level (1=Guided, 2=Assisted, 3=Collaborative, 4=Proactive, 5=Autonomous)",
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


class SocialLink(models.Model):
    """Social/professional links for a user."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="social_links",
    )
    link_type = models.CharField(
        max_length=20,
        choices=SOCIAL_LINK_TYPE_CHOICES,
    )
    url = models.URLField()
    order = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = "Lien social"
        verbose_name_plural = "Liens sociaux"
        ordering = ["order", "link_type"]

    def __str__(self):
        return f"{self.get_link_type_display()}: {self.url}"


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
    - personal_info: personal data (first_name, last_name, email, phone, location)
    - social_link: 1 link = 1 line (link_type, url)
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

    # Structured fields for personal_info
    first_name = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="First name from CV",
    )
    last_name = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Last name from CV",
    )
    email = models.EmailField(
        blank=True,
        null=True,
        help_text="Email from CV",
    )
    phone = models.CharField(
        max_length=30,
        blank=True,
        null=True,
        help_text="Phone number from CV",
    )
    location = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        help_text="Location/city from CV",
    )

    # Structured fields for social_link
    link_type = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        help_text="Type of social link (linkedin, github, portfolio, blog, medium, other)",
    )
    url = models.URLField(
        blank=True,
        null=True,
        help_text="URL of the social link",
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


class CandidateProfile(models.Model):
    """
    Candidate profile for targeting specific job types.
    Each profile can have different items (experiences, skills, etc.) selected.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="candidate_profiles",
    )
    title = models.CharField(
        max_length=100,
        help_text="Profile title (e.g., 'Data Scientist', 'Tech Lead')",
    )
    description = models.TextField(
        blank=True,
        help_text="Optional description of the target position",
    )
    is_default = models.BooleanField(
        default=False,
        help_text="Default profile selected on login",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Profil de candidature"
        verbose_name_plural = "Profils de candidature"
        ordering = ["-is_default", "title"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "title"],
                name="unique_profile_title_per_user",
            )
        ]

    def __str__(self):
        return f"{self.title} ({self.user.email})"

    def save(self, *args, **kwargs):
        # Ensure only one default profile per user
        if self.is_default:
            CandidateProfile.objects.filter(user=self.user, is_default=True).exclude(pk=self.pk).update(
                is_default=False
            )
        super().save(*args, **kwargs)

    def get_selected_lines(self):
        """Return all ExtractedLines selected for this profile."""
        selected_ids = self.item_selections.filter(is_selected=True).values_list("extracted_line_id", flat=True)
        return ExtractedLine.objects.filter(id__in=selected_ids)

    def get_selected_lines_by_type(self, content_type):
        """Return selected ExtractedLines of a specific type."""
        selected_ids = self.item_selections.filter(
            is_selected=True,
            extracted_line__content_type=content_type,
        ).values_list("extracted_line_id", flat=True)
        return ExtractedLine.objects.filter(id__in=selected_ids)

    def is_line_selected(self, extracted_line_id):
        """Check if a specific line is selected in this profile."""
        selection = self.item_selections.filter(extracted_line_id=extracted_line_id).first()
        # If no selection exists, default to True (selected)
        return selection.is_selected if selection else True

    def set_line_selection(self, extracted_line_id, is_selected):
        """Set selection status for a specific line."""
        selection, created = self.item_selections.get_or_create(
            extracted_line_id=extracted_line_id,
            defaults={"is_selected": is_selected},
        )
        if not created and selection.is_selected != is_selected:
            selection.is_selected = is_selected
            selection.save(update_fields=["is_selected"])
        return selection

    def initialize_all_selected(self):
        """Initialize all user's extracted lines as selected for this profile."""
        lines = ExtractedLine.objects.filter(user=self.user, is_active=True)
        for line in lines:
            self.item_selections.get_or_create(
                extracted_line=line,
                defaults={"is_selected": True},
            )

    @classmethod
    def get_or_create_default(cls, user):
        """Get or create the default 'Complet' profile for a user."""
        profile, created = cls.objects.get_or_create(
            user=user,
            title="Complet",
            defaults={
                "description": "Profil complet avec tous les elements",
                "is_default": True,
            },
        )
        if created:
            profile.initialize_all_selected()
        return profile, created


class ProfileItemSelection(models.Model):
    """
    Selection status of an ExtractedLine within a CandidateProfile.
    Tracks which items are selected/deselected for each profile.
    """

    profile = models.ForeignKey(
        CandidateProfile,
        on_delete=models.CASCADE,
        related_name="item_selections",
    )
    extracted_line = models.ForeignKey(
        ExtractedLine,
        on_delete=models.CASCADE,
        related_name="profile_selections",
    )
    is_selected = models.BooleanField(
        default=True,
        help_text="Whether this item is included in the profile",
    )

    class Meta:
        verbose_name = "Selection d'element"
        verbose_name_plural = "Selections d'elements"
        constraints = [
            models.UniqueConstraint(
                fields=["profile", "extracted_line"],
                name="unique_selection_per_profile_line",
            )
        ]

    def __str__(self):
        status = "selected" if self.is_selected else "deselected"
        return f"{self.profile.title}: {self.extracted_line.content[:30]}... ({status})"


class ChatConversation(models.Model):
    """
    Chat conversation for AI-assisted coaching.
    Supports STAR method (professional success) and Pitch creation.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="chat_conversations",
    )
    title = models.CharField(
        max_length=255,
        blank=True,
        help_text="Auto-generated title based on conversation content",
    )
    coaching_type = models.CharField(
        max_length=20,
        choices=COACHING_TYPE_CHOICES,
        default="star",
        help_text="Type of coaching (STAR for success, pitch for 30s/3min pitch)",
    )
    status = models.CharField(
        max_length=20,
        choices=CONVERSATION_STATUS_CHOICES,
        default="active",
    )
    context_snapshot = models.JSONField(
        default=dict,
        help_text="Snapshot of user context at conversation start (profile, experiences, etc.)",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Conversation chat"
        verbose_name_plural = "Conversations chat"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Conversation {self.id} - {self.user.email} ({self.status})"

    def get_messages(self):
        """Return all messages in this conversation ordered by creation time."""
        return self.messages.all().order_by("created_at")

    def get_last_message(self):
        """Return the last message in the conversation."""
        return self.messages.order_by("-created_at").first()

    def add_user_message(self, content):
        """Add a user message to the conversation."""
        return ChatMessage.objects.create(
            conversation=self,
            role="user",
            content=content,
            status="completed",
        )

    def add_assistant_message(self, content, task_id=None, status="completed"):
        """Add an assistant message to the conversation."""
        return ChatMessage.objects.create(
            conversation=self,
            role="assistant",
            content=content,
            task_id=task_id,
            status=status,
        )


class ChatMessage(models.Model):
    """
    Individual message in a chat conversation.
    Supports async processing with task_id for polling.
    """

    conversation = models.ForeignKey(
        ChatConversation,
        on_delete=models.CASCADE,
        related_name="messages",
    )
    role = models.CharField(
        max_length=20,
        choices=MESSAGE_ROLE_CHOICES,
    )
    content = models.TextField()
    status = models.CharField(
        max_length=20,
        choices=MESSAGE_STATUS_CHOICES,
        default="completed",
    )
    task_id = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        db_index=True,
        help_text="Task ID for async processing polling",
    )
    extracted_data = models.JSONField(
        default=dict,
        help_text="STAR elements detected in this message",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Message chat"
        verbose_name_plural = "Messages chat"
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["conversation", "created_at"]),
        ]

    def __str__(self):
        return f"{self.get_role_display()}: {self.content[:50]}..."

    def is_pending(self):
        """Check if message is still being processed."""
        return self.status in ("pending", "processing")


class ProfessionalSuccess(models.Model):
    """
    A professional success/achievement formatted using the STAR method.
    Can be created from a chat conversation or manually.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="professional_successes",
    )
    title = models.CharField(
        max_length=255,
        help_text="Short title for the success (e.g., 'Improved customer retention by 18%')",
    )
    # STAR components
    situation = models.TextField(
        blank=True,
        help_text="S - Context: Where, when, what was the environment, what were the stakes?",
    )
    task = models.TextField(
        blank=True,
        help_text="T - Task: What was YOUR specific mission/responsibility?",
    )
    action = models.TextField(
        blank=True,
        help_text="A - Actions: What did YOU do concretely? (use 'I', not 'we')",
    )
    result = models.TextField(
        blank=True,
        help_text="R - Results: What were the measurable outcomes?",
    )
    # Metadata
    skills_demonstrated = models.JSONField(
        default=list,
        help_text="List of skills demonstrated in this success",
    )
    source_conversation = models.ForeignKey(
        ChatConversation,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="generated_successes",
        help_text="Conversation that generated this success (if any)",
    )
    is_draft = models.BooleanField(
        default=True,
        help_text="Whether this success is still a draft",
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this success is included in the candidate profile",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Succes professionnel"
        verbose_name_plural = "Succes professionnels"
        ordering = ["-created_at"]

    def __str__(self):
        status = "brouillon" if self.is_draft else "finalise"
        return f"{self.title} ({status})"

    def is_complete(self):
        """Check if all STAR components are filled."""
        return all([self.situation, self.task, self.action, self.result])

    def get_completion_percentage(self):
        """Calculate STAR completion percentage."""
        fields = [self.situation, self.task, self.action, self.result]
        filled = sum(1 for f in fields if f.strip())
        return int((filled / 4) * 100)

    def get_star_summary(self):
        """Get a formatted STAR summary for display."""
        return {
            "situation": self.situation[:200] + "..." if len(self.situation) > 200 else self.situation,
            "task": self.task[:200] + "..." if len(self.task) > 200 else self.task,
            "action": self.action[:200] + "..." if len(self.action) > 200 else self.action,
            "result": self.result[:200] + "..." if len(self.result) > 200 else self.result,
        }


class Pitch(models.Model):
    """
    User's pitch in two formats: 30 seconds (elevator) and 3 minutes (detailed).
    Can be created from a chat conversation or manually edited.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="pitches",
    )
    title = models.CharField(
        max_length=255,
        blank=True,
        help_text="Optional title for this pitch version (e.g., 'Tech Lead pitch')",
    )
    # Pitch content
    pitch_30s = models.TextField(
        blank=True,
        help_text="30-second elevator pitch (~75-80 words)",
    )
    pitch_3min = models.TextField(
        blank=True,
        help_text="3-minute detailed pitch (~400-450 words)",
    )
    # Key strengths highlighted in the pitch
    key_strengths = models.JSONField(
        default=list,
        help_text="List of 3-5 key strengths highlighted in this pitch",
    )
    # Target context for this pitch
    target_context = models.CharField(
        max_length=255,
        blank=True,
        help_text="Target context (e.g., 'Tech interview', 'Networking event')",
    )
    # Metadata
    source_conversation = models.ForeignKey(
        ChatConversation,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="generated_pitches",
        help_text="Conversation that generated this pitch (if any)",
    )
    is_draft = models.BooleanField(
        default=True,
        help_text="Whether this pitch is still a draft",
    )
    is_default = models.BooleanField(
        default=False,
        help_text="Default pitch to display",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Pitch"
        verbose_name_plural = "Pitches"
        ordering = ["-is_default", "-created_at"]

    def __str__(self):
        status = "brouillon" if self.is_draft else "finalise"
        title = self.title or f"Pitch #{self.id}"
        return f"{title} ({status})"

    def save(self, *args, **kwargs):
        # Ensure only one default pitch per user
        if self.is_default:
            Pitch.objects.filter(user=self.user, is_default=True).exclude(pk=self.pk).update(is_default=False)
        super().save(*args, **kwargs)

    def is_complete(self):
        """Check if both pitch formats are filled."""
        return bool(self.pitch_30s and self.pitch_3min)

    def get_word_count_30s(self):
        """Get word count for 30s pitch (target: 75-80 words)."""
        return len(self.pitch_30s.split()) if self.pitch_30s else 0

    def get_word_count_3min(self):
        """Get word count for 3min pitch (target: 400-450 words)."""
        return len(self.pitch_3min.split()) if self.pitch_3min else 0

    def get_completion_percentage(self):
        """Calculate pitch completion percentage."""
        filled = sum(
            [
                1 if self.pitch_30s else 0,
                1 if self.pitch_3min else 0,
            ]
        )
        return int((filled / 2) * 100)
