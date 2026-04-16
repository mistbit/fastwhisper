"""任务 API 接口"""
import asyncio
from datetime import datetime, timezone
import logging
import os
from typing import Annotated, Literal, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    ERROR_CODE_LABELS,
    STAGE_DESCRIPTIONS,
    get_current_user,
    get_db,
    save_upload_file,
    validate_audio_file,
)
from app.core.config import settings
from app.schemas.task import (
    ApiResponse,
    MinutesDetailResponse,
    MinutesResponse,
    ProgressResponse,
    TaskDetailResponse,
    TaskListItem,
    TaskListResponse,
    TaskOverviewResponse,
    TaskResponse,
    TranscriptResponse,
    TranscriptSegmentResponse,
)
from app.services.task_service import TaskService
from app.workers.processor import task_processor

router = APIRouter(prefix="/tasks", tags=["tasks"])
logger = logging.getLogger(__name__)


def _normalize_datetime(value: Optional[datetime]) -> Optional[datetime]:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _calculate_queue_seconds(task) -> Optional[float]:
    processing_started_at = _normalize_datetime(task.processing_started_at)
    created_at = _normalize_datetime(task.created_at)
    if not processing_started_at or not created_at:
        return None
    return round(
        max(
            0.0,
            (processing_started_at - created_at).total_seconds(),
        ),
        2,
    )


def _calculate_processing_seconds(task) -> Optional[float]:
    processing_started_at = _normalize_datetime(task.processing_started_at)
    if not processing_started_at:
        return None

    end_time = None
    if task.status == "completed" and task.completed_at:
        end_time = _normalize_datetime(task.completed_at)
    elif task.status == "failed" and task.updated_at:
        end_time = _normalize_datetime(task.updated_at)
    elif task.status == "processing":
        end_time = datetime.now(timezone.utc)

    if not end_time:
        return None

    return round(
        max(
            0.0,
            (end_time - processing_started_at).total_seconds(),
        ),
        2,
    )


def _get_error_label(code: Optional[str]) -> Optional[str]:
    if not code:
        return None
    return ERROR_CODE_LABELS.get(code, code)


def build_task_list_item(task) -> TaskListItem:
    return TaskListItem(
        task_id=task.task_id,
        filename=task.filename,
        status=task.status,
        progress=task.progress,
        attempt_count=task.attempt_count,
        stage=task.stage,
        error_message=task.error_message,
        processing_started_at=_normalize_datetime(task.processing_started_at),
        processing_seconds=_calculate_processing_seconds(task),
        queue_seconds=_calculate_queue_seconds(task),
        last_error_code=task.last_error_code,
        last_error_label=_get_error_label(task.last_error_code),
        last_error_stage=task.last_error_stage,
        asr_engine=task.asr_engine,
        created_at=_normalize_datetime(task.created_at),
        completed_at=_normalize_datetime(task.completed_at),
    )


def build_task_detail_response(task) -> TaskDetailResponse:
    return TaskDetailResponse(
        task_id=task.task_id,
        filename=task.filename,
        file_size=task.file_size,
        status=task.status,
        progress=task.progress,
        attempt_count=task.attempt_count,
        stage=task.stage,
        stage_description=STAGE_DESCRIPTIONS.get(task.stage)
        if task.stage
        else None,
        error_message=task.error_message,
        processing_started_at=_normalize_datetime(task.processing_started_at),
        processing_seconds=_calculate_processing_seconds(task),
        queue_seconds=_calculate_queue_seconds(task),
        last_error_code=task.last_error_code,
        last_error_label=_get_error_label(task.last_error_code),
        last_error_stage=task.last_error_stage,
        language=task.language,
        speaker_count=task.speaker_count,
        asr_engine=task.asr_engine,
        duration=task.duration,
        created_at=_normalize_datetime(task.created_at),
        updated_at=_normalize_datetime(task.updated_at),
        completed_at=_normalize_datetime(task.completed_at),
    )


def build_progress_response(task, estimated_remaining: Optional[int]) -> ProgressResponse:
    return ProgressResponse(
        task_id=task.task_id,
        status=task.status,
        progress=task.progress,
        stage=task.stage,
        stage_description=STAGE_DESCRIPTIONS.get(task.stage)
        if task.stage
        else None,
        error_message=task.error_message,
        attempt_count=task.attempt_count,
        processing_started_at=_normalize_datetime(task.processing_started_at),
        processing_seconds=_calculate_processing_seconds(task),
        queue_seconds=_calculate_queue_seconds(task),
        last_error_code=task.last_error_code,
        last_error_label=_get_error_label(task.last_error_code),
        last_error_stage=task.last_error_stage,
        created_at=_normalize_datetime(task.created_at),
        updated_at=_normalize_datetime(task.updated_at),
        estimated_remaining=estimated_remaining,
    )


