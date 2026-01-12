from pydantic import BaseModel, Field


class MatchRequest(BaseModel):
    """
    Request payload for matching a CV against job offers.
    """

    title_embedding: list[float] = Field(..., description="Embedding vector for profile title")
    cv_embedding: list[float] = Field(..., description="Embedding vector for CV/profile description")
    top_k: int = Field(default=20, description="Number of top matches to return")


class MatchResultSchema(BaseModel):
    """
    Represents a single match result with job offer id and similarity score.
    """

    offer_id: str = Field(..., description="Job offer ID")
    score: float = Field(..., description="Similarity score")
    ingestion_date: str | None = Field(None, description="Ingestion date (ISO format) for partitioned queries")


class MatchResponse(BaseModel):
    """
    Represents the response from a match request:

    :param matches: List of matched job offers with their similarity scores.
    """

    matches: list[MatchResultSchema] = Field(..., description="List of matched job offers with their similarity scores")
