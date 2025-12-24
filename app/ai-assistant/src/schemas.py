"""Pydantic schemas for AI Assistant API."""

from enum import Enum

from pydantic import BaseModel


class CoachingType(str, Enum):
    """Types of coaching available."""

    STAR = "star"  # Professional success formalization
    PITCH = "pitch"  # 30s and 3min pitch creation


class LLMConfigRequest(BaseModel):
    """Optional LLM configuration from user settings (Premium+ only)."""

    llm_endpoint: str | None = None
    llm_model: str | None = None
    llm_api_key: str | None = None


class UserContext(BaseModel):
    """User context for personalized coaching."""

    first_name: str = ""
    last_name: str = ""
    location: str = ""
    profile_title: str = ""
    experiences: list[dict] = []
    interests: list[str] = []
    existing_successes: list[dict] = []  # For STAR: titles only, for PITCH: full STAR data
    skills: list[str] = []  # Hard and soft skills
    education: list[dict] = []  # Education history
    # AI autonomy level (1=Guided, 2=Assisted, 3=Collaborative, 4=Proactive, 5=Autonomous)
    autonomy_level: int = 3


class ChatStartRequest(BaseModel):
    """Request to start a new chat conversation."""

    conversation_id: int
    user_context: UserContext
    coaching_type: CoachingType = CoachingType.STAR
    llm_config: LLMConfigRequest | None = None  # Custom LLM config (Premium+)


class ChatStartResponse(BaseModel):
    """Response after starting a conversation."""

    task_id: str
    message: str = "Conversation started"


class ChatMessageRequest(BaseModel):
    """Request to send a message in a conversation."""

    conversation_id: int
    message: str
    history: list[dict] = []  # Previous messages for context
    user_context: UserContext | None = None
    coaching_type: CoachingType = CoachingType.STAR
    llm_config: LLMConfigRequest | None = None  # Custom LLM config (Premium+)


class ChatMessageResponse(BaseModel):
    """Response after sending a message (async)."""

    task_id: str


class TaskStatusResponse(BaseModel):
    """Response for task status check."""

    status: str  # pending, processing, completed, failed
    response: str | None = None  # LLM response if completed
    error: str | None = None  # Error message if failed
    extracted_data: dict | None = None  # Extracted STAR data if any


class ExtractSuccessRequest(BaseModel):
    """Request to extract STAR data from conversation."""

    conversation_id: int
    messages: list[dict]


class ExtractSuccessResponse(BaseModel):
    """Response with extracted STAR data."""

    title: str
    situation: str
    task: str
    action: str
    result: str
    skills_demonstrated: list[str]
    is_complete: bool


class ExtractPitchRequest(BaseModel):
    """Request to extract pitch from conversation."""

    conversation_id: int
    messages: list[dict]


class ExtractPitchResponse(BaseModel):
    """Response with extracted pitch data."""

    pitch_30s: str  # 30-second elevator pitch
    pitch_3min: str  # 3-minute detailed pitch
    key_strengths: list[str]  # Main strengths highlighted
    is_complete: bool


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    service: str
