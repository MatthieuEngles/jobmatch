"""REST API views for browser extension integration."""

from accounts.models import Application, CandidateProfile, ImportedOffer
from django.db import IntegrityError
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import status
from rest_framework.generics import ListAPIView, RetrieveUpdateDestroyAPIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from .serializers import (
    ImportedOfferSerializer,
    ImportedOfferUpdateSerializer,
    ImportOfferRequestSerializer,
    ImportOfferResponseSerializer,
    UserSerializer,
)


@extend_schema(tags=["Health"])
class HealthCheckView(APIView):
    """Health check endpoint."""

    permission_classes = [AllowAny]

    @extend_schema(
        summary="Health check",
        description="Returns OK if the API is running.",
        responses={200: {"type": "object", "properties": {"status": {"type": "string"}}}},
    )
    def get(self, request):
        return Response({"status": "ok"})


@extend_schema(tags=["Authentication"])
class CurrentUserView(APIView):
    """Get current authenticated user info."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Get current user",
        description="Returns the authenticated user's information.",
        responses={200: UserSerializer},
    )
    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data)


@extend_schema(tags=["Authentication"])
class LogoutView(APIView):
    """Logout by blacklisting the refresh token."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Logout",
        description="Blacklists the refresh token to invalidate the session.",
        request={"type": "object", "properties": {"refresh": {"type": "string"}}},
        responses={200: {"type": "object", "properties": {"message": {"type": "string"}}}},
    )
    def post(self, request):
        try:
            refresh_token = request.data.get("refresh")
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()
            return Response({"message": "Successfully logged out"}, status=status.HTTP_200_OK)
        except Exception:
            # Token may be invalid or already blacklisted
            return Response({"message": "Logout processed"}, status=status.HTTP_200_OK)


@extend_schema(tags=["Offers"])
class ImportOfferView(APIView):
    """Import a job offer captured by browser extension."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Import an offer",
        description="Import a job offer captured by the browser extension. Returns 201 if new, 200 if already exists.",
        request=ImportOfferRequestSerializer,
        responses={
            201: ImportOfferResponseSerializer,
            200: ImportOfferResponseSerializer,
        },
    )
    def post(self, request):
        serializer = ImportOfferRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        offer_data = serializer.validated_data["offer"]
        profile_id = serializer.validated_data.get("profileId")

        # Get candidate profile if specified
        candidate_profile = None
        if profile_id:
            candidate_profile = CandidateProfile.objects.filter(id=profile_id, user=request.user).first()

        # Create the imported offer
        try:
            imported_offer = ImportedOffer.objects.create(
                user=request.user,
                candidate_profile=candidate_profile,
                source_url=offer_data["sourceUrl"],
                source_domain=offer_data["sourceDomain"],
                captured_at=offer_data["capturedAt"],
                title=offer_data["title"],
                company=offer_data.get("company", ""),
                location=offer_data.get("location", ""),
                description=offer_data.get("description", ""),
                contract_type=offer_data.get("contractType", ""),
                remote_type=offer_data.get("remoteType", ""),
                salary=offer_data.get("salary"),
                skills=offer_data.get("skills", []),
            )
        except IntegrityError:
            # Offer already exists for this user
            existing = ImportedOffer.objects.filter(user=request.user, source_url=offer_data["sourceUrl"]).first()
            if existing:
                response_serializer = ImportOfferResponseSerializer(
                    {
                        "offerId": existing.id,
                        "matchScore": existing.match_score,
                        "message": "Offer already imported",
                    }
                )
                return Response(response_serializer.data, status=status.HTTP_200_OK)
            raise

        # TODO: Call matching service to compute match_score
        # When matching service is ready:
        # 1. Get user's CV embedding from cv-ingestion or cache
        # 2. Call POST /match with offer data
        # 3. Update imported_offer.match_score and matched_at
        #
        # For now, match_score is None (not computed)

        # Auto-create Application for this offer (use get_or_create to handle duplicates)
        Application.objects.get_or_create(
            user=request.user,
            imported_offer=imported_offer,
            defaults={"candidate_profile": candidate_profile},
        )

        response_serializer = ImportOfferResponseSerializer(
            {
                "offerId": imported_offer.id,
                "matchScore": imported_offer.match_score,
                "message": "Offer imported successfully",
            }
        )
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)


@extend_schema(tags=["Offers"])
class ImportedOfferListView(ListAPIView):
    """List all imported offers for the current user."""

    permission_classes = [IsAuthenticated]
    serializer_class = ImportedOfferSerializer

    @extend_schema(
        summary="List offers",
        description="Returns all imported offers for the authenticated user.",
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        return ImportedOffer.objects.filter(user=self.request.user)


@extend_schema_view(
    retrieve=extend_schema(
        summary="Get offer details",
        description="Returns details of a specific imported offer.",
        tags=["Offers"],
    ),
    update=extend_schema(
        summary="Update offer",
        description="Update an imported offer (full update).",
        tags=["Offers"],
    ),
    partial_update=extend_schema(
        summary="Partial update offer",
        description="Partially update an imported offer (e.g., status only).",
        tags=["Offers"],
    ),
    destroy=extend_schema(
        summary="Delete offer",
        description="Delete an imported offer.",
        tags=["Offers"],
    ),
)
class ImportedOfferDetailView(RetrieveUpdateDestroyAPIView):
    """Get, update or delete a specific imported offer."""

    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return ImportedOffer.objects.filter(user=self.request.user)

    def get_serializer_class(self):
        if self.request.method in ["PUT", "PATCH"]:
            return ImportedOfferUpdateSerializer
        return ImportedOfferSerializer
