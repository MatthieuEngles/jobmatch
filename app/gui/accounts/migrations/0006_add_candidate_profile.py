# Generated migration for CandidateProfile and ProfileItemSelection

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0005_add_structured_fields_to_extractedline"),
    ]

    operations = [
        migrations.CreateModel(
            name="CandidateProfile",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "title",
                    models.CharField(
                        help_text="Profile title (e.g., 'Data Scientist', 'Tech Lead')",
                        max_length=100,
                    ),
                ),
                (
                    "description",
                    models.TextField(
                        blank=True,
                        help_text="Optional description of the target position",
                    ),
                ),
                (
                    "is_default",
                    models.BooleanField(
                        default=False,
                        help_text="Default profile selected on login",
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="candidate_profiles",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Profil de candidature",
                "verbose_name_plural": "Profils de candidature",
                "ordering": ["-is_default", "title"],
            },
        ),
        migrations.CreateModel(
            name="ProfileItemSelection",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "is_selected",
                    models.BooleanField(
                        default=True,
                        help_text="Whether this item is included in the profile",
                    ),
                ),
                (
                    "extracted_line",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="profile_selections",
                        to="accounts.extractedline",
                    ),
                ),
                (
                    "profile",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="item_selections",
                        to="accounts.candidateprofile",
                    ),
                ),
            ],
            options={
                "verbose_name": "Selection d'element",
                "verbose_name_plural": "Selections d'elements",
            },
        ),
        migrations.AddConstraint(
            model_name="candidateprofile",
            constraint=models.UniqueConstraint(
                fields=("user", "title"),
                name="unique_profile_title_per_user",
            ),
        ),
        migrations.AddConstraint(
            model_name="profileitemselection",
            constraint=models.UniqueConstraint(
                fields=("profile", "extracted_line"),
                name="unique_selection_per_profile_line",
            ),
        ),
    ]
