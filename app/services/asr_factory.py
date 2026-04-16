"""ASR engine factory — returns the configured transcription service."""
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)


def get_asr_service():
    """Return the ASR service instance based on the ASR_ENGINE setting."""
    engine = settings.ASR_ENGINE

    if engine == "sensevoice":
        from app.services.sensevoice_service import sensevoice_service

        logger.info("Using SenseVoice (FunASR) ASR engine")
        return sensevoice_service

    # Default: whisper
    from app.services.whisper_service import whisper_service

    logger.info("Using faster-whisper ASR engine")
    return whisper_service
