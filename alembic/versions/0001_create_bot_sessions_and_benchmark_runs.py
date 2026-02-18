from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    driver_type = postgresql.ENUM(
        "selenium", "playwright", name="driver_type", create_type=True
    )
    typing_profile_type = postgresql.ENUM(
        "beginner", "intermediate", "expert", "robot",
        name="typing_profile_type", create_type=True,
    )
    session_status = postgresql.ENUM(
        "pending", "running", "completed", "failed",
        name="session_status", create_type=True,
    )
    winner_type = postgresql.ENUM(
        "selenium", "playwright", "tie", name="winner_type", create_type=True
    )

    driver_type.create(op.get_bind(), checkfirst=True)
    typing_profile_type.create(op.get_bind(), checkfirst=True)
    session_status.create(op.get_bind(), checkfirst=True)
    winner_type.create(op.get_bind(), checkfirst=True)


    op.create_table(
        "benchmark_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "profile",
            sa.Enum("beginner", "intermediate", "expert", "robot",
                    name="typing_profile_type"),
            nullable=False,
        ),
        sa.Column("runs_per_driver", sa.Integer(), nullable=False, server_default="1"),
        sa.Column(
            "status",
            sa.Enum("pending", "running", "completed", "failed", name="session_status"),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("selenium_avg_wpm", sa.Float(), nullable=True),
        sa.Column("playwright_avg_wpm", sa.Float(), nullable=True),
        sa.Column("selenium_avg_browser_start", sa.Float(), nullable=True),
        sa.Column("playwright_avg_browser_start", sa.Float(), nullable=True),
        sa.Column("selenium_avg_memory_mb", sa.Float(), nullable=True),
        sa.Column("playwright_avg_memory_mb", sa.Float(), nullable=True),
        sa.Column(
            "winner",
            sa.Enum("selenium", "playwright", "tie", name="winner_type"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "bot_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "driver",
            sa.Enum("selenium", "playwright", name="driver_type"),
            nullable=False,
        ),
        sa.Column(
            "profile",
            sa.Enum("beginner", "intermediate", "expert", "robot",
                    name="typing_profile_type"),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Enum("pending", "running", "completed", "failed", name="session_status"),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("wpm", sa.Float(), nullable=True),
        sa.Column("accuracy", sa.Float(), nullable=True),
        sa.Column("duration_sec", sa.Float(), nullable=True),
        sa.Column("browser_start_ms", sa.Float(), nullable=True),
        sa.Column("peak_memory_mb", sa.Float(), nullable=True),
        sa.Column("peak_cpu_percent", sa.Float(), nullable=True),
        sa.Column("screenshot_before", sa.String(512), nullable=True),
        sa.Column("screenshot_after", sa.String(512), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("benchmark_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["benchmark_id"], ["benchmark_runs.id"], ondelete="SET NULL"
        ),
    )
    op.create_index("ix_bot_sessions_benchmark_id", "bot_sessions", ["benchmark_id"])


def downgrade() -> None:
    op.drop_index("ix_bot_sessions_benchmark_id", table_name="bot_sessions")
    op.drop_table("bot_sessions")
    op.drop_table("benchmark_runs")

    op.execute("DROP TYPE IF EXISTS driver_type")
    op.execute("DROP TYPE IF EXISTS typing_profile_type")
    op.execute("DROP TYPE IF EXISTS session_status")
    op.execute("DROP TYPE IF EXISTS winner_type")
