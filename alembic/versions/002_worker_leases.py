"""Add worker lease columns

Revision ID: 002
Revises: 001
Create Date: 2026-04-01

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("tasks", sa.Column("heartbeat_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("tasks", sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("tasks", sa.Column("worker_id", sa.String(length=100), nullable=True))
    op.create_index("ix_tasks_lease_expires_at", "tasks", ["lease_expires_at"])
    op.create_index("ix_tasks_worker_id", "tasks", ["worker_id"])


def downgrade() -> None:
    op.drop_index("ix_tasks_worker_id", table_name="tasks")
    op.drop_index("ix_tasks_lease_expires_at", table_name="tasks")
    op.drop_column("tasks", "worker_id")
    op.drop_column("tasks", "lease_expires_at")
    op.drop_column("tasks", "heartbeat_at")
