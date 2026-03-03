"""Initial migration

Revision ID: 001
Revises:
Create Date: 2024-03-15

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create tasks table
    op.create_table(
        "tasks",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("task_id", sa.String(36), nullable=False),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("file_path", sa.String(500), nullable=False),
        sa.Column("file_size", sa.BigInteger(), nullable=True),
        sa.Column("duration", sa.Float(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("progress", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("stage", sa.String(50), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("language", sa.String(10), nullable=False, server_default="auto"),
        sa.Column("speaker_count", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("task_id"),
    )
    op.create_index("ix_tasks_id", "tasks", ["id"])
    op.create_index("ix_tasks_task_id", "tasks", ["task_id"])
    op.create_index("ix_tasks_status", "tasks", ["status"])

    # Create transcript_segments table
    op.create_table(
        "transcript_segments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("task_id", sa.String(36), nullable=False),
        sa.Column("speaker", sa.String(50), nullable=False),
        sa.Column("speaker_label", sa.String(100), nullable=True),
        sa.Column("start_time", sa.Float(), nullable=False),
        sa.Column("end_time", sa.Float(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.task_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_transcript_segments_id", "transcript_segments", ["id"])
    op.create_index("ix_transcript_segments_task_id", "transcript_segments", ["task_id"])

    # Create meeting_minutes table
    op.create_table(
        "meeting_minutes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("task_id", sa.String(36), nullable=False),
        sa.Column("full_transcript", sa.Text(), nullable=True),
        sa.Column("detected_language", sa.String(10), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("key_points", postgresql.JSONB(), nullable=True),
        sa.Column("action_items", postgresql.JSONB(), nullable=True),
        sa.Column("decisions", postgresql.JSONB(), nullable=True),
        sa.Column("model_used", sa.String(100), nullable=True),
        sa.Column("tokens_used", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.task_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("task_id"),
    )
    op.create_index("ix_meeting_minutes_id", "meeting_minutes", ["id"])


def downgrade() -> None:
    op.drop_index("ix_meeting_minutes_id", table_name="meeting_minutes")
    op.drop_table("meeting_minutes")

    op.drop_index("ix_transcript_segments_task_id", table_name="transcript_segments")
    op.drop_index("ix_transcript_segments_id", table_name="transcript_segments")
    op.drop_table("transcript_segments")

    op.drop_index("ix_tasks_status", table_name="tasks")
    op.drop_index("ix_tasks_task_id", table_name="tasks")
    op.drop_index("ix_tasks_id", table_name="tasks")
    op.drop_table("tasks")