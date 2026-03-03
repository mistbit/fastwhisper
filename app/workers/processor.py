"""后台任务处理器"""
import asyncio
import logging
import os
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import settings
from app.core.database import SessionLocal
from app.services.aligner_service import transcript_aligner
from app.services.diarization_service import diarization_service
from app.services.llm_service import llm_service
from app.services.task_service import TaskService
from app.services.whisper_service import whisper_service

logger = logging.getLogger(__name__)


class TaskProcessor:
    """后台任务处理器"""

    def __init__(self):
        self._running = False
        self._semaphore = asyncio.Semaphore(settings.MAX_CONCURRENT_TASKS)

    async def start(self):
        """启动处理器"""
        self._running = True
        logger.info("Task processor started")

        while self._running:
            try:
                await self._process_pending_tasks()
            except Exception as e:
                logger.error(f"Error in task processor: {e}")

            await asyncio.sleep(1)

    def stop(self):
        """停止处理器"""
        self._running = False
        logger.info("Task processor stopped")

    async def _process_pending_tasks(self):
        """处理待处理的任务"""
        async with SessionLocal() as db:
            task_service = TaskService(db)

            # 查找待处理的任务
            from sqlalchemy import select
            from app.models.task import Task

            result = await db.execute(
                select(Task)
                .where(Task.status == "pending")
                .order_by(Task.created_at)
                .limit(settings.MAX_CONCURRENT_TASKS)
            )
            tasks = result.scalars().all()

            for task in tasks:
                # 启动任务处理（不等待完成）
                asyncio.create_task(self._process_task_with_semaphore(task.task_id))

    async def _process_task_with_semaphore(self, task_id: str):
        """使用信号量处理任务"""
        async with self._semaphore:
            await self._process_task(task_id)

    async def _process_task(self, task_id: str):
        """
        处理单个任务

        流程：
        1. 音频预处理
        2. Whisper 转录
        3. 说话人分离
        4. 结果对齐
        5. LLM 生成纪要
        """
        async with SessionLocal() as db:
            task_service = TaskService(db)

            try:
                task = await task_service.get_task(task_id)
                if not task:
                    logger.error(f"Task not found: {task_id}")
                    return

                logger.info(f"Processing task: {task_id}")

                # Stage 1: 预处理 (0-10%)
                await task_service.mark_processing(task_id, "preprocessing", 5)
                audio_path = task.file_path

                # Stage 2: Whisper 转录 (10-50%)
                await task_service.mark_processing(task_id, "transcribing", 10)
                transcript_result = await whisper_service.transcribe(
                    audio_path, task.language
                )
                await task_service.update_progress(task_id, progress=50)

                # Stage 3: 说话人分离 (50-70%)
                await task_service.mark_processing(task_id, "diarizing", 50)
                diarization_segments = await diarization_service.diarize(
                    audio_path,
                    num_speakers=task.speaker_count,
                )
                await task_service.update_progress(task_id, progress=70)

                # Stage 4: 对齐 (70-75%)
                aligned_segments = transcript_aligner.align(
                    transcript_result["segments"],
                    diarization_segments,
                )
                await task_service.update_progress(task_id, progress=75)

                # Stage 5: LLM 生成纪要 (75-95%)
                await task_service.mark_processing(task_id, "generating", 75)

                # 为说话人生成标签
                speaker_labels = await llm_service.summarize_speakers(aligned_segments)

                # 生成会议纪要
                full_text = transcript_result["text"]
                minutes = await llm_service.generate_minutes(full_text)
                await task_service.update_progress(task_id, progress=95)

                # Stage 6: 保存结果 (95-100%)
                await task_service.save_transcript(
                    task_id,
                    aligned_segments,
                    full_text,
                    transcript_result["language"],
                    speaker_labels,
                )

                await task_service.save_minutes(
                    task_id,
                    full_text,
                    transcript_result["language"],
                    minutes,
                )

                # 更新任务时长
                if transcript_result.get("duration"):
                    task.duration = transcript_result["duration"]
                    await db.commit()

                # 完成
                await task_service.mark_completed(task_id)
                logger.info(f"Task completed: {task_id}")

            except Exception as e:
                logger.error(f"Task failed: {task_id}, error: {e}")
                await task_service.mark_failed(task_id, str(e))


# 全局任务处理器实例
task_processor = TaskProcessor()