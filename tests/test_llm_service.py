import pytest

from app.services.llm_service import LLMService, settings


@pytest.mark.asyncio
async def test_generate_minutes_chunks_long_segment_payloads(monkeypatch):
    service = LLMService()
    chunk_inputs = []

    async def fake_generate_minutes_for_text(transcript):
        chunk_inputs.append(transcript)
        return (
            {
                "summary": transcript[:20],
                "key_points": [],
                "action_items": [],
                "decisions": [],
            },
            10,
        )

    async def fake_merge_minutes_documents(documents):
        assert len(documents) == 2
        return (
            {
                "summary": "merged summary",
                "key_points": [],
                "action_items": [],
                "decisions": [],
            },
            5,
        )

    monkeypatch.setattr(service, "_generate_minutes_for_text", fake_generate_minutes_for_text)
    monkeypatch.setattr(service, "_merge_minutes_documents", fake_merge_minutes_documents)
    monkeypatch.setattr(service, "_is_enabled", lambda: True)

    segments = [
        {"speaker": "SPEAKER_00", "text": "a" * 5000},
        {"speaker": "SPEAKER_01", "text": "b" * 5000},
    ]
    transcript = " ".join(segment["text"] for segment in segments)

    result = await service.generate_minutes(transcript, segments=segments)

    assert len(chunk_inputs) == 2
    assert result["summary"] == "merged summary"
    assert result["tokens_used"] == 25
    assert result["model_used"] == service.model


def test_chunk_segments_respects_token_budget():
    service = LLMService()

    class FakeTokenizer:
        def encode(self, text):
            return text.split()

    service._tokenizer = FakeTokenizer()
    service._tokenizer_checked = True

    chunks = service._chunk_segments(
        [
            {"speaker": "SPEAKER_00", "text": "one two three"},
            {"speaker": "SPEAKER_01", "text": "four five six"},
            {"speaker": "SPEAKER_02", "text": "seven eight nine"},
        ],
        max_chars=200,
        max_tokens=5,
    )

    assert len(chunks) == 3


@pytest.mark.asyncio
async def test_request_json_only_falls_back_for_response_format_errors():
    service = LLMService()

    class FakeResponse:
        def __init__(self, content, tokens=12):
            self.choices = [type("Choice", (), {"message": type("Message", (), {"content": content})()})()]
            self.usage = type("Usage", (), {"total_tokens": tokens})()

    class FakeCompletions:
        def __init__(self):
            self.calls = []

        async def create(self, **kwargs):
            self.calls.append(kwargs)
            if "response_format" in kwargs:
                raise RuntimeError("response_format json_object is unsupported")
            return FakeResponse('{"summary": "ok"}')

    completions = FakeCompletions()
    service.client = type(
        "FakeClient",
        (),
        {"chat": type("Chat", (), {"completions": completions})()},
    )()

    result, tokens = await service._request_json(
        [{"role": "user", "content": "hello"}]
    )

    assert result["summary"] == "ok"
    assert tokens == 12
    assert len(completions.calls) == 2
    assert "response_format" in completions.calls[0]
    assert "response_format" not in completions.calls[1]


@pytest.mark.asyncio
async def test_request_json_does_not_retry_for_generic_transport_errors():
    service = LLMService()

    class FakeCompletions:
        async def create(self, **kwargs):
            raise RuntimeError("connection timeout")

    service.client = type(
        "FakeClient",
        (),
        {"chat": type("Chat", (), {"completions": FakeCompletions()})()},
    )()

    with pytest.raises(RuntimeError, match="connection timeout"):
        await service._request_json([{"role": "user", "content": "hello"}])


@pytest.mark.asyncio
async def test_generate_minutes_uses_local_fallback_when_llm_disabled(monkeypatch):
    service = LLMService()
    monkeypatch.setattr(settings, "ENABLE_LLM_MINUTES", False)
    monkeypatch.setattr(settings, "LLM_API_KEY", "")

    result = await service.generate_minutes(
        "今天讨论了版本计划和上线安排。",
        segments=[
            {"speaker": "SPEAKER_00", "text": "今天讨论了版本计划。"},
            {"speaker": "SPEAKER_01", "text": "上线安排定在周五。"},
        ],
    )

    assert result["model_used"] == "local-transcript-only"
    assert result["tokens_used"] == 0
    assert "本地模式未启用 LLM" in result["summary"]
    assert len(result["key_points"]) == 2
