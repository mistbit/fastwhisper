import asyncio
import logging
import re
from threading import Lock
from typing import Any, Callable, Optional

from app.core.config import settings

logger = logging.getLogger(__name__)


class SenseVoiceService:
    """SenseVoice (FunASR) transcription service"""

    _instance: Optional["SenseVoiceService"] = None

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
        from funasr import AutoModel

        device = settings.WHISPER_DEVICE if settings.WHISPER_DEVICE != "cuda" else "cuda:0"

        attempts = [device]
        if device.startswith("cuda"):
            attempts.append("cpu")

        last_error: Optional[Exception] = None
        for dev in attempts:
            try:
                logger.info(
                    "Loading SenseVoice model: %s, device: %s",
                    settings.SENSEVOICE_MODEL,
                    dev,
                )
                model = AutoModel(
                    model=settings.SENSEVOICE_MODEL,
                    vad_model="fsmn-vad",
                    vad_kwargs={"max_single_segment_time": 30000},
                    device=dev,
                    disable_update=True,
                )
                logger.info("SenseVoice model loaded successfully")
                return model
            except Exception as exc:
                last_error = exc
                logger.warning(
                    "Failed to load SenseVoice model with device=%s: %s",
                    dev,
                    exc,
                )

        raise RuntimeError(
            "Failed to initialize SenseVoice model. Check model name and device configuration."
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
        from funasr.utils.postprocess_utils import rich_transcription_postprocess

        model = self._get_model()
        lang_map = {"zh": "zh", "en": "en", "auto": "auto"}
        lang = lang_map.get(language, "auto")

        res = model.generate(
            input=audio_path,
            cache={},
            language=lang,
            use_itn=True,
            batch_size_s=60,
            merge_vad=True,
            merge_length_s=15,
        )

        if not res:
            return {
                "text": "",
                "language": language if language != "auto" else "unknown",
                "language_probability": 0.0,
                "segments": [],
                "duration": 0.0,
            }

        result = res[0]
        raw_text = result.get("text", "")
        text = rich_transcription_postprocess(raw_text)
        detected_lang = self._detect_language_from_tags(raw_text)
        duration = self._get_audio_duration(audio_path)
        timestamps = result.get("timestamp", [])

        if timestamps:
            segments = self._build_segments_from_timestamps(text, timestamps)
        else:
            segments = self._build_segments_from_text(text, duration)

        return {
            "text": text,
            "language": detected_lang,
            "language_probability": 1.0,
            "segments": segments,
            "duration": duration,
        }

    def _detect_language_from_tags(self, raw_text: str) -> str:
        match = re.search(r"<\|(\w+)\|>", raw_text)
        if match:
            tag = match.group(1).lower()
            lang_map = {"zh": "zh", "en": "en", "ja": "ja", "ko": "ko", "yue": "yue"}
            return lang_map.get(tag, tag)
        return "unknown"

    def _get_audio_duration(self, audio_path: str) -> float:
        try:
            from faster_whisper.audio import decode_audio

            audio = decode_audio(audio_path, sampling_rate=16000)
            return len(audio) / 16000.0
        except Exception:
            try:
                import librosa

                duration = librosa.get_duration(path=audio_path)
                return float(duration)
            except Exception:
                return 0.0

    def _build_segments_from_timestamps(
        self, text: str, timestamps: list
    ) -> list[dict]:
        if not timestamps:
            return []

        segments = []
        current_text = []
        current_start = None
        current_end = None

        chars = list(text.replace(" ", ""))
        char_idx = 0

        for i, ts in enumerate(timestamps):
            if len(ts) < 2:
                continue

            start_ms, end_ms = ts[0], ts[1]
            start_s = start_ms / 1000.0
            end_s = end_ms / 1000.0

            if current_start is None:
                current_start = start_s

            current_end = end_s
            if char_idx < len(chars):
                current_text.append(chars[char_idx])
                char_idx += 1

            joined = "".join(current_text)
            is_sentence_end = joined and joined[-1] in "。！？.!?\n"
            gap_after = False
            if i + 1 < len(timestamps):
                next_ts = timestamps[i + 1]
                if len(next_ts) >= 2 and (next_ts[0] / 1000.0 - end_s) > 0.7:
                    gap_after = True

            if is_sentence_end or gap_after:
                segment_text = joined.strip()
                if segment_text:
                    segments.append(
                        {
                            "start": current_start,
                            "end": current_end,
                            "text": segment_text,
                            "confidence": 0,
                        }
                    )
                current_text = []
                current_start = None
                current_end = None

        if current_text:
            segment_text = "".join(current_text).strip()
            if segment_text:
                segments.append(
                    {
                        "start": current_start or 0.0,
                        "end": current_end or 0.0,
                        "text": segment_text,
                        "confidence": 0,
                    }
                )

        return segments

    def _build_segments_from_text(
        self, text: str, duration: float
    ) -> list[dict]:
        if not text.strip():
            return []

        sentences = re.split(r"(?<=[。！？.!?])\s*", text.strip())
        sentences = [s.strip() for s in sentences if s.strip()]

        if not sentences:
            return [
                {
                    "start": 0.0,
                    "end": duration,
                    "text": text.strip(),
                    "confidence": 0,
                }
            ]

        total_chars = sum(len(s) for s in sentences)
        if total_chars == 0:
            total_chars = 1

        segments = []
        current_time = 0.0
        for sentence in sentences:
            seg_duration = (len(sentence) / total_chars) * duration
            segments.append(
                {
                    "start": round(current_time, 3),
                    "end": round(current_time + seg_duration, 3),
                    "text": sentence,
                    "confidence": 0,
                }
            )
            current_time += seg_duration

        return segments


sensevoice_service = SenseVoiceService()
