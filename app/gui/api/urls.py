"""URL configuration for the REST API."""

from django.urls import path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .views import (
    CurrentUserView,
    HealthCheckView,
    ImportedOfferDetailView,
    ImportedOfferListView,
    ImportOfferView,
    LogoutView,
)

app_name = "api"

urlpatterns = [
    # OpenAPI schema and documentation
    path("schema/", SpectacularAPIView.as_view(), name="schema"),
    path("docs/", SpectacularSwaggerView.as_view(url_name="api:schema"), name="swagger-ui"),
    path("redoc/", SpectacularRedocView.as_view(url_name="api:schema"), name="redoc"),
    # Health check
    path("health/", HealthCheckView.as_view(), name="health"),
    # Authentication (JWT)
    path("auth/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("auth/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("auth/user/", CurrentUserView.as_view(), name="current_user"),
    path("auth/logout/", LogoutView.as_view(), name="logout"),
    # Offers
    path("offers/", ImportedOfferListView.as_view(), name="offer_list"),
    path("offers/import/", ImportOfferView.as_view(), name="offer_import"),
    path("offers/<int:pk>/", ImportedOfferDetailView.as_view(), name="offer_detail"),
]
