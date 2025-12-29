from pydantic import BaseModel


class MatchRequest(BaseModel):
    """
    Represents a request to match embedded cv title and description and a job offer.

    title_embedded: profile title embedded (np.ndarray as str)
    description_embedded: profile description embedded (np.ndarray as str)
    job_offers_sqlite: Path to the job offers embeddings database (sqlite).
    """
    title_embedded: list[float]
    description_embedded: list[float]
    job_offers_sqlite: str

class MatchResponse(BaseModel):
    """
    Represents the response from a match request:

    :param result: List of matched job offers with their similarity scores.
    """
    result: list[tuple[str, float]]
