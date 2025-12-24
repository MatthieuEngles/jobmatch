"""AI Assistant FastAPI service for STAR and Pitch coaching."""

import json
import logging

from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from .config import settings
from .llm.chat_handler import (
    extract_pitch_data,
    extract_star_data,
    get_initial_message_async,
    process_chat_message,
    stream_chat_message,
    stream_initial_message,
)
from .llm.providers import LLMConfig
from .schemas import (
    ChatMessageRequest,
    ChatMessageResponse,
    ChatStartRequest,
    ChatStartResponse,
    ExtractPitchRequest,
    ExtractPitchResponse,
    ExtractSuccessRequest,
    ExtractSuccessResponse,
    HealthResponse,
    LLMConfigRequest,
    TaskStatusResponse,
)
from .task_store import TaskStatus, task_store

# Configure logging
logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="AI Assistant Service",
    description="AI-powered coaching for professional success (STAR) and pitch creation",
    version="1.1.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return HealthResponse(status="healthy", service=settings.SERVICE_NAME)


def _build_llm_config(config_request: LLMConfigRequest | None) -> LLMConfig | None:
    """Convert LLMConfigRequest to LLMConfig for providers."""
    if not config_request:
        return None
    if not config_request.llm_endpoint:
        return None
    return LLMConfig(
        endpoint=config_request.llm_endpoint,
        model=config_request.llm_model,
        api_key=config_request.llm_api_key,
    )


async def _generate_initial_message_task(
    task_id: str,
    request: ChatStartRequest,
):
    """Background task to generate the initial message."""
    try:
        await task_store.update_status(task_id, TaskStatus.PROCESSING)

        # Build LLM config from request (Premium+ users)
        llm_config = _build_llm_config(request.llm_config)

        # Generate initial message using LLM
        initial_message = await get_initial_message_async(
            request.user_context,
            coaching_type=request.coaching_type,
            llm_config=llm_config,
        )

        # Complete the task
        await task_store.complete_task(
            task_id,
            {"response": initial_message, "extracted_data": None},
        )

    except Exception as e:
        logger.error(f"Initial message generation failed: {e}")
        await task_store.fail_task(task_id, str(e))


