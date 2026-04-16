import uuid
from datetime import datetime
from typing import List, Optional

from sqlalchemy import (
    BigInteger,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

JSON_LIST = JSON().with_variant(JSONB, "postgresql")


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    task_id: Mapped[str] = mapped_column(
        String(36), unique=True, nullable=False, index=True, default=lambda: str(uuid.uuid4())
    )
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    file_size: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    duration: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    processing_started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Status
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending", index=True
    )  # pending/processing/completed/failed
    progress: Mapped[int] = mapped_column(Integer, default=0)
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    stage: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True
    )  # preprocessing/transcribing/diarizing/generating
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    last_error_code: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True, index=True
    )
    last_error_stage: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Config
    language: Mapped[str] = mapped_column(String(10), default="auto")
    speaker_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    asr_engine: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    heartbeat_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    lease_expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    worker_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)

    # Relationships
    segments: Mapped[List["TranscriptSegment"]] = relationship(
        "TranscriptSegment", back_populates="task", cascade="all, delete-orphan"
    )
    minutes: Mapped[Optional["MeetingMinutes"]] = relationship(
        "MeetingMinutes", back_populates="task", uselist=False, cascade="all, delete-orphan"
    )


class TranscriptSegment(Base):
    __tablename__ = "transcript_segments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    task_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("tasks.task_id"), nullable=False, index=True
    )

    # Speaker
    speaker: Mapped[str] = mapped_column(String(50), nullable=False)
    speaker_label: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Time
    start_time: Mapped[float] = mapped_column(Float, nullable=False)
    end_time: Mapped[float] = mapped_column(Float, nullable=False)

    # Content
    text: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Relationship
    task: Mapped["Task"] = relationship("Task", back_populates="segments")


class MeetingMinutes(Base):
    __tablename__ = "meeting_minutes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    task_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("tasks.task_id"), unique=True, nullable=False
    )

    # Content
    full_transcript: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    detected_language: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)

    # Minutes
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    key_points: Mapped[Optional[list]] = mapped_column(JSON_LIST, nullable=True)
    action_items: Mapped[Optional[list]] = mapped_column(JSON_LIST, nullable=True)
    decisions: Mapped[Optional[list]] = mapped_column(JSON_LIST, nullable=True)

    # Metadata
    model_used: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    tokens_used: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Timestamp
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationship
    task: Mapped["Task"] = relationship("Task", back_populates="minutes")
