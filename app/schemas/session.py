from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.enums import DriverType, TypingProfileType, SessionStatus


class SessionRunRequest(BaseModel):
    """Request to run single typing session"""
    driver: DriverType
    profile: TypingProfileType
    runs: int = Field(default=1, ge=1, le=10, description="Number of runs (1-10)")


class SessionRunResponse(BaseModel):
    """Response for session run request"""
    session_ids: list[UUID]
    status: SessionStatus
    avg_wpm: Optional[float] = None
    avg_accuracy: Optional[float] = None

    class Config:
        from_attributes = True


class SessionDetailResponse(BaseModel):
    """Detailed session information"""
    id: UUID
    driver: DriverType
    profile: TypingProfileType
    status: SessionStatus
    wpm: Optional[float] = None
    accuracy: Optional[float] = None
    duration_sec: Optional[float] = None
    browser_start_ms: Optional[float] = None
    peak_memory_mb: Optional[float] = None
    peak_cpu_percent: Optional[float] = None
    screenshot_before: Optional[str] = None
    screenshot_after: Optional[str] = None
    error_message: Optional[str] = None
    benchmark_id: Optional[UUID] = None
    created_at: datetime
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class SessionListItem(BaseModel):
    """Brief session information for list view"""
    id: UUID
    driver: DriverType
    profile: TypingProfileType
    status: SessionStatus
    wpm: Optional[float] = None
    accuracy: Optional[float] = None
    created_at: datetime

    class Config:
        from_attributes = True


class SessionListResponse(BaseModel):
    """Paginated list of sessions"""
    items: list[SessionListItem]
    total: int
    page: int
    page_size: int
