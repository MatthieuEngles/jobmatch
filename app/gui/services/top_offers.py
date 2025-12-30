"""
Top Offers service - orchestrates the flow for personalized job recommendations.

Flow:
1. Get user's candidate profiles
2. For each profile, generate embeddings (title + CV)
3. Call matching service to get scored offers
4. Merge results across profiles, deduplicate, keep best scores
5. Fetch offer details from database
6. Return formatted results for display
"""

import logging
import os
from dataclasses import dataclass

from .matching import get_matching_service
from .offers_db import get_offers_db

logger = logging.getLogger(__name__)


@dataclass
class TopOfferResult:
    """A top offer with its details and matching information."""

    offer_id: str
    intitule: str
    entreprise: str | None
    description: str | None
    score: float
    matching_profiles: list[str]  # Names of profiles that matched this offer


def get_embedder():
    """
    Get the embedder function based on environment configuration.

    Returns a callable that takes a list of texts and returns embeddings.
    """
    provider = os.environ.get("EMBEDDINGS_PROVIDER", "sentence_transformers")
    model = os.environ.get("EMBEDDINGS_MODEL", "all-MiniLM-L6-v2")

    try:
        from shared.embeddings import create_embedder

        return create_embedder(provider, model=model)
    except ImportError as e:
        logger.error(f"Failed to import embeddings: {e}")
        raise ImportError("Shared embeddings module not available. Ensure shared package is installed.") from e


def get_top_offers_for_user(user, top_k: int = 20) -> list[TopOfferResult]:
    """
    Get personalized top offers for a user based on their candidate profiles.

    Args:
        user: Django User object
        top_k: Maximum number of offers to return

    Returns:
        List of TopOfferResult sorted by score descending

    Raises:
        ValueError: If user has no profiles
    """
    # Get user's candidate profiles
    profiles = list(user.candidate_profiles.all())

    if not profiles:
        logger.info(f"User {user.id} has no candidate profiles")
        return []

    # Get services
    matching_service = get_matching_service()
    offers_db = get_offers_db()

    # Check if we're in mock mode (skip embeddings)
    use_mock = os.environ.get("USE_MOCK_MATCHING", "false").lower() == "true"

    # Collect all matches from all profiles
    # Key: offer_id, Value: (best_score, list of profile names)
    all_matches: dict[str, tuple[float, list[str]]] = {}

    for profile in profiles:
        try:
            if use_mock:
                # In mock mode, use dummy embeddings
                title_embedding = [0.0] * 384  # Dummy embedding
                cv_embedding = [0.0] * 384
            else:
                # Generate real embeddings
                embedder = get_embedder()

                # Title embedding from profile description
                title_text = profile.description or profile.title
                title_embeddings = embedder([title_text])
                title_embedding = title_embeddings[0].tolist()

                # CV embedding from selected lines
                selected_lines = profile.get_selected_lines()
                if selected_lines:
                    cv_text = "\n".join(line.content for line in selected_lines if line.content)
                else:
                    cv_text = title_text  # Fallback to title if no lines

                cv_embeddings = embedder([cv_text])
                cv_embedding = cv_embeddings[0].tolist()

            # Get matches from matching service
            matches = matching_service.get_matches(
                title_embedding=title_embedding,
                cv_embedding=cv_embedding,
                top_k=top_k,
            )

            # Merge results
            profile_name = profile.title or profile.description[:30] if profile.description else f"Profil {profile.id}"
            for match in matches:
                if match.offer_id in all_matches:
                    # Keep best score, add profile name
                    current_score, current_profiles = all_matches[match.offer_id]
                    if match.score > current_score:
                        all_matches[match.offer_id] = (
                            match.score,
                            current_profiles + [profile_name],
                        )
                    else:
                        all_matches[match.offer_id] = (
                            current_score,
                            current_profiles + [profile_name],
                        )
                else:
                    all_matches[match.offer_id] = (match.score, [profile_name])

        except Exception as e:
            logger.error(f"Error processing profile {profile.id}: {e}")
            continue

    if not all_matches:
        logger.info(f"No matches found for user {user.id}")
        return []

    # Sort by score and take top_k
    sorted_matches = sorted(all_matches.items(), key=lambda x: x[1][0], reverse=True)[:top_k]

    # Get offer details
    offer_ids = [offer_id for offer_id, _ in sorted_matches]
    offer_details = offers_db.get_offers_by_ids(offer_ids)

    # Build results
    results = []
    for offer_id, (score, profile_names) in sorted_matches:
        details = offer_details.get(offer_id)
        if details:
            results.append(
                TopOfferResult(
                    offer_id=offer_id,
                    intitule=details.intitule,
                    entreprise=details.entreprise,
                    description=details.description,
                    score=score,
                    matching_profiles=list(set(profile_names)),  # Dedupe profiles
                )
            )
        else:
            # Offer not found in DB, include with minimal info
            logger.warning(f"Offer {offer_id} not found in offers DB")
            results.append(
                TopOfferResult(
                    offer_id=offer_id,
                    intitule="Offre non trouvée",
                    entreprise=None,
                    description=None,
                    score=score,
                    matching_profiles=list(set(profile_names)),
                )
            )

    return results
