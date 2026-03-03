"""任务管理服务"""
import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.task import MeetingMinutes, Task, TranscriptSegment

logger = logging.getLogger(__name__)


class TaskService:
    """任务管理服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_task(
        self,
        filename: str,
        file_path: str,
        file_size: Optional[int] = None,
        language: str = "auto",
        speaker_count: Optional[int] = None,
    ) -> Task:
        """创建新任务"""
        task = Task(
            task_id=str(uuid.uuid4()),
            filename=filename,
            file_path=file_path,
            file_size=file_size,
            language=language,
            speaker_count=speaker_count,
            status="pending",
            progress=0,
        )
        self.db.add(task)
        await self.db.commit()
        await self.db.refresh(task)
        return task

    async def get_task(self, task_id: str) -> Optional[Task]:
        """获取任务"""
        result = await self.db.execute(select(Task).where(Task.task_id == task_id))
        return result.scalar_one_or_none()

    async def update_progress(
        self,
        task_id: str,
        status: Optional[str] = None,
        progress: Optional[int] = None,
        stage: Optional[str] = None,
        error_message: Optional[str] = None,
    ) -> None:
        """更新任务进度"""
        values = {"updated_at": datetime.now(timezone.utc)}

        if status:
            values["status"] = status
        if progress is not None:
            values["progress"] = progress
        if stage:
            values["stage"] = stage
        if error_message:
            values["error_message"] = error_message

        if status == "completed":
            values["completed_at"] = datetime.now(timezone.utc)

        await self.db.execute(
            update(Task).where(Task.task_id == task_id).values(**values)
        )
        await self.db.commit()

    async def mark_processing(self, task_id: str, stage: str, progress: int) -> None:
        """标记任务处理中"""
        await self.update_progress(
            task_id, status="processing", stage=stage, progress=progress
        )

    async def mark_completed(self, task_id: str) -> None:
        """标记任务完成"""
        await self.update_progress(task_id, status="completed", progress=100)

    async def mark_failed(self, task_id: str, error_message: str) -> None:
        """标记任务失败"""
        await self.update_progress(
            task_id, status="failed", error_message=error_message
        )

    async def save_transcript(
        self,
        task_id: str,
        segments: list[dict],
        full_text: str,
        detected_language: str,
        speaker_labels: Optional[dict] = None,
    ) -> None:
        """保存转录结果"""
        # 删除旧的片段（如果有）
        await self.db.execute(
            TranscriptSegment.__table__.delete().where(
                TranscriptSegment.task_id == task_id
            )
        )

        # 保存新片段
        for seg in segments:
            segment = TranscriptSegment(
                task_id=task_id,
                speaker=seg["speaker"],
                speaker_label=speaker_labels.get(seg["speaker"]) if speaker_labels else None,
                start_time=seg["start"],
                end_time=seg["end"],
                text=seg["text"],
                confidence=seg.get("confidence"),
            )
            self.db.add(segment)

        await self.db.commit()

    async def save_minutes(
        self,
        task_id: str,
        full_transcript: str,
        detected_language: str,
        minutes: dict,
    ) -> MeetingMinutes:
        """保存会议纪要"""
        # 删除旧的纪要（如果有）
        existing = await self.db.execute(
            select(MeetingMinutes).where(MeetingMinutes.task_id == task_id)
        )
        if existing.scalar_one_or_none():
            await self.db.execute(
                MeetingMinutes.__table__.delete().where(
                    MeetingMinutes.task_id == task_id
                )
            )

        meeting_minutes = MeetingMinutes(
            task_id=task_id,
            full_transcript=full_transcript,
            detected_language=detected_language,
            summary=minutes.get("summary"),
            key_points=minutes.get("key_points"),
            action_items=minutes.get("action_items"),
            decisions=minutes.get("decisions"),
            model_used=minutes.get("model_used"),
            tokens_used=minutes.get("tokens_used"),
        )
        self.db.add(meeting_minutes)
        await self.db.commit()
        await self.db.refresh(meeting_minutes)
        return meeting_minutes

    async def get_tasks(
        self,
        status: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Task], int]:
        """获取任务列表"""
        query = select(Task)

        if status:
            query = query.where(Task.status == status)

        # 使用 SQL COUNT 高效计算总数
        count_query = select(func.count(Task.id))
        if status:
            count_query = count_query.where(Task.status == status)
        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0

        # 分页
        query = query.order_by(Task.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)

        result = await self.db.execute(query)
        tasks = result.scalars().all()

        return list(tasks), total

    async def delete_task(self, task_id: str) -> bool:
        """删除任务"""
        task = await self.get_task(task_id)
        if not task:
            return False

        # 删除文件
        if task.file_path and os.path.exists(task.file_path):
            try:
                os.remove(task.file_path)
            except OSError as e:
                logger.warning(f"Failed to delete file {task.file_path}: {e}")

        # 删除数据库记录（级联删除会处理关联表）
        await self.db.delete(task)
        await self.db.commit()
        return True