"""In-memory task store for async chat processing."""

import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class TaskStatus(str, Enum):
    """Task processing status."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class Task:
    """Represents an async processing task."""

    task_id: str
    status: TaskStatus
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    result: dict[str, Any] | None = None
    error: str | None = None
    conversation_id: int | None = None


class TaskStore:
    """Thread-safe in-memory task store."""

    def __init__(self, max_tasks: int = 1000, cleanup_after_hours: int = 1):
        self._tasks: dict[str, Task] = {}
        self._lock = asyncio.Lock()
        self._max_tasks = max_tasks
        self._cleanup_after_hours = cleanup_after_hours

    async def create_task(self, conversation_id: int | None = None) -> str:
        """Create a new task and return its ID."""
        task_id = str(uuid.uuid4())
        task = Task(
            task_id=task_id,
            status=TaskStatus.PENDING,
            conversation_id=conversation_id,
        )

        async with self._lock:
            # Cleanup old tasks if we're at capacity
            if len(self._tasks) >= self._max_tasks:
                await self._cleanup_old_tasks()

            self._tasks[task_id] = task

        logger.info(f"Created task {task_id} for conversation: {conversation_id}")
        return task_id

    async def get_task(self, task_id: str) -> Task | None:
        """Get a task by ID."""
        async with self._lock:
            return self._tasks.get(task_id)

    async def update_status(self, task_id: str, status: TaskStatus) -> None:
        """Update task status."""
        async with self._lock:
            if task_id in self._tasks:
                self._tasks[task_id].status = status
                self._tasks[task_id].updated_at = datetime.utcnow()
                logger.debug(f"Task {task_id} status updated to {status}")

    async def complete_task(self, task_id: str, result: dict[str, Any]) -> None:
        """Mark task as completed with result."""
        async with self._lock:
            if task_id in self._tasks:
                self._tasks[task_id].status = TaskStatus.COMPLETED
                self._tasks[task_id].result = result
                self._tasks[task_id].updated_at = datetime.utcnow()
                logger.info(f"Task {task_id} completed successfully")

    async def fail_task(self, task_id: str, error: str) -> None:
        """Mark task as failed with error message."""
        async with self._lock:
            if task_id in self._tasks:
                self._tasks[task_id].status = TaskStatus.FAILED
                self._tasks[task_id].error = error
                self._tasks[task_id].updated_at = datetime.utcnow()
                logger.error(f"Task {task_id} failed: {error}")

    async def _cleanup_old_tasks(self) -> None:
        """Remove tasks older than cleanup_after_hours."""
        from datetime import timedelta

        cutoff = datetime.utcnow() - timedelta(hours=self._cleanup_after_hours)
        to_remove = [
            task_id
            for task_id, task in self._tasks.items()
            if task.created_at < cutoff and task.status in (TaskStatus.COMPLETED, TaskStatus.FAILED)
        ]

        for task_id in to_remove:
            del self._tasks[task_id]

        if to_remove:
            logger.info(f"Cleaned up {len(to_remove)} old tasks")


# Global task store instance
task_store = TaskStore()
