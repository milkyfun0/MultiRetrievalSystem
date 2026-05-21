from typing import Any, Optional

from pydantic import BaseModel


class JobStatusResponse(BaseModel):
    job_id: str
    state: str
    progress: int
    message: Optional[str] = None
    error: Optional[str] = None
    result: Optional[dict[str, Any]] = None
    phase: Optional[str] = None
    can_terminate: bool = False
    terminated_at: Optional[str] = None
    terminate_reason: Optional[str] = None


class TaskTerminateRequest(BaseModel):
    reason: Optional[str] = None


class TaskTerminateResponse(BaseModel):
    job_id: str
    state: str
    message: str
    terminated_at: Optional[str] = None