@app.post("/chat/start", response_model=ChatStartResponse)
async def start_conversation(
    request: ChatStartRequest,
    background_tasks: BackgroundTasks,
):
    """Start a new coaching conversation.

    Supports both STAR (professional success) and PITCH coaching types.
    Generates a proactive initial message using the LLM based on user context.
    """
    try:
        # Create task for tracking
        task_id = await task_store.create_task(conversation_id=request.conversation_id)

        # Schedule background processing for initial message
        background_tasks.add_task(_generate_initial_message_task, task_id, request)

        return ChatStartResponse(task_id=task_id, message="Conversation started")

    except Exception as e:
        logger.error(f"Failed to start conversation: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


async def _process_message_task(
    task_id: str,
    request: ChatMessageRequest,
):
    """Background task to process a chat message."""
    try:
        await task_store.update_status(task_id, TaskStatus.PROCESSING)

        # Build LLM config from request (Premium+ users)
        llm_config = _build_llm_config(request.llm_config)

        # Process the message with coaching type
        response = await process_chat_message(
            message=request.message,
            history=request.history,
            user_context=request.user_context,
            coaching_type=request.coaching_type,
            llm_config=llm_config,
        )

        # Complete the task
        await task_store.complete_task(
            task_id,
            {"response": response, "extracted_data": None},
        )

    except Exception as e:
        logger.error(f"Message processing failed: {e}")
        await task_store.fail_task(task_id, str(e))


@app.post("/chat/message/async", response_model=ChatMessageResponse)
async def send_message_async(
    request: ChatMessageRequest,
    background_tasks: BackgroundTasks,
):
    """Send a message and get a task ID for polling.

    The actual LLM processing happens in the background.
    Use /chat/message/status/{task_id} to poll for the response.
    """
    try:
        # Create task
        task_id = await task_store.create_task(conversation_id=request.conversation_id)

        # Schedule background processing
        background_tasks.add_task(_process_message_task, task_id, request)

        return ChatMessageResponse(task_id=task_id)

    except Exception as e:
        logger.error(f"Failed to queue message: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.get("/chat/message/status/{task_id}", response_model=TaskStatusResponse)
async def get_message_status(task_id: str):
    """Poll for the status of an async message.

    Returns:
        - status: pending, processing, completed, or failed
        - response: The assistant's response (if completed)
        - error: Error message (if failed)
    """
    task = await task_store.get_task(task_id)

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    response_data = None
    extracted_data = None

    if task.status == TaskStatus.COMPLETED and task.result:
        response_data = task.result.get("response")
        extracted_data = task.result.get("extracted_data")

    return TaskStatusResponse(
        status=task.status.value,
        response=response_data,
        error=task.error,
        extracted_data=extracted_data,
    )


def _sse_generator(token_generator):
    """Convert a token generator to SSE format.

    SSE format: data: <content>\n\n
    Final event: data: [DONE]\n\n
    """
    try:
        for token in token_generator:
            # Ensure token is a string
            if token is None:
                continue
            if not isinstance(token, str):
                token = str(token)
            # Escape newlines for SSE (each data line is separate)
            escaped = token.replace("\n", "\\n")
            yield f"data: {json.dumps({'token': escaped})}\n\n"
        yield "data: [DONE]\n\n"
    except Exception as e:
        logger.exception(f"SSE stream error: {e}")
        yield f"data: {json.dumps({'error': str(e)})}\n\n"


@app.post("/chat/start/stream")
async def start_conversation_stream(request: ChatStartRequest):
    """Start a new coaching conversation with streaming response.

    Returns an SSE stream of tokens as they are generated.
    """
    logger.info(f"Starting streaming conversation for coaching_type={request.coaching_type}")

    llm_config = _build_llm_config(request.llm_config)

    def generate():
        return _sse_generator(
            stream_initial_message(
                request.user_context,
                coaching_type=request.coaching_type,
                llm_config=llm_config,
            )
        )

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        },
    )


@app.post("/chat/message/stream")
async def send_message_stream(request: ChatMessageRequest):
    """Send a message and get a streaming response.

    Returns an SSE stream of tokens as they are generated.
    """
    logger.info(f"Starting streaming message for coaching_type={request.coaching_type}")

    llm_config = _build_llm_config(request.llm_config)

    def generate():
        return _sse_generator(
            stream_chat_message(
                message=request.message,
                history=request.history,
                user_context=request.user_context,
                coaching_type=request.coaching_type,
                llm_config=llm_config,
            )
        )

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        },
    )


@app.post("/chat/extract-success", response_model=ExtractSuccessResponse)
async def extract_success(request: ExtractSuccessRequest):
    """Extract STAR data from a conversation.

    Analyzes the conversation messages and extracts structured
    STAR components (Situation, Task, Action, Result).
    """
    try:
        data = await extract_star_data(request.messages)

        return ExtractSuccessResponse(
            title=data["title"],
            situation=data["situation"],
            task=data["task"],
            action=data["action"],
            result=data["result"],
            skills_demonstrated=data["skills_demonstrated"],
            is_complete=data["is_complete"],
        )

    except Exception as e:
        logger.error(f"STAR extraction failed: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.post("/chat/extract-pitch", response_model=ExtractPitchResponse)
async def extract_pitch(request: ExtractPitchRequest):
    """Extract pitch data from a conversation.

    Analyzes the conversation messages and extracts structured
    pitch components (30s pitch, 3min pitch, key strengths).
    """
    try:
        data = await extract_pitch_data(request.messages)

        return ExtractPitchResponse(
            pitch_30s=data["pitch_30s"],
            pitch_3min=data["pitch_3min"],
            key_strengths=data["key_strengths"],
            is_complete=data["is_complete"],
        )

    except Exception as e:
        logger.error(f"Pitch extraction failed: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8084)  # nosec B104 - Docker container binding
