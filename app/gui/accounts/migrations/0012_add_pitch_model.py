# Generated manually

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0011_add_coaching_type_to_conversation"),
    ]

    operations = [
        migrations.CreateModel(
            name="Pitch",
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
                        blank=True,
                        help_text="Optional title for this pitch version (e.g., 'Tech Lead pitch')",
                        max_length=255,
                    ),
                ),
                (
                    "pitch_30s",
                    models.TextField(
                        blank=True,
                        help_text="30-second elevator pitch (~75-80 words)",
                    ),
                ),
                (
                    "pitch_3min",
                    models.TextField(
                        blank=True,
                        help_text="3-minute detailed pitch (~400-450 words)",
                    ),
                ),
                (
                    "key_strengths",
                    models.JSONField(
                        default=list,
                        help_text="List of 3-5 key strengths highlighted in this pitch",
                    ),
                ),
                (
                    "target_context",
                    models.CharField(
                        blank=True,
                        help_text="Target context (e.g., 'Tech interview', 'Networking event')",
                        max_length=255,
                    ),
                ),
                (
                    "is_draft",
                    models.BooleanField(
                        default=True,
                        help_text="Whether this pitch is still a draft",
                    ),
                ),
                (
                    "is_default",
                    models.BooleanField(
                        default=False,
                        help_text="Default pitch to display",
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "source_conversation",
                    models.ForeignKey(
                        blank=True,
                        help_text="Conversation that generated this pitch (if any)",
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="generated_pitches",
                        to="accounts.chatconversation",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="pitches",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Pitch",
                "verbose_name_plural": "Pitches",
                "ordering": ["-is_default", "-created_at"],
            },
        ),
    ]
