import asyncio
import logging
from typing import Callable, List, Optional

from faster_whisper import WhisperModel

from app.core.config import settings

logger = logging.getLogger(__name__)


class WhisperService:
    """Whisper 转录服务"""

    _instance: Optional["WhisperService"] = None
    _model: Optional[WhisperModel] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._model is None:
            self._initialize_model()

    def _initialize_model(self):
        """初始化 Whisper 模型"""
        logger.info(
            f"Loading Whisper model: {settings.WHISPER_MODEL}, "
            f"device: {settings.WHISPER_DEVICE}, "
            f"compute_type: {settings.WHISPER_COMPUTE_TYPE}"
        )
        self._model = WhisperModel(
            settings.WHISPER_MODEL,
            device=settings.WHISPER_DEVICE,
            compute_type=settings.WHISPER_COMPUTE_TYPE,
        )
        logger.info("Whisper model loaded successfully")

    async def transcribe(
        self,
        audio_path: str,
        language: str = "auto",
        progress_callback: Optional[Callable[[float], None]] = None,
    ) -> dict:
        """
        转录音频文件

        Args:
            audio_path: 音频文件路径
            language: 语言 (auto/zh/en)
            progress_callback: 进度回调函数

        Returns:
            {
                "text": "完整文本",
                "language": "检测到的语言",
                "language_probability": 0.95,
                "segments": [
                    {"start": 0.0, "end": 5.0, "text": "...", "confidence": 0.9}
                ]
            }
        """
        # 在线程池中运行，避免阻塞
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            self._transcribe_sync,
            audio_path,
            language,
        )

        if progress_callback:
            progress_callback(1.0)

        return result

    def _transcribe_sync(self, audio_path: str, language: str) -> dict:
        """同步转录"""
        lang_param = None if language == "auto" else language

        segments_gen, info = self._model.transcribe(
            audio_path,
            language=lang_param,
            beam_size=5,
            vad_filter=True,  # 使用 VAD 过滤静音
            vad_parameters=dict(min_silence_duration_ms=500),
        )

        segments = []
        full_text = []

        for segment in segments_gen:
            segments.append(
                {
                    "start": segment.start,
                    "end": segment.end,
                    "text": segment.text.strip(),
                    "confidence": getattr(segment, "avg_logprob", 0),
                }
            )
            full_text.append(segment.text.strip())

        return {
            "text": " ".join(full_text),
            "language": info.language,
            "language_probability": info.language_probability,
            "segments": segments,
            "duration": info.duration,
        }


# 单例实例
whisper_service = WhisperService()