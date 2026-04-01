"""后台任务处理器"""
import asyncio
import logging
import os
import socket
import uuid
from datetime import datetime, timezone

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
        self._active_tasks: set[asyncio.Task] = set()
        self.worker_id = f"{socket.gethostname()}-{os.getpid()}-{uuid.uuid4().hex[:8]}"

    async def start(self):
        """启动处理器"""
        if self._running:
            return

        self._running = True
        logger.info("Task processor started: worker_id=%s", self.worker_id)

        async with SessionLocal() as db:
            requeued = await TaskService(db).requeue_stale_processing_tasks(
                datetime.now(timezone.utc)
            )
            if requeued:
                logger.info("Requeued %s stale tasks at worker start", requeued)

        try:
            while self._running:
                await self._dispatch_pending_tasks()
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            logger.info("Task processor cancelled")
            raise
        finally:
            self._running = False
            if self._active_tasks:
                for task in list(self._active_tasks):
                    task.cancel()
                await asyncio.gather(*self._active_tasks, return_exceptions=True)
            logger.info("Task processor stopped")

    def stop(self):
        """停止处理器"""
        self._running = False

    def _prune_finished_tasks(self):
        self._active_tasks = {task for task in self._active_tasks if not task.done()}

    def _classify_failure(self, stage: str, exc: Exception) -> str:
        if isinstance(exc, FileNotFoundError):
            return "source_missing"

        stage_map = {
            "preprocessing": "preprocessing_error",
            "transcribing": "transcription_error",
            "diarizing": "diarization_error",
            "generating": "generation_error",
            "saving": "storage_error",
        }
        return stage_map.get(stage, "processing_error")

    async def _dispatch_pending_tasks(self):
        self._prune_finished_tasks()
        available_slots = settings.MAX_CONCURRENT_TASKS - len(self._active_tasks)
        if available_slots <= 0:
            return

        async with SessionLocal() as db:
            task_service = TaskService(db)
            requeued = await task_service.requeue_stale_processing_tasks(
                datetime.now(timezone.utc)
            )
            if requeued:
                logger.info("Requeued %s stale tasks while dispatching", requeued)

            task_ids = await task_service.claim_pending_tasks(
                available_slots,
                worker_id=self.worker_id,
                lease_seconds=settings.WORKER_LEASE_SECONDS,
            )

        for task_id in task_ids:
            task = asyncio.create_task(self._process_task(task_id))
            self._active_tasks.add(task)
            task.add_done_callback(self._active_tasks.discard)

    async def process_task_inline(self, task_id: str):
        """在 API 进程内直接处理任务，适用于本地最小可用模式。"""
        async with SessionLocal() as db:
            claimed = await TaskService(db).start_task(task_id)

        if not claimed:
            logger.info("Skip inline processing for task %s because it is no longer pending", task_id)
            return

        await self._run_task(task_id, with_heartbeat=False)

    async def _process_task(self, task_id: str):
        await self._run_task(task_id, with_heartbeat=True)

    async def _run_task(self, task_id: str, *, with_heartbeat: bool):
        """
        处理单个任务

        流程：
        1. 音频预处理
        2. Whisper 转录
        3. 说话人分离
        4. 结果对齐
        5. LLM 生成纪要
        6. 保存结果
        """
        async with SessionLocal() as db:
            task_service = TaskService(db)
            heartbeat_stop = asyncio.Event()
            heartbeat_task = None
            if with_heartbeat:
                heartbeat_task = asyncio.create_task(
                    self._heartbeat_loop(task_id, heartbeat_stop)
                )
            current_stage = "preprocessing"

            try:
                task = await task_service.get_task(task_id)
                if not task:
                    logger.error("Task not found: %s", task_id)
                    return

                logger.info("Processing task: %s", task_id)
                audio_path = task.file_path
                language = task.language
                speaker_count = task.speaker_count

                current_stage = "preprocessing"
                await task_service.mark_processing(task_id, "preprocessing", 5)

                current_stage = "transcribing"
                await task_service.mark_processing(task_id, "transcribing", 10)
                transcript_result = await whisper_service.transcribe(audio_path, language)
                await task_service.update_progress(task_id, progress=50)

                current_stage = "diarizing"
                await task_service.mark_processing(task_id, "diarizing", 50)
                diarization_segments = await diarization_service.diarize(
                    audio_path,
                    num_speakers=speaker_count,
                    transcript_segments=transcript_result["segments"],
                )
                await task_service.update_progress(task_id, progress=70)

                aligned_segments = transcript_aligner.align(
                    transcript_result["segments"],
                    diarization_segments,
                )
                await task_service.update_progress(task_id, progress=75)

                current_stage = "generating"
                await task_service.mark_processing(task_id, "generating", 75)
                speaker_labels = await llm_service.summarize_speakers(aligned_segments)
                full_text = transcript_result["text"]
                minutes = await llm_service.generate_minutes(
                    full_text,
                    segments=aligned_segments,
                )

                current_stage = "saving"
                await task_service.mark_processing(task_id, "saving", 95)
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

                if transcript_result.get("duration"):
                    task.duration = transcript_result["duration"]
                    await db.commit()

                await task_service.mark_completed(task_id)
                logger.info("Task completed: %s", task_id)
            except asyncio.CancelledError:
                logger.warning("Task cancelled before completion: %s", task_id)
                raise
            except Exception as exc:
                logger.error("Task failed: %s, error: %s", task_id, exc)
                await task_service.mark_failed(
                    task_id,
                    str(exc),
                    error_code=self._classify_failure(current_stage, exc),
                    error_stage=current_stage,
                )
            finally:
                heartbeat_stop.set()
                if heartbeat_task is not None:
                    heartbeat_task.cancel()
                    await asyncio.gather(heartbeat_task, return_exceptions=True)

    async def _heartbeat_loop(self, task_id: str, stop_event: asyncio.Event):
        """定期刷新 lease，防止活跃任务被误回收"""
        try:
            while True:
                try:
                    await asyncio.wait_for(
                        stop_event.wait(),
                        timeout=settings.WORKER_HEARTBEAT_SECONDS,
                    )
                    return
                except TimeoutError:
                    async with SessionLocal() as db:
                        alive = await TaskService(db).record_heartbeat(
                            task_id,
                            worker_id=self.worker_id,
                            lease_seconds=settings.WORKER_LEASE_SECONDS,
                        )
                    if not alive:
                        logger.warning(
                            "Stopped heartbeating task %s because lease ownership changed",
                            task_id,
                        )
                        return
        except asyncio.CancelledError:
            return


task_processor = TaskProcessor()
