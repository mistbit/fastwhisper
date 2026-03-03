"""任务 API 接口"""
import logging
import os
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    STAGE_DESCRIPTIONS,
    get_current_user,
    get_db,
    save_upload_file,
    validate_audio_file,
)
from app.schemas.task import (
    ApiResponse,
    MinutesDetailResponse,
    MinutesResponse,
    ProgressResponse,
    TaskListItem,
    TaskListResponse,
    TaskResponse,
    TranscriptResponse,
    TranscriptSegmentResponse,
)
from app.services.task_service import TaskService

router = APIRouter(prefix="/tasks", tags=["tasks"])
logger = logging.getLogger(__name__)


@router.post("", response_model=ApiResponse, status_code=status.HTTP_201_CREATED)
async def create_task(
    file: UploadFile = File(..., description="音频文件"),
    language: str = Form(default="auto", description="语言: auto/zh/en"),
    speaker_count: Optional[int] = Form(default=None, description="预期说话人数量"),
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
        )

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

    return ApiResponse(
        data=ProgressResponse(
            task_id=task.task_id,
            status=task.status,
            progress=task.progress,
            stage=task.stage,
            stage_description=STAGE_DESCRIPTIONS.get(task.stage)
            if task.stage
            else None,
            created_at=task.created_at,
            updated_at=task.updated_at,
            estimated_remaining=estimated_remaining,
        )
    )


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
    task = await task_service.get_task(task_id)

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
        )
    )


@router.get("", response_model=ApiResponse)
async def list_tasks(
    status: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
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
            items=[
                TaskListItem(
                    task_id=task.task_id,
                    filename=task.filename,
                    status=task.status,
                    progress=task.progress,
                    created_at=task.created_at,
                    completed_at=task.completed_at,
                )
                for task in tasks
            ],
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