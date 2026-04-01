"""Add task observability columns

Revision ID: 003
Revises: 002
Create Date: 2026-04-01

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "tasks",
        sa.Column("processing_started_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "tasks",
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "tasks",
        sa.Column("last_error_code", sa.String(length=50), nullable=True),
    )
    op.add_column(
        "tasks",
        sa.Column("last_error_stage", sa.String(length=50), nullable=True),
    )
    op.create_index("ix_tasks_last_error_code", "tasks", ["last_error_code"])
    op.alter_column("tasks", "attempt_count", server_default=None)


def downgrade() -> None:
    op.drop_index("ix_tasks_last_error_code", table_name="tasks")
    op.drop_column("tasks", "last_error_stage")
    op.drop_column("tasks", "last_error_code")
    op.drop_column("tasks", "attempt_count")
    op.drop_column("tasks", "processing_started_at")
