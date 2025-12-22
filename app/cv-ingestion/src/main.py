"""FastAPI application for CV ingestion service."""

import logging
from typing import Annotated

from fastapi import FastAPI, File, HTTPException, UploadFile

from .config import settings
from .extractors import extract_text_from_docx, extract_text_from_pdf
from .llm import analyze_cv_text
from .schemas import ExtractionResponse, HealthResponse

# Configure logging
logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="CV Ingestion Service",
    description="Extract structured information from CV files",
    version="1.0.0",
)


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return HealthResponse(status="healthy", service=settings.SERVICE_NAME)


@app.post("/extract", response_model=ExtractionResponse)
async def extract_cv(file: Annotated[UploadFile, File(description="CV file (PDF or DOCX)")]):
    """
    Extract structured information from a CV file.

    Accepts PDF or DOCX files, extracts text, analyzes with LLM,
    and returns structured data.
    """
    # Validate file type
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    filename_lower = file.filename.lower()
    supported = settings.SUPPORTED_FORMATS.split(",")

    if not any(filename_lower.endswith(f".{fmt}") for fmt in supported):
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file format. Supported: {supported}",
        )

    # Read file content
    try:
        content = await file.read()
    except Exception as e:
        logger.error(f"Failed to read file: {e}")
        raise HTTPException(status_code=400, detail="Failed to read file") from e

    # Check file size
    max_size = settings.MAX_FILE_SIZE_MB * 1024 * 1024
    if len(content) > max_size:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Max size: {settings.MAX_FILE_SIZE_MB}MB",
        )

    # Extract text based on file type
    try:
        if filename_lower.endswith(".pdf"):
            raw_text = extract_text_from_pdf(content)
        elif filename_lower.endswith(".docx"):
            raw_text = extract_text_from_docx(content)
        else:
            raise HTTPException(status_code=400, detail="Unsupported file format")
    except ValueError as e:
        logger.error(f"Text extraction failed: {e}")
        return ExtractionResponse(
            success=False,
            error=f"Text extraction failed: {e}",
        )

    # Analyze with LLM
    try:
        extracted_lines = analyze_cv_text(raw_text)
    except ValueError as e:
        logger.error(f"LLM analysis failed: {e}")
        return ExtractionResponse(
            success=False,
            raw_text=raw_text,
            error=f"LLM analysis failed: {e}",
        )

    logger.info(f"Successfully extracted {len(extracted_lines)} lines from {file.filename}")

    return ExtractionResponse(
        success=True,
        extracted_lines=extracted_lines,
        raw_text=raw_text,
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8081)  # nosec B104 - Docker container
