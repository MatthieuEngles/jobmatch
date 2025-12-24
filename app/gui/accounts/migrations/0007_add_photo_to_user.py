# Generated migration for User.photo field

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0006_add_candidate_profile"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="photo",
            field=models.ImageField(
                blank=True,
                help_text="Profile photo",
                null=True,
                upload_to="profile_photos/",
            ),
        ),
    ]
