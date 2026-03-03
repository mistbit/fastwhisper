import asyncio
import logging
from typing import List, Optional

import torch

from app.core.config import settings

logger = logging.getLogger(__name__)


class DiarizationService:
    """说话人分离服务"""

    _instance: Optional["DiarizationService"] = None
    _pipeline = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._pipeline is None:
            self._initialize_pipeline()

    def _initialize_pipeline(self):
        """初始化 pyannote 说话人分离模型"""
        try:
            from pyannote.audio import Pipeline

            logger.info("Loading diarization pipeline...")
            self._pipeline = Pipeline.from_pretrained(
                "pyannote/speaker-diarization-3.1",
                use_auth_token=settings.HUGGINGFACE_TOKEN,
            )

            if torch.cuda.is_available() and settings.WHISPER_DEVICE == "cuda":
                self._pipeline = self._pipeline.to(torch.device("cuda"))

            logger.info("Diarization pipeline loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load diarization pipeline: {e}")
            raise

    async def diarize(
        self,
        audio_path: str,
        num_speakers: Optional[int] = None,
        min_speakers: int = 2,
        max_speakers: int = 10,
    ) -> List[dict]:
        """
        执行说话人分离

        Args:
            audio_path: 音频文件路径
            num_speakers: 预期说话人数量（如果已知）
            min_speakers: 最小说话人数量
            max_speakers: 最大说话人数量

        Returns:
            [
                {"speaker": "SPEAKER_01", "start": 0.0, "end": 5.5},
                {"speaker": "SPEAKER_02", "start": 5.5, "end": 10.0},
                ...
            ]
        """
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            self._diarize_sync,
            audio_path,
            num_speakers,
            min_speakers,
            max_speakers,
        )
        return result

    def _diarize_sync(
        self,
        audio_path: str,
        num_speakers: Optional[int],
        min_speakers: int,
        max_speakers: int,
    ) -> List[dict]:
        """同步执行说话人分离"""
        kwargs = {}
        if num_speakers:
            kwargs["num_speakers"] = num_speakers
        else:
            kwargs["min_speakers"] = min_speakers
            kwargs["max_speakers"] = max_speakers

        diarization = self._pipeline(audio_path, **kwargs)

        segments = []
        for turn, _, speaker in diarization.itertracks(yield_label=True):
            segments.append(
                {
                    "speaker": speaker,
                    "start": turn.start,
                    "end": turn.end,
                }
            )

        return segments

    def get_speaker_count(self, segments: List[dict]) -> int:
        """获取说话人数量"""
        speakers = set(seg["speaker"] for seg in segments)
        return len(speakers)


# 单例实例
diarization_service = DiarizationService()