from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "benchmark_runs",
        sa.Column("selenium_avg_cpu_percent", sa.Float(), nullable=True)
    )
    op.add_column(
        "benchmark_runs",
        sa.Column("playwright_avg_cpu_percent", sa.Float(), nullable=True)
    )
    op.add_column(
        "benchmark_runs",
        sa.Column("selenium_avg_accuracy", sa.Float(), nullable=True)
    )
    op.add_column(
        "benchmark_runs",
        sa.Column("playwright_avg_accuracy", sa.Float(), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("benchmark_runs", "playwright_avg_accuracy")
    op.drop_column("benchmark_runs", "selenium_avg_accuracy")
    op.drop_column("benchmark_runs", "playwright_avg_cpu_percent")
    op.drop_column("benchmark_runs", "selenium_avg_cpu_percent")
