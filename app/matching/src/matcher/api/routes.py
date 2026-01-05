"""
API routes for the matching service.

"""

import os

import numpy as np
from fastapi import APIRouter
from matcher.api.schemas import MatchRequest, MatchResponse
from matcher.core import match_cv
from matcher.logging_config import logger

router = APIRouter()


@router.post("/match", response_model=MatchResponse)
def match(request: MatchRequest) -> MatchResponse:
    """
    Match embedded title and description from a cv to a job offer.

    :param request: Description
        title_embedding: profile title embedding (list[float])
        cv_embedding: profile description embedding (list[float])
        top_k: number of top matches to return (int)
    :type request: MatchRequest
    """
    # Get database path from environment variable
    job_offers_db = os.getenv("JOB_OFFERS_DB_PATH", "/app/matching/data/job_offers_gold.db")

    logger.info("Received match request for DB: %s", job_offers_db)
    logger.debug("Title embedding length: %d", len(request.title_embedding))
    logger.debug("CV embedding length: %d", len(request.cv_embedding))
    logger.debug("Top K: %d", request.top_k)

    result = match_cv(
        np.array(request.title_embedding, dtype=np.float32),
        np.array(request.cv_embedding, dtype=np.float32),
        job_offers_db,
    )

    # Return top_k results
    top_results = result[: request.top_k]

    logger.info("Returning %d match results (top %d)", len(top_results), request.top_k)

    return {"matches": [{"offer_id": r.id, "score": r.similarity} for r in top_results]}
