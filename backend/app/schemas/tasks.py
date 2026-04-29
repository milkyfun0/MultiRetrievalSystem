from typing import Any

from pydantic import BaseModel


class JobStatusResponse(BaseModel):
    job_id: str
    state: str
    progress: int
    message: str | None = None
    error: str | None = None
    result: dict[str, Any] | None = None
    phase: str | None = None
    can_terminate: bool = False
    terminated_at: str | None = None
    terminate_reason: str | None = None


class TaskTerminateRequest(BaseModel):
    reason: str | None = None


class TaskTerminateResponse(BaseModel):
    job_id: str
    state: str
    message: str
    terminated_at: str | None = None
