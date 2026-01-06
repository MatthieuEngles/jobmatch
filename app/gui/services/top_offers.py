"""
Top Offers service - orchestrates the flow for personalized job recommendations.

Flow:
1. Get user's candidate profiles
2. For each profile, generate embeddings (title + CV)
3. Call matching service to get scored offers (with Redis caching)
4. Merge results across profiles, deduplicate, keep best scores
5. Fetch offer details from database
6. Return formatted results for display
"""

import hashlib
import logging
import os
from dataclasses import dataclass

from django.core.cache import cache

from .matching import MatchResult, get_matching_service
from .offers_db import get_offers_db

logger = logging.getLogger(__name__)

# Cache TTL from settings (default 15 minutes)
try:
    from django.conf import settings

    CACHE_TTL_MATCHING = getattr(settings, "CACHE_TTL_MATCHING_RESULTS", 60 * 15)
except Exception:
    CACHE_TTL_MATCHING = 60 * 15


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


def _get_profile_cache_key(profile_id: int, title_text: str, cv_text: str, top_k: int) -> str:
    """Generate a cache key for profile matching results."""
    # Hash the content to create a unique key that changes when profile content changes
    # MD5 used for cache key generation only (not security), hence usedforsecurity=False
    content_hash = hashlib.md5(f"{title_text}:{cv_text}:{top_k}".encode(), usedforsecurity=False).hexdigest()[:16]
    return f"matching:profile:{profile_id}:{content_hash}"


def _get_cached_matches(cache_key: str) -> list[MatchResult] | None:
    """Get cached matching results."""
    try:
        cached = cache.get(cache_key)
        if cached:
            logger.debug(f"Cache hit for {cache_key}")
            # Deserialize from JSON
            return [
                MatchResult(
                    offer_id=m["offer_id"],
                    score=m["score"],
                    ingestion_date=m.get("ingestion_date"),
                )
                for m in cached
            ]
    except Exception as e:
        logger.warning(f"Cache get error: {e}")
    return None


def _cache_matches(cache_key: str, matches: list[MatchResult]) -> None:
    """Cache matching results."""
    try:
        # Serialize to JSON-compatible format
        data = [
            {
                "offer_id": m.offer_id,
                "score": m.score,
                "ingestion_date": m.ingestion_date,
            }
            for m in matches
        ]
        cache.set(cache_key, data, CACHE_TTL_MATCHING)
        logger.debug(f"Cached {len(matches)} matches for {cache_key}")
    except Exception as e:
        logger.warning(f"Cache set error: {e}")


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
    # Key: offer_id, Value: (best_score, list of profile names, ingestion_date)
    all_matches: dict[str, tuple[float, list[str], str | None]] = {}

    for profile in profiles:
        try:
            # Prepare text for embeddings and cache key
            # Title text = profile title (e.g., "Data Scientist", "Tech Lead")
            title_text = profile.title

            # CV text = concatenation of experiences + skills (hard + soft)
            cv_parts = []

            # Get experiences
            experiences = profile.get_selected_lines_by_type("experience")
            for exp in experiences:
                # Build rich text: position + entity + dates + description (detailed text)
                parts = []
                if exp.position:
                    parts.append(exp.position)
                if exp.entity:
                    parts.append(f"chez {exp.entity}")
                if exp.dates:
                    parts.append(f"({exp.dates})")

                # Add description (detailed activity text visible in card)
                if exp.description:
                    parts.append(f": {exp.description}")
                elif exp.content:
                    # Fallback to content if no description
                    parts.append(f": {exp.content}")

                if parts:
                    cv_parts.append(" ".join(parts))

            # Get hard skills
            hard_skills = profile.get_selected_lines_by_type("skill_hard")
            skill_texts = [s.content for s in hard_skills if s.content]
            if skill_texts:
                cv_parts.append("Compétences techniques: " + ", ".join(skill_texts))

            # Get soft skills
            soft_skills = profile.get_selected_lines_by_type("skill_soft")
            soft_texts = [s.content for s in soft_skills if s.content]
            if soft_texts:
                cv_parts.append("Soft skills: " + ", ".join(soft_texts))

            # Build final CV text (fallback to title if no lines)
            cv_text = "\n".join(cv_parts) if cv_parts else title_text

            # Check cache first
            cache_key = _get_profile_cache_key(profile.id, title_text, cv_text, top_k)
            matches = _get_cached_matches(cache_key)

            if matches is None:
                # Cache miss - compute embeddings and get matches
                logger.info(f"Cache miss for profile {profile.id}, computing matches...")

                # Log the text being embedded for debugging
                logger.info("=" * 60)
                logger.info(f"PROFILE {profile.id} - TEXT TO EMBED")
                logger.info("=" * 60)
                logger.info(f"TITLE TEXT ({len(title_text)} chars):")
                logger.info(title_text[:500] if len(title_text) > 500 else title_text)
                if len(title_text) > 500:
                    logger.info(f"... [truncated, total {len(title_text)} chars]")
                logger.info("-" * 40)
                logger.info(f"CV TEXT ({len(cv_text)} chars):")
                logger.info(cv_text[:1000] if len(cv_text) > 1000 else cv_text)
                if len(cv_text) > 1000:
                    logger.info(f"... [truncated, total {len(cv_text)} chars]")
                logger.info("=" * 60)

                if use_mock:
                    # In mock mode, use dummy embeddings
                    title_embedding = [0.0] * 384  # Dummy embedding
                    cv_embedding = [0.0] * 384
                else:
                    # Generate real embeddings
                    embedder = get_embedder()

                    # Title embedding from profile description
                    title_embeddings = embedder([title_text])
                    title_embedding = title_embeddings[0].tolist()

                    # CV embedding from selected lines
                    cv_embeddings = embedder([cv_text])
                    cv_embedding = cv_embeddings[0].tolist()

                # Get matches from matching service
                matches = matching_service.get_matches(
                    title_embedding=title_embedding,
                    cv_embedding=cv_embedding,
                    top_k=top_k,
                )

                # Cache the results
                _cache_matches(cache_key, matches)
            else:
                logger.info(f"Cache hit for profile {profile.id}, using cached matches")

            # Merge results
            profile_name = profile.title or profile.description[:30] if profile.description else f"Profil {profile.id}"
            for match in matches:
                if match.offer_id in all_matches:
                    # Keep best score, add profile name, keep ingestion_date
                    current_score, current_profiles, current_date = all_matches[match.offer_id]
                    if match.score > current_score:
                        all_matches[match.offer_id] = (
                            match.score,
                            current_profiles + [profile_name],
                            match.ingestion_date or current_date,
                        )
                    else:
                        all_matches[match.offer_id] = (
                            current_score,
                            current_profiles + [profile_name],
                            current_date or match.ingestion_date,
                        )
                else:
                    all_matches[match.offer_id] = (match.score, [profile_name], match.ingestion_date)

        except Exception as e:
            logger.error(f"Error processing profile {profile.id}: {e}")
            continue

    if not all_matches:
        logger.info(f"No matches found for user {user.id}")
        return []

    # Sort by score and take top_k
    sorted_matches = sorted(all_matches.items(), key=lambda x: x[1][0], reverse=True)[:top_k]

    # Get offer details with ingestion_dates for partition pruning
    offer_ids = [offer_id for offer_id, _ in sorted_matches]
    ingestion_dates = {offer_id: data[2] for offer_id, data in sorted_matches if data[2] is not None}
    offer_details = offers_db.get_offers_by_ids(offer_ids, ingestion_dates=ingestion_dates)

    # Build results
    results = []
    for offer_id, (score, profile_names, _ingestion_date) in sorted_matches:
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
