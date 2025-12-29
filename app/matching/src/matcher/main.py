"""
CV to Job Matching Service main application.

FastAPI API to match CV embeddings against job offer embeddings stored in SQLite.
Logs go to stdout and are Docker-friendly.
"""

import time

from fastapi import FastAPI, Request
from matcher.api.routes import router as matching_router
from matcher.logging_config import logger

# -----------------------------
# Create FastAPI app
# -----------------------------
app = FastAPI(
    title="CV to Job Matching Service",
    version="1.0.0",
)

# -----------------------------
# Include routers
# -----------------------------
app.include_router(matching_router, prefix="/matching", tags=["matching"])


# -----------------------------
# Simple logging middleware
# -----------------------------
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    logger.info(
        "%s %s completed_in=%.3f status_code=%d",
        request.method,
        request.url.path,
        process_time,
        response.status_code,
    )
    return response
