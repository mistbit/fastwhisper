from app.services.aligner_service import transcript_aligner


def test_aligner_assigns_best_overlap_and_merges_adjacent_segments():
    whisper_segments = [
        {"start": 0.0, "end": 1.0, "text": "大家好", "confidence": 0.9},
        {"start": 1.1, "end": 2.1, "text": "今天开会", "confidence": 0.8},
        {"start": 3.0, "end": 4.0, "text": "我来补充", "confidence": 0.7},
    ]
    diarization_segments = [
        {"speaker": "SPEAKER_00", "start": 0.0, "end": 2.5},
        {"speaker": "SPEAKER_01", "start": 2.8, "end": 4.5},
    ]

    aligned = transcript_aligner.align(whisper_segments, diarization_segments)

    assert len(aligned) == 2
    assert aligned[0]["speaker"] == "SPEAKER_00"
    assert aligned[0]["text"] == "大家好 今天开会"
    assert aligned[1]["speaker"] == "SPEAKER_01"
    assert aligned[1]["text"] == "我来补充"
