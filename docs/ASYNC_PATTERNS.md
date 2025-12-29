# Async Patterns for Long-Running LLM Tasks

This document describes the patterns used in JobMatch for handling long-running LLM tasks (CV generation, cover letters, etc.) that take 20-60+ seconds to complete.

## The Problem

When a user triggers an AI generation task:
1. The GUI (Django) sends a request to the ai-assistant (FastAPI) service
2. The ai-assistant calls an LLM provider (OpenAI, Anthropic, Ollama)
3. LLM processing takes 20-60+ seconds
4. Django's default HTTP timeout is 10 seconds

**Result**: The request times out before the LLM finishes, showing an error to the user.

## The Solution: Task-Based Polling Pattern

Instead of waiting for the LLM to complete, we return immediately with a `task_id` and let the client poll for the result.

### Architecture Flow

```
┌──────────┐      POST /generate/cv        ┌───────────────┐
│  Django  │  ──────────────────────────>  │  ai-assistant │
│   GUI    │  <─ 200 OK {task_id: "abc"}   │   (FastAPI)   │
└──────────┘                               └───────────────┘
     │                                            │
     │                                            │ asyncio.create_task()
     │                                            │ (non-blocking)
     │                                            ▼
     │                                     ┌─────────────────┐
     │                                     │ Background Task │
     │                                     │  LLM Call...    │
     │                                     │  (30+ seconds)  │
     │                                     └─────────────────┘
     │                                            │
     │  GET /generate/status/{task_id}            │
     │  ────────────────────────────────>         │
     │  <── {status: "processing"}                │
     │                                            │
     │  (polling every 2s)                        │
     │  ────────────────────────────────>         │
     │  <── {status: "completed", content: "..."} │
     ▼                                            ▼
```

### Implementation Details

#### 1. FastAPI Endpoint (ai-assistant)

```python
# main.py
import asyncio

@app.post("/generate/cv", response_model=GenerateCVResponse)
async def generate_cv_endpoint(request: GenerateCVRequest):
    # Create a task ID immediately
    task_id = await task_store.create_task(conversation_id=request.application_id)

    # CRITICAL: Use asyncio.create_task() for TRUE async execution
    # BackgroundTasks doesn't work because it waits for async functions to complete
    asyncio.create_task(_generate_cv_task(task_id, request))

    # Return immediately with task_id
    return GenerateCVResponse(task_id=task_id, message="CV generation started")
```

#### 2. Background Task with Thread Execution

The LLM providers use synchronous HTTP libraries (OpenAI SDK, Anthropic SDK). To avoid blocking the asyncio event loop, we must run them in a separate thread:

```python
# chat_handler.py
async def generate_cv(candidate, job_offer, llm_config=None):
    import asyncio

    provider = get_llm_provider(llm_config)
    prompt = build_cv_prompt(candidate, job_offer)

    # CRITICAL: Run synchronous LLM call in thread to avoid blocking event loop
    response = await asyncio.to_thread(
        provider.chat,
        [{"role": "user", "content": prompt}],
        system_prompt,
    )
    return response
```

#### 3. Task Store (In-Memory)

```python
# task_store.py
class TaskStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class TaskStore:
    async def create_task(self, conversation_id=None) -> str:
        """Create a new task, return task_id"""

    async def update_status(self, task_id: str, status: TaskStatus):
        """Update task status"""

    async def complete_task(self, task_id: str, result: dict):
        """Mark task as completed with result"""

    async def fail_task(self, task_id: str, error: str):
        """Mark task as failed with error"""
```

#### 4. Status Endpoint

```python
@app.get("/generate/status/{task_id}", response_model=GenerationTaskStatusResponse)
async def get_generation_status(task_id: str):
    task = await task_store.get_task(task_id)

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    return GenerationTaskStatusResponse(
        status=task.status.value,  # "pending", "processing", "completed", "failed"
        content=task.result.get("content") if task.result else None,
        error=task.error,
    )
```

#### 5. Django View (Client Side)

```python
# views.py
@login_required
@require_POST
def application_generate_cv_view(request, application_id):
    response = requests.post(
        f"{ai_assistant_url}/generate/cv",
        json={...},
        timeout=10,  # Short timeout is OK - endpoint returns immediately
    )
    data = response.json()
    return JsonResponse({"task_id": data["task_id"]})


@login_required
@require_GET
def application_generation_status_view(request, application_id, task_id):
    response = requests.get(
        f"{ai_assistant_url}/generate/status/{task_id}",
        timeout=10,
    )
    return JsonResponse(response.json())
```

#### 6. JavaScript Client (Polling)

```javascript
async function generateCv() {
    // Start generation
    const response = await fetch(`/accounts/applications/${appId}/generate/cv/`, {
        method: 'POST',
        headers: {'X-CSRFToken': csrfToken}
    });
    const data = await response.json();

    // Poll for status
    pollStatus(data.task_id);
}

async function pollStatus(taskId) {
    const response = await fetch(`/accounts/applications/${appId}/generate/status/${taskId}/`);
    const data = await response.json();

    if (data.status === 'completed') {
        displayResult(data.content);
    } else if (data.status === 'failed') {
        showError(data.error);
    } else {
        // Still processing, poll again in 2 seconds
        setTimeout(() => pollStatus(taskId), 2000);
    }
}
```

## Common Pitfalls

### 1. Using `BackgroundTasks` with async functions

**DON'T:**
```python
background_tasks.add_task(_generate_cv_task, task_id, request)
```

This doesn't work because FastAPI's `BackgroundTasks` still waits for the async function to complete before sending the HTTP response.

**DO:**
```python
asyncio.create_task(_generate_cv_task(task_id, request))
```

### 2. Calling synchronous LLM APIs directly in async functions

**DON'T:**
```python
async def generate_cv(...):
    response = provider.chat(messages, system_prompt)  # BLOCKS EVENT LOOP!
```

**DO:**
```python
async def generate_cv(...):
    response = await asyncio.to_thread(provider.chat, messages, system_prompt)
```

### 3. Short timeout on POST request

The initial POST request to start generation should return in <1 second. If it takes longer, either:
- The task store creation is slow (shouldn't be)
- You're accidentally waiting for the LLM (wrong async pattern)

## Alternative: Server-Sent Events (SSE) for Streaming

For real-time token streaming (like ChatGPT), use SSE:

```python
@app.post("/chat/message/stream")
async def send_message_stream(request: ChatMessageRequest):
    def generate():
        for chunk in provider.chat_stream(messages, system_prompt):
            yield f"data: {json.dumps({'token': chunk})}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")
```

**Use polling for**: CV generation, cover letters (one-shot generation)
**Use SSE for**: Chat conversations (real-time token display)

## Files Reference

- `app/ai-assistant/src/main.py` - FastAPI endpoints
- `app/ai-assistant/src/task_store.py` - Task management
- `app/ai-assistant/src/llm/chat_handler.py` - LLM calls with `asyncio.to_thread`
- `app/gui/accounts/views.py` - Django views for starting/polling tasks
