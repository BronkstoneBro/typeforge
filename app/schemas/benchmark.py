from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.enums import TypingProfileType, SessionStatus, WinnerType


class BenchmarkRequest(BaseModel):
    """Request to run comparative benchmark"""
    profile: TypingProfileType
    runs_per_driver: int = Field(default=3, ge=1, le=10, description="Number of runs per driver (1-10)")


class DriverStats(BaseModel):
    """Aggregated statistics for a driver"""
    avg_wpm: Optional[float] = None
    avg_browser_start_ms: Optional[float] = None
    avg_memory_mb: Optional[float] = None
    avg_cpu_percent: Optional[float] = None
    avg_accuracy: Optional[float] = None


class BenchmarkResponse(BaseModel):
    """Response for benchmark run request"""
    benchmark_id: UUID
    profile: TypingProfileType
    status: SessionStatus
    selenium: DriverStats
    playwright: DriverStats
    winner: Optional[WinnerType] = None
    summary: Optional[str] = None

    class Config:
        from_attributes = True


class BenchmarkDetailResponse(BaseModel):
    """Detailed benchmark report"""
    id: UUID
    profile: TypingProfileType
    runs_per_driver: int
    status: SessionStatus
    selenium_avg_wpm: Optional[float] = None
    selenium_avg_browser_start: Optional[float] = None
    selenium_avg_memory_mb: Optional[float] = None
    selenium_avg_cpu_percent: Optional[float] = None
    selenium_avg_accuracy: Optional[float] = None
    playwright_avg_wpm: Optional[float] = None
    playwright_avg_browser_start: Optional[float] = None
    playwright_avg_memory_mb: Optional[float] = None
    playwright_avg_cpu_percent: Optional[float] = None
    playwright_avg_accuracy: Optional[float] = None
    winner: Optional[WinnerType] = None
    selenium_session_ids: list[UUID] = Field(default_factory=list)
    playwright_session_ids: list[UUID] = Field(default_factory=list)
    created_at: datetime
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class BenchmarkListItem(BaseModel):
    """Brief benchmark information for list view"""
    id: UUID
    profile: TypingProfileType
    runs_per_driver: int
    status: SessionStatus
    winner: Optional[WinnerType] = None
    created_at: datetime

    class Config:
        from_attributes = True


class BenchmarkListResponse(BaseModel):
    """Paginated list of benchmarks"""
    items: list[BenchmarkListItem]
    total: int
    page: int
    page_size: int
