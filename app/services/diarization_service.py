import asyncio
import logging
from threading import Lock
from typing import Optional

import numpy as np
from faster_whisper.audio import decode_audio

from app.core.config import settings

logger = logging.getLogger(__name__)

LOCAL_SAMPLE_RATE = 8000
LOCAL_MIN_SEGMENT_SECONDS = 0.8
LOCAL_MAX_SEGMENT_SECONDS = 8.0
LOCAL_DEFAULT_SPEAKER_COUNT = 2
LOCAL_FRAME_SAMPLES = 200
LOCAL_HOP_SAMPLES = 80
LOCAL_NFFT = 512
LOCAL_MEL_BANDS = 24
LOCAL_MFCC_COUNT = 10


class DiarizationService:
    """说话人分离服务"""

    _instance: Optional["DiarizationService"] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if getattr(self, "_bootstrapped", False):
            return
        self._pipeline = None
        self._pipeline_lock = Lock()
        self._pipeline_unavailable_reason: Optional[str] = None
        self._mel_cache: dict[tuple[int, int, int, int], tuple[np.ndarray, np.ndarray]] = {}
        self._bootstrapped = True

    def _initialize_pipeline(self):
        if not settings.ENABLE_SPEAKER_DIARIZATION:
            self._pipeline_unavailable_reason = (
                "Speaker diarization is disabled."
            )
            logger.info(self._pipeline_unavailable_reason)
            return None

        if not settings.HUGGINGFACE_TOKEN:
            self._pipeline_unavailable_reason = (
                "HUGGINGFACE_TOKEN is not configured; using local speaker clustering fallback."
            )
            logger.info(self._pipeline_unavailable_reason)
            return None

        try:
            import torch
            from pyannote.audio import Pipeline

            logger.info("Loading diarization pipeline...")
            pipeline = Pipeline.from_pretrained(
                "pyannote/speaker-diarization-3.1",
                use_auth_token=settings.HUGGINGFACE_TOKEN,
            )

            if torch.cuda.is_available() and settings.WHISPER_DEVICE == "cuda":
                pipeline = pipeline.to(torch.device("cuda"))

            logger.info("Diarization pipeline loaded successfully")
            return pipeline
        except Exception as exc:
            self._pipeline_unavailable_reason = (
                f"Failed to initialize speaker diarization pipeline, using local clustering fallback: {exc}"
            )
            logger.warning(self._pipeline_unavailable_reason)
            return None

    def _get_pipeline(self):
        if self._pipeline is None and self._pipeline_unavailable_reason is None:
            with self._pipeline_lock:
                if self._pipeline is None and self._pipeline_unavailable_reason is None:
                    self._pipeline = self._initialize_pipeline()
        return self._pipeline

    async def diarize(
        self,
        audio_path: str,
        num_speakers: Optional[int] = None,
        min_speakers: int = 2,
        max_speakers: int = 10,
        transcript_segments: Optional[list[dict]] = None,
    ) -> list[dict]:
        """执行说话人分离，优先 pyannote，不可用时回退到本地聚类。"""
        if not settings.ENABLE_SPEAKER_DIARIZATION:
            return []

        pipeline = self._get_pipeline()
        loop = asyncio.get_running_loop()
        if pipeline is not None:
            try:
                return await loop.run_in_executor(
                    None,
                    self._diarize_sync,
                    audio_path,
                    num_speakers,
                    min_speakers,
                    max_speakers,
                )
            except Exception as exc:
                logger.warning(
                    "Speaker diarization pipeline failed, falling back to local clustering: %s",
                    exc,
                )

        if transcript_segments:
            target_speakers = max(
                1,
                num_speakers or min_speakers or LOCAL_DEFAULT_SPEAKER_COUNT,
            )
            try:
                return await loop.run_in_executor(
                    None,
                    self._local_diarize_sync,
                    audio_path,
                    transcript_segments,
                    target_speakers,
                    max_speakers,
                )
            except Exception as exc:
                logger.warning(
                    "Local speaker clustering failed, falling back to single speaker: %s",
                    exc,
                )

        return []

    def _diarize_sync(
        self,
        audio_path: str,
        num_speakers: Optional[int],
        min_speakers: int,
        max_speakers: int,
    ) -> list[dict]:
        pipeline = self._get_pipeline()
        if pipeline is None:
            return []

        kwargs = {}
        if num_speakers:
            kwargs["num_speakers"] = num_speakers
        else:
            kwargs["min_speakers"] = min_speakers
            kwargs["max_speakers"] = max_speakers

        diarization = pipeline(audio_path, **kwargs)

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

    def _local_diarize_sync(
        self,
        audio_path: str,
        transcript_segments: list[dict],
        target_speakers: int,
        max_speakers: int,
    ) -> list[dict]:
        if len(transcript_segments) < 2:
            return []

        audio = self._load_audio_samples(audio_path, LOCAL_SAMPLE_RATE)
        if audio.size == 0:
            return []

        feature_vectors = []
        segment_refs = []
        for segment in transcript_segments:
            clip = self._extract_segment_audio(audio, segment, LOCAL_SAMPLE_RATE)
            if clip.size == 0:
                continue
            feature_vectors.append(self._extract_segment_features(clip, LOCAL_SAMPLE_RATE))
            segment_refs.append(segment)

        if len(feature_vectors) < 2:
            return []

        requested_speakers = min(
            max(1, target_speakers),
            max(1, max_speakers),
            len(feature_vectors),
        )
        labels = self._cluster_features(np.vstack(feature_vectors), requested_speakers)
        speaker_names = self._build_speaker_name_map(labels)

        return [
            {
                "speaker": speaker_names[int(label)],
                "start": segment["start"],
                "end": segment["end"],
            }
            for segment, label in zip(segment_refs, labels)
        ]

    def _load_audio_samples(self, audio_path: str, sample_rate: int) -> np.ndarray:
        samples = decode_audio(audio_path, sampling_rate=sample_rate)
        if isinstance(samples, tuple):
            samples = np.mean(np.stack(samples), axis=0)
        return np.asarray(samples, dtype=np.float32)

    def _extract_segment_audio(
        self,
        audio: np.ndarray,
        segment: dict,
        sample_rate: int,
    ) -> np.ndarray:
        total_samples = audio.shape[0]
        if total_samples == 0:
            return np.zeros(0, dtype=np.float32)

        start = max(0.0, float(segment.get("start", 0.0)))
        end = max(start, float(segment.get("end", start)))
        min_samples = int(LOCAL_MIN_SEGMENT_SECONDS * sample_rate)
        max_samples = int(LOCAL_MAX_SEGMENT_SECONDS * sample_rate)

        start_idx = max(0, min(total_samples, int(start * sample_rate)))
        end_idx = max(start_idx, min(total_samples, int(end * sample_rate)))

        if end_idx - start_idx < min_samples:
            center_idx = (start_idx + end_idx) // 2
            half = min_samples // 2
            start_idx = max(0, center_idx - half)
            end_idx = min(total_samples, start_idx + min_samples)
            start_idx = max(0, end_idx - min_samples)

        if end_idx - start_idx > max_samples:
            center_idx = (start_idx + end_idx) // 2
            half = max_samples // 2
            start_idx = max(0, center_idx - half)
            end_idx = min(total_samples, start_idx + max_samples)

        clip = audio[start_idx:end_idx]
        return np.asarray(clip, dtype=np.float32)

    def _extract_segment_features(
        self,
        clip: np.ndarray,
        sample_rate: int,
    ) -> np.ndarray:
        if clip.size == 0:
            return np.zeros(16, dtype=np.float32)

        clip = clip.astype(np.float32, copy=False)
        if clip.size < LOCAL_FRAME_SAMPLES:
            clip = np.pad(clip, (0, LOCAL_FRAME_SAMPLES - clip.size))

        clip = clip - float(np.mean(clip))
        clip = np.append(clip[0], clip[1:] - 0.97 * clip[:-1])

        frames = []
        for start in range(0, clip.size - LOCAL_FRAME_SAMPLES + 1, LOCAL_HOP_SAMPLES):
            frames.append(clip[start : start + LOCAL_FRAME_SAMPLES])
        frame_matrix = np.vstack(frames).astype(np.float32, copy=False)
        frame_matrix *= np.hamming(LOCAL_FRAME_SAMPLES)

        spectrum = np.abs(np.fft.rfft(frame_matrix, n=LOCAL_NFFT)) ** 2
        filterbank, dct_basis = self._get_mel_components(
            sample_rate,
            LOCAL_NFFT,
            LOCAL_MEL_BANDS,
            LOCAL_MFCC_COUNT,
        )
        mel_energies = np.maximum(spectrum @ filterbank.T, 1e-6)
        log_mel = np.log(mel_energies)
        mfcc = log_mel @ dct_basis

        mfcc_mean = np.mean(mfcc, axis=0)
        mfcc_std = np.std(mfcc, axis=0)[:4]
        zero_crossings = ((frame_matrix[:, 1:] >= 0) != (frame_matrix[:, :-1] >= 0)).mean(axis=1)
        zcr = float(np.mean(zero_crossings)) if zero_crossings.size else 0.0
        rms = float(np.mean(np.sqrt(np.mean(np.square(frame_matrix), axis=1)))) if frame_matrix.size else 0.0
        duration = clip.size / float(sample_rate)

        return np.asarray(
            [
                np.log1p(duration),
                *mfcc_mean,
                *mfcc_std,
                zcr,
                rms,
            ],
            dtype=np.float32,
        )

    def _get_mel_components(
        self,
        sample_rate: int,
        n_fft: int,
        n_mels: int,
        n_mfcc: int,
    ) -> tuple[np.ndarray, np.ndarray]:
        key = (sample_rate, n_fft, n_mels, n_mfcc)
        cached = self._mel_cache.get(key)
        if cached is not None:
            return cached

        filterbank = self._build_mel_filterbank(sample_rate, n_fft, n_mels)
        dct_basis = np.cos(
            np.pi
            / n_mels
            * (np.arange(n_mels, dtype=np.float32)[:, None] + 0.5)
            * np.arange(n_mfcc, dtype=np.float32)[None, :]
        ).astype(np.float32)
        self._mel_cache[key] = (filterbank, dct_basis)
        return filterbank, dct_basis

    def _build_mel_filterbank(
        self,
        sample_rate: int,
        n_fft: int,
        n_mels: int,
    ) -> np.ndarray:
        mel_points = np.linspace(
            self._hz_to_mel(50.0),
            self._hz_to_mel(sample_rate / 2.0 - 50.0),
            n_mels + 2,
            dtype=np.float32,
        )
        hz_points = self._mel_to_hz(mel_points)
        bin_points = np.floor((n_fft + 1) * hz_points / sample_rate).astype(int)

        filterbank = np.zeros((n_mels, n_fft // 2 + 1), dtype=np.float32)
        for index in range(1, n_mels + 1):
            left, center, right = bin_points[index - 1], bin_points[index], bin_points[index + 1]
            if center <= left:
                center = left + 1
            if right <= center:
                right = center + 1

            for bin_index in range(left, min(center, filterbank.shape[1])):
                filterbank[index - 1, bin_index] = (bin_index - left) / max(center - left, 1)
            for bin_index in range(center, min(right, filterbank.shape[1])):
                filterbank[index - 1, bin_index] = (right - bin_index) / max(right - center, 1)

        return filterbank

    def _hz_to_mel(self, hz: float) -> float:
        return 2595.0 * np.log10(1.0 + hz / 700.0)

    def _mel_to_hz(self, mel: np.ndarray) -> np.ndarray:
        return 700.0 * (np.power(10.0, mel / 2595.0) - 1.0)

    def _cluster_features(self, features: np.ndarray, speaker_count: int) -> np.ndarray:
        if features.shape[0] == 0:
            return np.zeros(0, dtype=int)

        speaker_count = max(1, min(speaker_count, features.shape[0]))
        if speaker_count == 1:
            return np.zeros(features.shape[0], dtype=int)

        normalized = features.astype(np.float32, copy=True)
        normalized -= np.mean(normalized, axis=0, keepdims=True)
        std = np.std(normalized, axis=0, keepdims=True)
        std[std < 1e-6] = 1.0
        normalized /= std

        centroids = self._initialize_centroids(normalized, speaker_count)
        labels = np.zeros(normalized.shape[0], dtype=int)

        for _ in range(25):
            distances = np.sum(
                np.square(normalized[:, None, :] - centroids[None, :, :]),
                axis=2,
            )
            next_labels = np.argmin(distances, axis=1)
            if np.array_equal(next_labels, labels):
                break
            labels = next_labels

            new_centroids = []
            min_distances = np.min(distances, axis=1)
            for cluster_index in range(speaker_count):
                members = normalized[labels == cluster_index]
                if members.size == 0:
                    fallback_index = int(np.argmax(min_distances))
                    new_centroids.append(normalized[fallback_index])
                else:
                    new_centroids.append(np.mean(members, axis=0))
            centroids = np.vstack(new_centroids)

        return labels

    def _initialize_centroids(self, features: np.ndarray, speaker_count: int) -> np.ndarray:
        centroids = [features[0]]
        while len(centroids) < speaker_count:
            distances = np.sum(
                np.square(features[:, None, :] - np.vstack(centroids)[None, :, :]),
                axis=2,
            )
            next_index = int(np.argmax(np.min(distances, axis=1)))
            centroids.append(features[next_index])
        return np.vstack(centroids)

    def _build_speaker_name_map(self, labels: np.ndarray) -> dict[int, str]:
        mapping: dict[int, str] = {}
        next_index = 1
        for label in labels:
            label = int(label)
            if label not in mapping:
                mapping[label] = f"SPEAKER_{next_index:02d}"
                next_index += 1
        return mapping

    def get_speaker_count(self, segments: list[dict]) -> int:
        speakers = set(seg["speaker"] for seg in segments)
        return len(speakers)


diarization_service = DiarizationService()
