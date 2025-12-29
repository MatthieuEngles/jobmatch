"""
API routes for the matching service.

"""

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
        title_embedded: profile title embedded (list[float])
        description_embedded: profile description embedded (list[float])
        job_offers_sqlite: Path to the job offers embeddings database (sqlite).
    :type request: MatchRequest
    """
    logger.info("Received match request for DB: %s", request.job_offers_sqlite)
    logger.debug("Title embedding length: %d", len(request.title_embedded))
    logger.debug("Description embedding length: %d", len(request.description_embedded))

    result = match_cv(
        np.array(request.title_embedded, dtype=np.float32),
        np.array(request.description_embedded, dtype=np.float32),
        request.job_offers_sqlite,
    )

    logger.info("Returning %d match results", len(result))
    return {"result": result}
