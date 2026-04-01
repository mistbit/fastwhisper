import numpy as np
import pytest

from app.services.diarization_service import DiarizationService, settings


@pytest.mark.asyncio
async def test_diarize_falls_back_to_local_clustering(monkeypatch):
    service = DiarizationService()
    service._pipeline = None
    service._pipeline_unavailable_reason = "pyannote unavailable"

    monkeypatch.setattr(settings, "ENABLE_SPEAKER_DIARIZATION", True, raising=False)
    monkeypatch.setattr(
        service,
        "_local_diarize_sync",
        lambda *args: [
            {"speaker": "SPEAKER_01", "start": 0.0, "end": 1.0},
            {"speaker": "SPEAKER_02", "start": 1.0, "end": 2.0},
        ],
    )

    segments = await service.diarize(
        "fake.m4a",
        transcript_segments=[
            {"start": 0.0, "end": 1.0, "text": "你好"},
            {"start": 1.0, "end": 2.0, "text": "你好呀"},
        ],
    )

    assert [segment["speaker"] for segment in segments] == ["SPEAKER_01", "SPEAKER_02"]


def test_local_diarize_sync_clusters_distinct_feature_groups(monkeypatch):
    service = DiarizationService()

    monkeypatch.setattr(
        service,
        "_load_audio_samples",
        lambda *args, **kwargs: np.ones(32000, dtype=np.float32),
    )

    vectors = iter(
        [
            np.array([0.0, 0.0, 0.0], dtype=np.float32),
            np.array([0.1, 0.1, 0.1], dtype=np.float32),
            np.array([4.0, 4.0, 4.0], dtype=np.float32),
            np.array([4.1, 4.1, 4.1], dtype=np.float32),
        ]
    )
    monkeypatch.setattr(service, "_extract_segment_features", lambda *args, **kwargs: next(vectors))

    diarization_segments = service._local_diarize_sync(
        "fake.m4a",
        [
            {"start": 0.0, "end": 1.0, "text": "A"},
            {"start": 1.0, "end": 2.0, "text": "B"},
            {"start": 2.0, "end": 3.0, "text": "C"},
            {"start": 3.0, "end": 4.0, "text": "D"},
        ],
        target_speakers=2,
        max_speakers=4,
    )

    speakers = [segment["speaker"] for segment in diarization_segments]
    assert speakers[0] == speakers[1]
    assert speakers[2] == speakers[3]
    assert speakers[0] != speakers[2]
