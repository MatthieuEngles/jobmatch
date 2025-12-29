"""
API routes for the matching service.

"""
import numpy as np
from fastapi import APIRouter
from matcher.core import match_cv
from matcher.api.schemas import MatchRequest, MatchResponse

router = APIRouter()

@router.post("/match", response_model=MatchResponse)
def match(request: MatchRequest):
    """
    Match embedded title and description from a cv to a job offer.
    
    :param request: Description
        title_embedded: profile title embedded (list[float])
        description_embedded: profile description embedded (list[float])
        job_offers_sqlite: Path to the job offers embeddings database (sqlite).
    :type request: MatchRequest
    """
    result = match_cv(
        np.array(request.title_embedded, dtype=np.float32),
        np.array(request.description_embedded, dtype=np.float32),
        request.job_offers_sqlite
    )
    return {"result": result}
