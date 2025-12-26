"""Serializers for the REST API."""

from accounts.models import ImportedOffer, User
from rest_framework import serializers


class UserSerializer(serializers.ModelSerializer):
    """Serializer for current user info."""

    class Meta:
        model = User
        fields = ["id", "email", "first_name", "last_name"]
        read_only_fields = fields


class SalarySerializer(serializers.Serializer):
    """Serializer for salary information."""

    min = serializers.IntegerField(required=False, allow_null=True)
    max = serializers.IntegerField(required=False, allow_null=True)
    currency = serializers.CharField(max_length=10, required=False, default="EUR")
    period = serializers.CharField(max_length=20, required=False, default="year")


class OfferImportSerializer(serializers.Serializer):
    """Serializer for importing an offer from browser extension."""

    sourceUrl = serializers.URLField(max_length=500)
    sourceDomain = serializers.CharField(max_length=100)
    title = serializers.CharField(max_length=300)
    company = serializers.CharField(max_length=200, required=False, allow_blank=True, default="")
    location = serializers.CharField(max_length=200, required=False, allow_blank=True, default="")
    description = serializers.CharField(required=False, allow_blank=True, default="")
    contractType = serializers.CharField(max_length=50, required=False, allow_blank=True, default="")
    salary = SalarySerializer(required=False, allow_null=True)
    skills = serializers.ListField(
        child=serializers.CharField(max_length=100),
        required=False,
        default=list,
    )
    remoteType = serializers.CharField(max_length=50, required=False, allow_blank=True, default="")
    capturedAt = serializers.DateTimeField()


class ImportOfferRequestSerializer(serializers.Serializer):
    """Serializer for the full import request."""

    offer = OfferImportSerializer()
    profileId = serializers.IntegerField(required=False, allow_null=True)


class ImportedOfferSerializer(serializers.ModelSerializer):
    """Serializer for ImportedOffer model (read)."""

    # Use camelCase for API response to match frontend conventions
    sourceUrl = serializers.CharField(source="source_url")
    sourceDomain = serializers.CharField(source="source_domain")
    capturedAt = serializers.DateTimeField(source="captured_at")
    contractType = serializers.CharField(source="contract_type")
    remoteType = serializers.CharField(source="remote_type")
    matchScore = serializers.FloatField(source="match_score", allow_null=True)
    matchedAt = serializers.DateTimeField(source="matched_at", allow_null=True)
    createdAt = serializers.DateTimeField(source="created_at")
    updatedAt = serializers.DateTimeField(source="updated_at")
    candidateProfileId = serializers.IntegerField(source="candidate_profile_id", allow_null=True)

    class Meta:
        model = ImportedOffer
        fields = [
            "id",
            "sourceUrl",
            "sourceDomain",
            "capturedAt",
            "title",
            "company",
            "location",
            "description",
            "contractType",
            "remoteType",
            "salary",
            "skills",
            "matchScore",
            "matchedAt",
            "status",
            "candidateProfileId",
            "createdAt",
            "updatedAt",
        ]
        read_only_fields = fields


class ImportedOfferUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating an ImportedOffer (status only)."""

    class Meta:
        model = ImportedOffer
        fields = ["status"]


class ImportOfferResponseSerializer(serializers.Serializer):
    """Serializer for import response."""

    offerId = serializers.IntegerField()
    matchScore = serializers.FloatField(allow_null=True)
    message = serializers.CharField()
