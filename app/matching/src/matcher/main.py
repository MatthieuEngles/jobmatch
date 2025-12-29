from fastapi import FastAPI
from matcher.api.routes import router as matching_router

app = FastAPI(
    title="CV to Job Matching Service",
    version="1.0.0",
)

app.include_router(matching_router, prefix="/matching", tags=["matching"])
