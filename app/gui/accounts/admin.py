from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import CV, CoverLetter, ExtractedLine, User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ["email", "first_name", "last_name", "is_active", "created_at"]
    search_fields = ["email", "first_name", "last_name"]
    ordering = ["-created_at"]


@admin.register(CV)
class CVAdmin(admin.ModelAdmin):
    list_display = [
        "original_filename",
        "user",
        "extraction_status",
        "uploaded_at",
    ]
    list_filter = ["extraction_status", "uploaded_at"]
    search_fields = ["original_filename", "user__email"]
    raw_id_fields = ["user"]
    ordering = ["-uploaded_at"]


@admin.register(CoverLetter)
class CoverLetterAdmin(admin.ModelAdmin):
    list_display = ["title", "original_filename", "user", "uploaded_at"]
    search_fields = ["title", "original_filename", "user__email"]
    raw_id_fields = ["user"]
    ordering = ["-uploaded_at"]


@admin.register(ExtractedLine)
class ExtractedLineAdmin(admin.ModelAdmin):
    list_display = [
        "content_type",
        "content_preview",
        "user",
        "source_cv",
        "is_active",
    ]
    list_filter = ["content_type", "is_active", "modified_by_user"]
    search_fields = ["content", "user__email"]
    raw_id_fields = ["user", "source_cv"]
    ordering = ["content_type", "order"]

    @admin.display(description="Contenu")
    def content_preview(self, obj):
        return obj.content[:50] + "..." if len(obj.content) > 50 else obj.content
