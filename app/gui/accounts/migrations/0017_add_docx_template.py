# Generated migration for DocxTemplate model and User.docx_template field

import django.db.models.deletion
from django.db import migrations, models


def create_default_template(apps, schema_editor):
    """Create the default professional DOCX template."""
    DocxTemplate = apps.get_model("accounts", "DocxTemplate")
    DocxTemplate.objects.create(
        name="Professionnel",
        description="Template professionnel avec police Calibri, couleur d'accent bleue et marges de 2cm.",
        font_name="Calibri",
        font_size_name=32,  # 16pt
        font_size_section=24,  # 12pt
        font_size_body=20,  # 10pt
        accent_color="#667eea",
        margin_top=1134,  # 2cm
        margin_right=1134,
        margin_bottom=1134,
        margin_left=1134,
        line_spacing=276,  # 1.15
        paragraph_spacing_after=120,
        is_default=True,
        is_system=True,
    )


def reverse_create_default_template(apps, schema_editor):
    """Remove the default template."""
    DocxTemplate = apps.get_model("accounts", "DocxTemplate")
    DocxTemplate.objects.filter(name="Professionnel", is_system=True).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0016_add_application_model"),
    ]

    operations = [
        # Create DocxTemplate model
        migrations.CreateModel(
            name="DocxTemplate",
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
                    "name",
                    models.CharField(
                        help_text="Template name (e.g., 'Professional', 'Modern', 'Classic')",
                        max_length=100,
                        unique=True,
                    ),
                ),
                (
                    "description",
                    models.TextField(blank=True, help_text="Template description"),
                ),
                (
                    "font_name",
                    models.CharField(
                        default="Calibri",
                        help_text="Main font family (e.g., 'Calibri', 'Arial', 'Times New Roman')",
                        max_length=50,
                    ),
                ),
                (
                    "font_size_name",
                    models.PositiveSmallIntegerField(
                        default=32,
                        help_text="Font size for name/title in half-points (32 = 16pt)",
                    ),
                ),
                (
                    "font_size_section",
                    models.PositiveSmallIntegerField(
                        default=24,
                        help_text="Font size for section titles in half-points (24 = 12pt)",
                    ),
                ),
                (
                    "font_size_body",
                    models.PositiveSmallIntegerField(
                        default=20,
                        help_text="Font size for body text in half-points (20 = 10pt)",
                    ),
                ),
                (
                    "accent_color",
                    models.CharField(
                        default="#667eea",
                        help_text="Accent color for section titles (hex format, e.g., '#667eea')",
                        max_length=7,
                    ),
                ),
                (
                    "margin_top",
                    models.PositiveIntegerField(default=1134, help_text="Top margin in twips (1134 = 2cm)"),
                ),
                (
                    "margin_right",
                    models.PositiveIntegerField(default=1134, help_text="Right margin in twips (1134 = 2cm)"),
                ),
                (
                    "margin_bottom",
                    models.PositiveIntegerField(default=1134, help_text="Bottom margin in twips (1134 = 2cm)"),
                ),
                (
                    "margin_left",
                    models.PositiveIntegerField(default=1134, help_text="Left margin in twips (1134 = 2cm)"),
                ),
                (
                    "line_spacing",
                    models.PositiveSmallIntegerField(
                        default=276,
                        help_text="Line spacing in 240ths of a line (240 = single, 276 = 1.15, 360 = 1.5)",
                    ),
                ),
                (
                    "paragraph_spacing_after",
                    models.PositiveSmallIntegerField(
                        default=120,
                        help_text="Space after paragraphs in twips (120 = approx 2mm)",
                    ),
                ),
                (
                    "is_default",
                    models.BooleanField(
                        default=False,
                        help_text="Is this the default template for new users?",
                    ),
                ),
                (
                    "is_system",
                    models.BooleanField(
                        default=False,
                        help_text="Is this a system template (cannot be deleted)?",
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "Template DOCX",
                "verbose_name_plural": "Templates DOCX",
                "ordering": ["-is_default", "name"],
            },
        ),
        # Add docx_template field to User
        migrations.AddField(
            model_name="user",
            name="docx_template",
            field=models.ForeignKey(
                blank=True,
                help_text="Preferred DOCX template for CV/cover letter exports",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="users",
                to="accounts.docxtemplate",
            ),
        ),
        # Create default template
        migrations.RunPython(
            create_default_template,
            reverse_create_default_template,
        ),
    ]
