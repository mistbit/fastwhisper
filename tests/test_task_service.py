from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select, update

from app.models.task import MeetingMinutes, Task, TranscriptSegment
from app.services.task_service import TaskService


@pytest.mark.asyncio
async def test_claim_pending_tasks_updates_status_and_avoids_duplicates(db_session):
    service = TaskService(db_session)

    created = []
    for index in range(3):
        task = await service.create_task(
            filename=f"meeting-{index}.wav",
            file_path=f"/tmp/meeting-{index}.wav",
        )
        created.append(task.task_id)

    first_claim = await service.claim_pending_tasks(
        2,
        worker_id="worker-a",
        lease_seconds=300,
    )
    second_claim = await service.claim_pending_tasks(
        2,
        worker_id="worker-b",
        lease_seconds=300,
    )

    assert len(first_claim) == 2
    assert len(second_claim) == 1
    assert set(first_claim).isdisjoint(second_claim)
    assert set(first_claim + second_claim) == set(created)

    tasks, _ = await service.get_tasks()
    assert sum(task.status == "processing" for task in tasks) == 3
    assert all(task.stage == "queued" for task in tasks)
    assert {task.worker_id for task in tasks} == {"worker-a", "worker-b"}
    assert all(task.lease_expires_at is not None for task in tasks)
    assert all(task.heartbeat_at is not None for task in tasks)


@pytest.mark.asyncio
async def test_requeue_stale_processing_tasks_only_requeues_expired_work(db_session):
    service = TaskService(db_session)
    task = await service.create_task(
        filename="meeting.wav",
        file_path="/tmp/meeting.wav",
    )

    await service.mark_processing(task.task_id, "transcribing", 10)
    expired_at = datetime.now(timezone.utc) - timedelta(seconds=5)
    await db_session.execute(
        update(Task)
        .where(Task.task_id == task.task_id)
        .values(
            worker_id="worker-a",
            heartbeat_at=expired_at,
            lease_expires_at=expired_at,
        )
    )
    await db_session.commit()

    reset_count = await service.requeue_stale_processing_tasks(datetime.now(timezone.utc))
    updated_task = await service.get_task(task.task_id)

    assert reset_count == 1
    assert updated_task is not None
    assert updated_task.status == "pending"
    assert updated_task.progress == 0
    assert updated_task.stage is None
    assert updated_task.worker_id is None
    assert updated_task.lease_expires_at is None
    assert "requeued" in (updated_task.error_message or "").lower()


@pytest.mark.asyncio
async def test_record_heartbeat_extends_current_worker_lease(db_session):
    service = TaskService(db_session)
    task = await service.create_task(
        filename="meeting.wav",
        file_path="/tmp/meeting.wav",
    )
    claimed_ids = await service.claim_pending_tasks(
        1,
        worker_id="worker-a",
        lease_seconds=30,
    )
    assert claimed_ids == [task.task_id]

    claimed_task = await service.get_task(task.task_id)
    original_expiry = claimed_task.lease_expires_at

    alive = await service.record_heartbeat(
        task.task_id,
        worker_id="worker-a",
        lease_seconds=120,
    )
    refreshed_task = await service.get_task(task.task_id)

    assert alive is True
    assert refreshed_task is not None
    assert refreshed_task.lease_expires_at > original_expiry


@pytest.mark.asyncio
async def test_retry_task_requeues_failed_task_and_clears_previous_results(
    db_session,
    tmp_path,
):
    service = TaskService(db_session)
    audio_path = tmp_path / "failed.wav"
    audio_path.write_bytes(b"audio")

    task = await service.create_task(
        filename="failed.wav",
        file_path=str(audio_path),
    )
    await service.save_transcript(
        task.task_id,
        [
            {
                "speaker": "SPEAKER_00",
                "start": 0.0,
                "end": 1.0,
                "text": "需要重试",
                "confidence": 0.9,
            }
        ],
        "需要重试",
        "zh",
        {"SPEAKER_00": "主持人"},
    )
    await service.save_minutes(
        task.task_id,
        "需要重试",
        "zh",
        {
            "summary": "旧纪要",
            "key_points": [],
            "action_items": [],
            "decisions": [],
        },
    )
    await service.mark_failed(task.task_id, "temporary error")

    retried = await service.retry_task(task.task_id)
    segments = (
        await db_session.execute(
            select(TranscriptSegment).where(TranscriptSegment.task_id == task.task_id)
        )
    ).scalars().all()
    minutes = (
        await db_session.execute(
            select(MeetingMinutes).where(MeetingMinutes.task_id == task.task_id)
        )
    ).scalar_one_or_none()

    assert retried is not None
    assert retried.status == "pending"
    assert retried.progress == 0
    assert retried.stage is None
    assert retried.error_message is None
    assert retried.completed_at is None
    assert segments == []
    assert minutes is None


@pytest.mark.asyncio
async def test_retry_task_rejects_non_failed_tasks(db_session, tmp_path):
    service = TaskService(db_session)
    audio_path = tmp_path / "pending.wav"
    audio_path.write_bytes(b"audio")

    task = await service.create_task(
        filename="pending.wav",
        file_path=str(audio_path),
    )

    with pytest.raises(ValueError, match="Only failed tasks can be retried"):
        await service.retry_task(task.task_id)


@pytest.mark.asyncio
async def test_get_task_stats_summarizes_counts_durations_and_failures(db_session):
    service = TaskService(db_session)
    now = datetime.now(timezone.utc)

    completed = await service.create_task(
        filename="completed.wav",
        file_path="/tmp/completed.wav",
    )
    failed = await service.create_task(
        filename="failed.wav",
        file_path="/tmp/failed.wav",
    )

    await db_session.execute(
        update(Task)
        .where(Task.task_id == completed.task_id)
        .values(
            status="completed",
            attempt_count=1,
            created_at=now - timedelta(minutes=12),
            processing_started_at=now - timedelta(minutes=10),
            completed_at=now - timedelta(minutes=4),
            updated_at=now - timedelta(minutes=4),
        )
    )
    await db_session.execute(
        update(Task)
        .where(Task.task_id == failed.task_id)
        .values(
            status="failed",
            attempt_count=2,
            created_at=now - timedelta(minutes=9),
            processing_started_at=now - timedelta(minutes=8),
            updated_at=now - timedelta(minutes=6),
            last_error_code="generation_error",
            last_error_stage="generating",
            error_message="llm timeout",
        )
    )
    await db_session.commit()

    stats = await service.get_task_stats()

    assert stats["total"] == 2
    assert stats["completed"] == 1
    assert stats["failed"] == 1
    assert stats["retried"] == 1
    assert stats["avg_queue_seconds"] == 90.0
    assert stats["avg_processing_seconds"] == 240.0
    assert stats["failure_breakdown"] == [{"code": "generation_error", "count": 1}]
