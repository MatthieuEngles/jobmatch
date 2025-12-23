"""Common interfaces shared across all services."""

from pydantic import BaseModel


class ServiceHealth(BaseModel):
    """Standard health check response for all services."""

    status: str
    service: str
    version: str = "1.0.0"
