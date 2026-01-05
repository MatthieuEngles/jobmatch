"""FastAPI application for CV ingestion service."""

import asyncio
import logging
from typing import Annotated

from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, UploadFile

from .config import settings
from .extractors import (
    extract_pdf_content,
    extract_text_from_docx,
    ocr_images,
)
from .llm import LLMConfig, analyze_cv_images, analyze_cv_text, get_llm_provider
from .schemas import (
    ExtractionResponse,
    HealthResponse,
    TaskStatusResponse,
    TaskSubmitResponse,
)
from .task_store import TaskStatus, task_store

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


async def process_cv_task(
    task_id: str,
    content: bytes,
    filename: str,
    llm_config: LLMConfig | None = None,
) -> None:
    """Background task to process CV extraction with smart text/image detection.

    Args:
        task_id: Unique task identifier.
        content: File content bytes.
        filename: Original filename.
        llm_config: Optional LLM configuration that overrides environment settings.
    """
    await task_store.update_status(task_id, TaskStatus.PROCESSING)

    try:
        filename_lower = filename.lower()
        extracted_lines = []
        raw_text = None

        if filename_lower.endswith(".pdf"):
            # Smart PDF extraction: detect text vs image-based
            pdf_content = extract_pdf_content(content)

            if pdf_content.is_text_based:
                # Text-based PDF: use text LLM
                raw_text = pdf_content.text
                loop = asyncio.get_event_loop()
                extracted_lines = await loop.run_in_executor(None, analyze_cv_text, raw_text, llm_config)
            else:
                # Image-based PDF: try Vision LLM, fallback to OCR
                provider = get_llm_provider(llm_config)

                if provider.supports_vision():
                    logger.info("Using Vision LLM for image-based PDF")
                    loop = asyncio.get_event_loop()
                    extracted_lines = await loop.run_in_executor(
                        None, analyze_cv_images, pdf_content.images, llm_config
                    )
                else:
                    # Fallback: OCR → text LLM
                    logger.info("Vision not supported, using OCR fallback")
                    raw_text = ocr_images(pdf_content.images)
                    loop = asyncio.get_event_loop()
                    extracted_lines = await loop.run_in_executor(None, analyze_cv_text, raw_text, llm_config)

        elif filename_lower.endswith(".docx"):
            raw_text = extract_text_from_docx(content)
            loop = asyncio.get_event_loop()
            extracted_lines = await loop.run_in_executor(None, analyze_cv_text, raw_text, llm_config)
        else:
            await task_store.fail_task(task_id, "Unsupported file format")
            return

        # Complete task with result
        result = {
            "success": True,
            "extracted_lines": [line.model_dump() for line in extracted_lines],
            "raw_text": raw_text,
        }
        await task_store.complete_task(task_id, result)
        logger.info(f"Task {task_id}: extracted {len(extracted_lines)} lines from {filename}")

    except ValueError as e:
        logger.error(f"Task {task_id} extraction failed: {e}")
        await task_store.fail_task(task_id, str(e))

    except Exception as e:
        logger.error(f"Task {task_id} unexpected error: {e}")
        await task_store.fail_task(task_id, f"Unexpected error: {e}")


@app.post("/extract/async", response_model=TaskSubmitResponse)
async def submit_cv_extraction(
    file: Annotated[UploadFile, File(description="CV file (PDF or DOCX)")],
    background_tasks: BackgroundTasks,
    llm_endpoint: Annotated[str | None, Form(description="Custom LLM endpoint URL")] = None,
    llm_model: Annotated[str | None, Form(description="LLM model name")] = None,
    llm_api_key: Annotated[str | None, Form(description="LLM API key")] = None,
    llm_api_mode: Annotated[str | None, Form(description="API mode: openai_compatible or ollama_native")] = None,
    llm_max_tokens: Annotated[int | None, Form(description="Max tokens for LLM response")] = None,
):
    """
    Submit a CV for asynchronous extraction.

    Returns a task_id immediately. Use GET /extract/status/{task_id} to poll for results.

    Optionally accepts custom LLM configuration to override server defaults.
    If no LLM config is provided, uses environment variables.
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

    # Build LLM config if any custom parameters provided
    llm_config = None
    if llm_endpoint or llm_model or llm_api_key or llm_api_mode or llm_max_tokens:
        llm_config = LLMConfig(
            endpoint=llm_endpoint,
            model=llm_model,
            api_key=llm_api_key,
            api_mode=llm_api_mode,
            max_tokens=llm_max_tokens,
        )
        logger.info(
            f"Using custom LLM config: endpoint={llm_endpoint}, model={llm_model}, api_mode={llm_api_mode}, max_tokens={llm_max_tokens}"
        )

    # Create task and start background processing
    task_id = await task_store.create_task(filename=file.filename)
    background_tasks.add_task(process_cv_task, task_id, content, file.filename, llm_config)

    return TaskSubmitResponse(task_id=task_id)


@app.get("/extract/status/{task_id}", response_model=TaskStatusResponse)
async def get_extraction_status(task_id: str):
    """
    Get the status of an extraction task.

    Returns:
    - pending: Task is queued
    - processing: Extraction in progress
    - completed: Success, includes extracted_lines
    - failed: Error occurred, includes error message
    """
    task = await task_store.get_task(task_id)

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    response = TaskStatusResponse(
        task_id=task.task_id,
        status=task.status.value,
        created_at=task.created_at,
        updated_at=task.updated_at,
    )

    if task.status == TaskStatus.COMPLETED and task.result:
        response.success = task.result.get("success")
        response.extracted_lines = task.result.get("extracted_lines")
        response.raw_text = task.result.get("raw_text")
    elif task.status == TaskStatus.FAILED:
        response.success = False
        response.error = task.error

    return response


# Keep the synchronous endpoint for backwards compatibility
@app.post("/extract", response_model=ExtractionResponse)
async def extract_cv(
    file: Annotated[UploadFile, File(description="CV file (PDF or DOCX)")],
):
    """
    Extract structured information from a CV file (synchronous).

    Accepts PDF or DOCX files, extracts text, analyzes with LLM,
    and returns structured data.

    Note: For long-running extractions, consider using POST /extract/async instead.
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

    # Extract and analyze
    try:
        raw_text = None
        extracted_lines = []

        if filename_lower.endswith(".pdf"):
            # Smart PDF extraction
            pdf_content = extract_pdf_content(content)

            if pdf_content.is_text_based:
                raw_text = pdf_content.text
                extracted_lines = analyze_cv_text(raw_text)
            else:
                provider = get_llm_provider()
                if provider.supports_vision():
                    extracted_lines = analyze_cv_images(pdf_content.images)
                else:
                    raw_text = ocr_images(pdf_content.images)
                    extracted_lines = analyze_cv_text(raw_text)

        elif filename_lower.endswith(".docx"):
            raw_text = extract_text_from_docx(content)
            extracted_lines = analyze_cv_text(raw_text)
        else:
            raise HTTPException(status_code=400, detail="Unsupported file format")

    except ValueError as e:
        logger.error(f"Extraction/analysis failed: {e}")
        return ExtractionResponse(
            success=False,
            raw_text=raw_text,
            error=str(e),
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
