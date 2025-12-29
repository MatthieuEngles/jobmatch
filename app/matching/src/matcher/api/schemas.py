from pydantic import BaseModel, Field


class MatchRequest(BaseModel):
    """
    Request payload for matching a CV against job offers.
    """

    title_embedded: list[float] = Field(
        ..., description="Embedding vector of the CV's profile title (as a list of floats)."
    )
    description_embedded: list[float] = Field(
        ..., description="Embedding vector of the CV's profile description (as a list of floats)."
    )
    job_offers_sqlite: str = Field(..., description="Path to the SQLite database containing job offer embeddings.")


class MatchResultSchema(BaseModel):
    """
    Represents a single match result with job offer id and similarity score.
    """

    id: str = Field(..., description="Job offer ID")
    similarity: float = Field(..., description="Similarity score")


class MatchResponse(BaseModel):
    """
    Represents the response from a match request:

    :param result: List of matched job offers with their similarity scores.
    """

    result: list[MatchResultSchema] = Field(..., description="List of matched job offers with their similarity scores")
