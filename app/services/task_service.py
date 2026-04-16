"""任务管理服务"""
from collections import Counter
import logging
import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

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
        asr_engine: Optional[str] = None,
    ) -> Task:
        """创建新任务"""
        task = Task(
            task_id=str(uuid.uuid4()),
            filename=filename,
            file_path=file_path,
            file_size=file_size,
            language=language,
            speaker_count=speaker_count,
            asr_engine=asr_engine,
            status="pending",
            progress=0,
        )
        self.db.add(task)
        await self.db.commit()
        await self.db.refresh(task)
        return task

    async def get_task(
        self,
        task_id: str,
        *,
        include_related: bool = False,
    ) -> Optional[Task]:
        """获取任务"""
        query = select(Task).where(Task.task_id == task_id)
        if include_related:
            query = query.options(
                selectinload(Task.segments),
                selectinload(Task.minutes),
            )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def claim_pending_tasks(
        self,
        limit: int,
        *,
        worker_id: str,
        lease_seconds: int,
    ) -> list[str]:
        """原子领取待处理任务，避免重复消费"""
        if limit <= 0:
            return []

        now = datetime.now(timezone.utc)
        lease_expires_at = now + timedelta(seconds=lease_seconds)
        pending_ids = (
            select(Task.id)
            .where(Task.status == "pending")
            .order_by(Task.created_at)
            .limit(limit)
        )

        result = await self.db.execute(
            update(Task)
            .where(Task.id.in_(pending_ids))
            .where(Task.status == "pending")
            .values(
                status="processing",
                stage="queued",
                progress=0,
                processing_started_at=now,
                attempt_count=Task.attempt_count + 1,
                updated_at=now,
                heartbeat_at=now,
                lease_expires_at=lease_expires_at,
                worker_id=worker_id,
                error_message=None,
            )
            .returning(Task.task_id)
        )
        await self.db.commit()
        return list(result.scalars().all())

    async def start_task(
        self,
        task_id: str,
        *,
        worker_id: Optional[str] = None,
        lease_seconds: Optional[int] = None,
    ) -> bool:
        """将指定任务标记为开始处理，适用于本地 inline 模式。"""
        now = datetime.now(timezone.utc)
        values = {
            "status": "processing",
            "stage": "queued",
            "progress": 0,
            "processing_started_at": now,
            "attempt_count": Task.attempt_count + 1,
            "updated_at": now,
            "error_message": None,
            "last_error_code": None,
            "last_error_stage": None,
        }

        if worker_id and lease_seconds:
            values.update(
                heartbeat_at=now,
                lease_expires_at=now + timedelta(seconds=lease_seconds),
                worker_id=worker_id,
            )
        else:
            values.update(
                heartbeat_at=None,
                lease_expires_at=None,
                worker_id=None,
            )

        result = await self.db.execute(
            update(Task)
            .where(Task.task_id == task_id)
            .where(Task.status == "pending")
            .values(**values)
        )
        await self.db.commit()
        return (result.rowcount or 0) > 0

    async def requeue_stale_processing_tasks(self, stale_before: datetime) -> int:
        """仅回收 lease 已过期的处理中任务"""
        now = datetime.now(timezone.utc)
        result = await self.db.execute(
            update(Task)
            .where(Task.status == "processing")
            .where(Task.completed_at.is_(None))
            .where(Task.lease_expires_at.is_not(None))
            .where(Task.lease_expires_at < stale_before)
            .values(
                status="pending",
                progress=0,
                stage=None,
                updated_at=now,
                heartbeat_at=None,
                lease_expires_at=None,
                worker_id=None,
                error_message="Worker lease expired before task completion. Task requeued.",
                last_error_code="lease_expired",
                last_error_stage=Task.stage,
            )
        )
        await self.db.commit()
        return result.rowcount or 0

    async def requeue_inline_processing_tasks(self) -> int:
        """本地 inline 模式在重启后标记被中断的处理中任务，便于用户显式重试。"""
        now = datetime.now(timezone.utc)
        result = await self.db.execute(
            update(Task)
            .where(Task.status == "processing")
            .where(Task.completed_at.is_(None))
            .where(Task.worker_id.is_(None))
            .where(Task.lease_expires_at.is_(None))
            .values(
                status="failed",
                progress=0,
                stage="failed",
                updated_at=now,
                error_message="Local processing was interrupted. Please retry the task.",
                last_error_code="processing_interrupted",
                last_error_stage=Task.stage,
                processing_started_at=None,
            )
        )
        await self.db.commit()
        return result.rowcount or 0

    async def record_heartbeat(
        self,
        task_id: str,
        *,
        worker_id: str,
        lease_seconds: int,
    ) -> bool:
        """刷新任务 lease，表示当前 worker 仍在工作"""
        now = datetime.now(timezone.utc)
        lease_expires_at = now + timedelta(seconds=lease_seconds)
        result = await self.db.execute(
            update(Task)
            .where(Task.task_id == task_id)
            .where(Task.worker_id == worker_id)
            .where(Task.status == "processing")
            .values(
                heartbeat_at=now,
                lease_expires_at=lease_expires_at,
                updated_at=now,
            )
        )
        await self.db.commit()
        return (result.rowcount or 0) > 0

    async def update_progress(
        self,
        task_id: str,
        status: Optional[str] = None,
        progress: Optional[int] = None,
        stage: Optional[str] = None,
        error_message: Optional[str] = None,
        last_error_code: Optional[str] = None,
        last_error_stage: Optional[str] = None,
    ) -> None:
        """更新任务进度"""
        values = {"updated_at": datetime.now(timezone.utc)}

        if status:
            values["status"] = status
        if progress is not None:
            values["progress"] = progress
        if stage:
            values["stage"] = stage
        if error_message is not None:
            values["error_message"] = error_message
        if last_error_code is not None:
            values["last_error_code"] = last_error_code
        if last_error_stage is not None:
            values["last_error_stage"] = last_error_stage

        if status == "completed":
            values["completed_at"] = datetime.now(timezone.utc)
            values["heartbeat_at"] = None
            values["lease_expires_at"] = None
            values["worker_id"] = None
        elif status == "failed":
            values["heartbeat_at"] = None
            values["lease_expires_at"] = None
            values["worker_id"] = None

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

    async def mark_failed(
        self,
        task_id: str,
        error_message: str,
        *,
        error_code: Optional[str] = None,
        error_stage: Optional[str] = None,
    ) -> None:
        """标记任务失败"""
        await self.update_progress(
            task_id,
            status="failed",
            error_message=error_message,
            stage="failed",
            last_error_code=error_code,
            last_error_stage=error_stage,
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

    async def retry_task(self, task_id: str) -> Optional[Task]:
        """重试失败任务，清理旧结果并重新入队"""
        task = await self.get_task(task_id)
        if not task:
            return None

        if task.status != "failed":
            raise ValueError("Only failed tasks can be retried.")

        if not task.file_path or not os.path.exists(task.file_path):
            raise FileNotFoundError("Source audio file is missing.")

        await self.db.execute(
            TranscriptSegment.__table__.delete().where(
                TranscriptSegment.task_id == task_id
            )
        )
        await self.db.execute(
            MeetingMinutes.__table__.delete().where(
                MeetingMinutes.task_id == task_id
            )
        )
        await self.db.execute(
            update(Task)
            .where(Task.task_id == task_id)
            .values(
                status="pending",
                progress=0,
                stage=None,
                error_message=None,
                processing_started_at=None,
                completed_at=None,
                heartbeat_at=None,
                lease_expires_at=None,
                worker_id=None,
                last_error_code=None,
                last_error_stage=None,
                updated_at=datetime.now(timezone.utc),
            )
        )
        await self.db.commit()
        return await self.get_task(task_id)

    async def get_task_stats(self) -> dict:
        """获取任务概览统计"""
        rows = (
            await self.db.execute(
                select(
                    Task.status,
                    Task.created_at,
                    Task.processing_started_at,
                    Task.completed_at,
                    Task.updated_at,
                    Task.last_error_code,
                    Task.attempt_count,
                )
            )
        ).all()

        status_counts = Counter()
        failure_counts = Counter()
        queue_waits: list[float] = []
        processing_times: list[float] = []
        retried = 0

        for row in rows:
            status_counts[row.status] += 1
            if row.attempt_count and row.attempt_count > 1:
                retried += 1

            if row.processing_started_at and row.created_at:
                queue_waits.append(
                    max(
                        0.0,
                        (row.processing_started_at - row.created_at).total_seconds(),
                    )
                )

            if row.processing_started_at:
                end_time = None
                if row.status == "completed" and row.completed_at:
                    end_time = row.completed_at
                elif row.status == "failed" and row.updated_at:
                    end_time = row.updated_at

                if end_time:
                    processing_times.append(
                        max(
                            0.0,
                            (end_time - row.processing_started_at).total_seconds(),
                        )
                    )

            if row.status == "failed" and row.last_error_code:
                failure_counts[row.last_error_code] += 1

        failure_breakdown = [
            {"code": code, "count": count}
            for code, count in failure_counts.most_common(5)
        ]

        return {
            "total": len(rows),
            "pending": status_counts["pending"],
            "processing": status_counts["processing"],
            "completed": status_counts["completed"],
            "failed": status_counts["failed"],
            "retried": retried,
            "avg_queue_seconds": (
                round(sum(queue_waits) / len(queue_waits), 2)
                if queue_waits
                else None
            ),
            "avg_processing_seconds": (
                round(sum(processing_times) / len(processing_times), 2)
                if processing_times
                else None
            ),
            "failure_breakdown": failure_breakdown,
        }
