import pytest
from sqlalchemy import update

from app.models.task import Task
from app.services.task_service import TaskService


@pytest.mark.asyncio
async def test_task_endpoints_cover_create_list_detail_progress_and_delete(client):
    response = await client.post(
        "/api/v1/tasks",
        files={"file": ("meeting.wav", b"fake-audio", "audio/wav")},
        data={"language": "auto"},
    )

    assert response.status_code == 201
    payload = response.json()
    task_id = payload["data"]["task_id"]

    detail_response = await client.get(f"/api/v1/tasks/{task_id}")
    progress_response = await client.get(f"/api/v1/tasks/{task_id}/progress")
    list_response = await client.get("/api/v1/tasks")

    assert detail_response.status_code == 200
    assert detail_response.json()["data"]["filename"] == "meeting.wav"
    assert detail_response.json()["data"]["attempt_count"] == 0
    assert progress_response.status_code == 200
    assert progress_response.json()["data"]["status"] == "pending"
    assert list_response.status_code == 200
    assert list_response.json()["data"]["total"] == 1

    delete_response = await client.delete(f"/api/v1/tasks/{task_id}")
    assert delete_response.status_code == 200


@pytest.mark.asyncio
async def test_minutes_endpoint_returns_transcript_and_summary(client, db_session):
    task_service = TaskService(db_session)
    task = await task_service.create_task(
        filename="completed.wav",
        file_path="/tmp/completed.wav",
    )

    await task_service.save_transcript(
        task.task_id,
        [
            {
                "speaker": "SPEAKER_00",
                "start": 0.0,
                "end": 1.0,
                "text": "先讨论发布计划",
                "confidence": 0.9,
            }
        ],
        "先讨论发布计划",
        "zh",
        {"SPEAKER_00": "主持人"},
    )
    await task_service.save_minutes(
        task.task_id,
        "先讨论发布计划",
        "zh",
        {
            "summary": "讨论了版本发布时间。",
            "key_points": [{"title": "版本计划", "content": "本周五发布"}],
            "action_items": [{"assignee": "Alice", "task": "准备发布说明", "deadline": "周四"}],
            "decisions": [{"topic": "发布时间", "decision": "本周五上线"}],
        },
    )
    await task_service.mark_completed(task.task_id)

    response = await client.get(f"/api/v1/tasks/{task.task_id}/minutes")

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["minutes"]["summary"] == "讨论了版本发布时间。"
    assert data["transcript"]["segments"][0]["speaker_label"] == "主持人"


@pytest.mark.asyncio
async def test_create_task_rejects_invalid_language(client):
    response = await client.post(
        "/api/v1/tasks",
        files={"file": ("meeting.wav", b"fake-audio", "audio/wav")},
        data={"language": "jp"},
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_retry_endpoint_requeues_failed_task(client, db_session):
    create_response = await client.post(
        "/api/v1/tasks",
        files={"file": ("retry.wav", b"fake-audio", "audio/wav")},
        data={"language": "auto"},
    )
    task_id = create_response.json()["data"]["task_id"]

    task_service = TaskService(db_session)
    await task_service.mark_failed(task_id, "upstream timeout")

    response = await client.post(f"/api/v1/tasks/{task_id}/retry")

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["status"] == "pending"
    assert data["progress"] == 0
    assert data["error_message"] is None


@pytest.mark.asyncio
async def test_retry_endpoint_rejects_non_failed_task(client):
    create_response = await client.post(
        "/api/v1/tasks",
        files={"file": ("retry.wav", b"fake-audio", "audio/wav")},
        data={"language": "auto"},
    )
    task_id = create_response.json()["data"]["task_id"]

    response = await client.post(f"/api/v1/tasks/{task_id}/retry")

    assert response.status_code == 409


@pytest.mark.asyncio
async def test_overview_endpoint_returns_status_counts_and_failure_breakdown(
    client,
    db_session,
):
    task_service = TaskService(db_session)
    completed = await task_service.create_task(
        filename="completed.wav",
        file_path="/tmp/completed.wav",
    )
    failed = await task_service.create_task(
        filename="failed.wav",
        file_path="/tmp/failed.wav",
    )
    await db_session.execute(
        update(Task)
        .where(Task.task_id == completed.task_id)
        .values(status="completed", attempt_count=1)
    )
    await db_session.execute(
        update(Task)
        .where(Task.task_id == failed.task_id)
        .values(
            status="failed",
            attempt_count=2,
            last_error_code="generation_error",
        )
    )
    await db_session.commit()

    response = await client.get("/api/v1/tasks/stats/overview")

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["total"] == 2
    assert data["completed"] == 1
    assert data["failed"] == 1
    assert data["retried"] == 1
    assert data["failure_breakdown"][0]["code"] == "generation_error"
    assert data["failure_breakdown"][0]["label"] == "纪要生成失败"
