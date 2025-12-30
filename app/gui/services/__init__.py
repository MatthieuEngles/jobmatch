# Services module for GUI business logic
from .matching import MatchingService, MatchingServiceError, get_matching_service
from .offers_db import OfferFullDetails, OffersDB, OffersDBError, get_offers_db
from .top_offers import TopOfferResult, get_top_offers_for_user

__all__ = [
    "get_matching_service",
    "MatchingService",
    "MatchingServiceError",
    "get_offers_db",
    "OffersDB",
    "OffersDBError",
    "OfferFullDetails",
    "get_top_offers_for_user",
    "TopOfferResult",
]
