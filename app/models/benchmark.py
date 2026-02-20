import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, Float, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import SessionStatus, TypingProfileType, WinnerType


class BenchmarkRun(Base):
    __tablename__ = "benchmark_runs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    profile: Mapped[TypingProfileType] = mapped_column(
        Enum(TypingProfileType, name="typing_profile_type"),
    )
    runs_per_driver: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[SessionStatus] = mapped_column(
        Enum(SessionStatus, name="session_status"), default=SessionStatus.PENDING
    )

    selenium_avg_wpm: Mapped[float | None] = mapped_column(Float, nullable=True)
    playwright_avg_wpm: Mapped[float | None] = mapped_column(Float, nullable=True)
    selenium_avg_browser_start: Mapped[float | None] = mapped_column(Float, nullable=True)
    playwright_avg_browser_start: Mapped[float | None] = mapped_column(Float, nullable=True)
    selenium_avg_memory_mb: Mapped[float | None] = mapped_column(Float, nullable=True)
    playwright_avg_memory_mb: Mapped[float | None] = mapped_column(Float, nullable=True)
    selenium_avg_cpu_percent: Mapped[float | None] = mapped_column(Float, nullable=True)
    playwright_avg_cpu_percent: Mapped[float | None] = mapped_column(Float, nullable=True)
    selenium_avg_accuracy: Mapped[float | None] = mapped_column(Float, nullable=True)
    playwright_avg_accuracy: Mapped[float | None] = mapped_column(Float, nullable=True)

    winner: Mapped[WinnerType | None] = mapped_column(
        Enum(WinnerType, name="winner_type"), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    sessions: Mapped[list["BotSession"]] = relationship(  # noqa: F821
        "BotSession", back_populates="benchmark", lazy="select"
    )
