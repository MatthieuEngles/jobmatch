from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """Custom user model for JobMatch."""

    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=20, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

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