@router.post("", response_model=ApiResponse, status_code=status.HTTP_201_CREATED)
async def create_task(
    file: UploadFile = File(..., description="音频文件"),
    language: Annotated[
        Literal["auto", "zh", "en"],
        Form(description="语言: auto/zh/en"),
    ] = "auto",
    speaker_count: Annotated[
        Optional[int],
        Form(ge=1, le=20, description="预期说话人数量"),
    ] = None,
    asr_engine: Annotated[
        Optional[Literal["whisper", "sensevoice"]],
        Form(description="ASR引擎: whisper/sensevoice"),
    ] = None,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(get_current_user),
):
    """
    接口1: 提交任务

    上传音频文件，创建转录任务。
    """
    validate_audio_file(file)
    file_path, file_size = await save_upload_file(file)

    try:
        task_service = TaskService(db)
        task = await task_service.create_task(
            filename=file.filename or "unknown",
            file_path=file_path,
            file_size=file_size,
            language=language,
            speaker_count=speaker_count,
            asr_engine=asr_engine,
        )

        if settings.USE_INLINE_TASKS:
            asyncio.create_task(task_processor.process_task_inline(task.task_id))

        return ApiResponse(
            code=201,
            message="任务创建成功",
            data=TaskResponse(
                task_id=task.task_id,
                filename=task.filename,
                file_size=task.file_size,
                status=task.status,
                created_at=task.created_at,
            ),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create task: {e}")
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except OSError:
                pass
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create task",
        )


@router.get("/stats/overview", response_model=ApiResponse)
async def get_task_overview(
    db: AsyncSession = Depends(get_db),
    _: str = Depends(get_current_user),
):
    """获取任务总览统计"""
    stats = await TaskService(db).get_task_stats()
    return ApiResponse(
        data=TaskOverviewResponse(
            total=stats["total"],
            pending=stats["pending"],
            processing=stats["processing"],
            completed=stats["completed"],
            failed=stats["failed"],
            retried=stats["retried"],
            avg_queue_seconds=stats["avg_queue_seconds"],
            avg_processing_seconds=stats["avg_processing_seconds"],
            failure_breakdown=[
                {
                    "code": item["code"],
                    "label": _get_error_label(item["code"]),
                    "count": item["count"],
                }
                for item in stats["failure_breakdown"]
            ],
        )
    )


@router.get("/{task_id}", response_model=ApiResponse)
async def get_task_detail(
    task_id: str,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(get_current_user),
):
    """获取任务详情"""
    task_service = TaskService(db)
    task = await task_service.get_task(task_id)

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task not found: {task_id}",
        )

    return ApiResponse(
        data=build_task_detail_response(task)
    )


@router.post("/{task_id}/retry", response_model=ApiResponse)
async def retry_task(
    task_id: str,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(get_current_user),
):
    """重试失败任务"""
    task_service = TaskService(db)

    try:
        task = await task_service.retry_task(task_id)
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task not found: {task_id}",
        )

    if settings.USE_INLINE_TASKS:
        asyncio.create_task(task_processor.process_task_inline(task.task_id))

    return ApiResponse(
        message="任务已重新加入队列",
        data=build_task_detail_response(task),
    )


@router.get("/{task_id}/progress", response_model=ApiResponse)
async def get_progress(
    task_id: str,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(get_current_user),
):
    """
    接口2: 查询进度
    """
    task_service = TaskService(db)
    task = await task_service.get_task(task_id)

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task not found: {task_id}",
        )

    estimated_remaining = None
    if task.status == "processing" and task.duration:
        remaining_progress = 100 - task.progress
        if remaining_progress > 0:
            total_estimate = task.duration * 0.5
            estimated_remaining = int(total_estimate * remaining_progress / 100)

    return ApiResponse(data=build_progress_response(task, estimated_remaining))


@router.get("/{task_id}/minutes", response_model=ApiResponse)
async def get_minutes(
    task_id: str,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(get_current_user),
):
    """
    接口3: 获取会议纪要
    """
    task_service = TaskService(db)
    task = await task_service.get_task(task_id, include_related=True)

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task not found: {task_id}",
        )

    if task.status != "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Task is not completed. Current status: {task.status}",
        )

    segments = [
        TranscriptSegmentResponse(
            speaker=seg.speaker,
            speaker_label=seg.speaker_label,
            start_time=seg.start_time,
            end_time=seg.end_time,
            text=seg.text,
            confidence=seg.confidence,
        )
        for seg in task.segments
    ]

    minutes_data = task.minutes
    if not minutes_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Meeting minutes not found for this task",
        )

    minutes = MinutesResponse(
        summary=minutes_data.summary,
        key_points=minutes_data.key_points or [],
        action_items=minutes_data.action_items or [],
        decisions=minutes_data.decisions or [],
    )

    return ApiResponse(
        data=MinutesDetailResponse(
            task_id=task.task_id,
            transcript=TranscriptResponse(
                full_text=minutes_data.full_transcript,
                language=minutes_data.detected_language,
                segments=segments,
            ),
            minutes=minutes,
            created_at=minutes_data.created_at,
            model_used=minutes_data.model_used,
            tokens_used=minutes_data.tokens_used,
        )
    )


@router.get("", response_model=ApiResponse)
async def list_tasks(
    status: Annotated[
        Optional[Literal["pending", "processing", "completed", "failed"]],
        Query(),
    ] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(get_current_user),
):
    """获取任务列表"""
    task_service = TaskService(db)
    tasks, total = await task_service.get_tasks(
        status=status, page=page, page_size=page_size
    )

    return ApiResponse(
        data=TaskListResponse(
            items=[build_task_list_item(task) for task in tasks],
            total=total,
            page=page,
            page_size=page_size,
        )
    )


@router.delete("/{task_id}", response_model=ApiResponse)
async def delete_task(
    task_id: str,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(get_current_user),
):
    """删除任务"""
    task_service = TaskService(db)
    success = await task_service.delete_task(task_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task not found: {task_id}",
        )

    return ApiResponse(message="任务删除成功")
