"""
API routes for the matching service.

"""

import os
from pathlib import Path

import numpy as np
from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException
from matcher.api.schemas import MatchRequest, MatchResponse
from matcher.core import match_cv
from matcher.logging_config import logger

# Load environment variables
env_path = Path(__file__).parent.parent.parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

router = APIRouter()


@router.post("/match", response_model=MatchResponse)
def match(request: MatchRequest) -> MatchResponse:
    """
    Match embedded title and description from a cv to a job offer.

    This endpoint automatically routes to either SQLite or BigQuery backend
    based on the MATCHING_METHOD environment variable.

    :param request: Description
        title_embedding: profile title embedding (list[float])
        cv_embedding: profile description embedding (list[float])
        top_k: number of top matches to return (int)
    :type request: MatchRequest
    """
    # Get matching method from environment
    matching_method = os.getenv("MATCHING_METHOD", "sqlite").lower()

    logger.info(f"Received match request using {matching_method} method")
    logger.debug("Title embedding length: %d", len(request.title_embedding))
    logger.debug("CV embedding length: %d", len(request.cv_embedding))
    logger.debug("Top K: %d", request.top_k)

    if matching_method == "sqlite":
        return _match_sqlite(request)
    elif matching_method == "bigquery":
        return _match_bigquery(request)
    else:
        raise HTTPException(
            status_code=500, detail=f"Invalid MATCHING_METHOD: {matching_method}. Must be 'sqlite' or 'bigquery'"
        )


def _match_sqlite(request: MatchRequest) -> MatchResponse:
    """
    Match using local SQLite database with vector similarity.

    Uses the legacy match_cv function with local embeddings database.
    """
    job_offers_db = os.getenv("JOB_OFFERS_DB_PATH", "/app/matching/data/job_offers_gold.db")

    logger.info("Using SQLite backend: %s", job_offers_db)

    result = match_cv(
        np.array(request.title_embedding, dtype=np.float32),
        np.array(request.cv_embedding, dtype=np.float32),
        job_offers_db,
    )

    # Return top_k results
    top_results = result[: request.top_k]

    logger.info("Returning %d SQLite match results (top %d)", len(top_results), request.top_k)

    return {"matches": [{"offer_id": r.id, "score": r.similarity, "ingestion_date": None} for r in top_results]}


def _match_bigquery(request: MatchRequest) -> MatchResponse:
    """
    Match using BigQuery Vector Search (optimized for 700k+ entries).

    Uses Google Cloud BigQuery's VECTOR_SEARCH functionality for scalable,
    cloud-based vector similarity search.
    """
    from matcher.vector_search import VectorSearchService

    logger.info("Using BigQuery Vector Search backend")

    try:
        # Initialize vector search service (loads config from env)
        service = VectorSearchService()

        # Perform vector search on description embeddings (default, no JOIN)
        # This is optimized for cost - no JOIN with main table
        results = service.find_nearest_embeddings(
            query_embedding=request.cv_embedding,  # Use CV/description embedding
            top_k=request.top_k,
            query_id=None,  # Auto-generated
            query_metadata={
                "source": "api_match",
                "title_embedding_dim": len(request.title_embedding),
                "cv_embedding_dim": len(request.cv_embedding),
            },
            use_title_embeddings=False,  # Use description embeddings (default)
        )

        logger.info("Returning %d BigQuery match results", len(results))

        # Convert BigQuery results to API response format
        # BigQuery returns: {"id": str, "similarity": float, "ingestion_date": str}
        # API expects: {"offer_id": str, "score": float, "ingestion_date": str}
        return {
            "matches": [
                {"offer_id": r["id"], "score": r["similarity"], "ingestion_date": r.get("ingestion_date")}
                for r in results
            ]
        }

    except Exception as e:
        logger.error(f"BigQuery vector search failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"BigQuery vector search failed: {str(e)}") from e
