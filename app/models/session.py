import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import DriverType, SessionStatus, TypingProfileType


class BotSession(Base):
    __tablename__ = "bot_sessions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    driver: Mapped[DriverType] = mapped_column(Enum(DriverType, name="driver_type"))
    profile: Mapped[TypingProfileType] = mapped_column(
        Enum(TypingProfileType, name="typing_profile_type")
    )
    status: Mapped[SessionStatus] = mapped_column(
        Enum(SessionStatus, name="session_status"), default=SessionStatus.PENDING
    )

    wpm: Mapped[float | None] = mapped_column(Float, nullable=True)
    accuracy: Mapped[float | None] = mapped_column(Float, nullable=True)
    duration_sec: Mapped[float | None] = mapped_column(Float, nullable=True)

    browser_start_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    peak_memory_mb: Mapped[float | None] = mapped_column(Float, nullable=True)
    peak_cpu_percent: Mapped[float | None] = mapped_column(Float, nullable=True)

    screenshot_before: Mapped[str | None] = mapped_column(String(512), nullable=True)
    screenshot_after: Mapped[str | None] = mapped_column(String(512), nullable=True)

    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    benchmark_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("benchmark_runs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    benchmark: Mapped["BenchmarkRun | None"] = relationship(  # noqa: F821
        "BenchmarkRun", back_populates="sessions"
    )
