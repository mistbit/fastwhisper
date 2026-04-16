import asyncio
import logging
from threading import Lock
from typing import Any, Callable, Optional

from app.core.config import settings

logger = logging.getLogger(__name__)


class WhisperService:
    """Whisper 转录服务"""

    _instance: Optional["WhisperService"] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if getattr(self, "_bootstrapped", False):
            return
        self._model: Optional[Any] = None
        self._model_lock = Lock()
        self._bootstrapped = True

    def _initialize_model(self) -> Any:
        """按需初始化 Whisper 模型，必要时从 GPU 回退到 CPU"""
        from faster_whisper import WhisperModel

        attempts = [(settings.WHISPER_DEVICE, settings.WHISPER_COMPUTE_TYPE)]
        if settings.WHISPER_DEVICE == "cuda":
            attempts.append(("cpu", "int8"))

        last_error: Optional[Exception] = None
        for device, compute_type in attempts:
            try:
                logger.info(
                    "Loading Whisper model: %s, device: %s, compute_type: %s",
                    settings.WHISPER_MODEL,
                    device,
                    compute_type,
                )
                model = WhisperModel(
                    settings.WHISPER_MODEL,
                    device=device,
                    compute_type=compute_type,
                )
                logger.info("Whisper model loaded successfully")
                return model
            except Exception as exc:
                last_error = exc
                logger.warning(
                    "Failed to load Whisper model with device=%s compute_type=%s: %s",
                    device,
                    compute_type,
                    exc,
                )

        raise RuntimeError(
            "Failed to initialize Whisper model. Check model name, runtime dependencies, and device configuration."
        ) from last_error

    def _get_model(self):
        if self._model is None:
            with self._model_lock:
                if self._model is None:
                    self._model = self._initialize_model()
        return self._model

    async def transcribe(
        self,
        audio_path: str,
        language: str = "auto",
        progress_callback: Optional[Callable[[float], None]] = None,
    ) -> dict:
        """在线程池中执行转录，避免阻塞事件循环"""
        loop = asyncio.get_running_loop()
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
        model = self._get_model()
        lang_param = None if language == "auto" else language

        transcribe_kwargs = dict(
            language=lang_param,
            beam_size=settings.WHISPER_BEAM_SIZE,
            vad_filter=True,
            vad_parameters=dict(min_silence_duration_ms=500),
            condition_on_previous_text=True,
            word_timestamps=True,
        )

        temperature = settings.WHISPER_TEMPERATURE
        if temperature == 0.0:
            transcribe_kwargs["temperature"] = 0.0
        else:
            transcribe_kwargs["temperature"] = [temperature, temperature + 0.2, temperature + 0.4]

        segments_gen, info = model.transcribe(audio_path, **transcribe_kwargs)

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


whisper_service = WhisperService()
