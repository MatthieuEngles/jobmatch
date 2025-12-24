# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0010_add_chat_and_professional_success"),
    ]

    operations = [
        migrations.AddField(
            model_name="chatconversation",
            name="coaching_type",
            field=models.CharField(
                choices=[
                    ("star", "Succes professionnel (STAR)"),
                    ("pitch", "Pitch (30s et 3min)"),
                ],
                default="star",
                help_text="Type of coaching (STAR for success, pitch for 30s/3min pitch)",
                max_length=20,
            ),
        ),
    ]
