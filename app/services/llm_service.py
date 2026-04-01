import json
import logging
from typing import Optional

from openai import AsyncOpenAI

from app.core.config import settings

logger = logging.getLogger(__name__)

MAX_CHARS_PER_CHUNK = 6000
MAX_MERGE_PAYLOAD_CHARS = 9000
MAX_INPUT_TOKENS = 3000
MAX_MERGE_PAYLOAD_TOKENS = 4500

MINUTES_PROMPT = """你是一个专业的会议纪要助手。请根据以下会议转录内容生成结构化的会议纪要。

## 转录内容
{transcript}

## 输出要求
请只输出 JSON 对象，结构如下：
{{
  "summary": "会议摘要（100-200字）",
  "key_points": [
    {{"title": "要点标题", "content": "详细内容"}}
  ],
  "action_items": [
    {{"assignee": "负责人", "task": "待办事项", "deadline": "截止日期（如有）"}}
  ],
  "decisions": [
    {{"topic": "议题", "decision": "决策内容"}}
  ]
}}

要求：
1. 提取关键信息，去除无关口语化表达
2. 保留具体数字、日期、人名等重要信息
3. 信息不明确时标注为“待确认”
4. 使用简洁专业的语言"""

MERGE_PROMPT = """你会收到多个会议纪要分片结果，请将它们合并为一份完整、去重后的会议纪要。

## 分片纪要
{documents}

## 输出要求
请只输出一个 JSON 对象，结构与下方完全一致：
{{
  "summary": "最终会议摘要",
  "key_points": [
    {{"title": "要点标题", "content": "详细内容"}}
  ],
  "action_items": [
    {{"assignee": "负责人", "task": "待办事项", "deadline": "截止日期（如有）"}}
  ],
  "decisions": [
    {{"topic": "议题", "decision": "决策内容"}}
  ]
}}

要求：
1. 合并重复项
2. 保留时间、负责人、结论等关键信息
3. 若存在冲突，以信息更完整的项为准
4. 摘要必须是全局摘要，而不是分片拼接"""

SPEAKER_PROMPT = """请根据每个说话人的发言样本，给出 2-4 个字的角色标签。

## 输入数据
{speaker_samples}

## 输出格式
请只输出 JSON 对象，键必须与输入中的 speaker 标识完全一致，值为角色标签。例如：
{{
  "SPEAKER_00": "主持人",
  "SPEAKER_01": "产品"
}}

要求：
1. 标签要简洁
2. 无法判断时保留原 speaker 标识
3. 不要输出额外说明"""


class LLMService:
    """LLM 会议纪要生成服务"""

    def __init__(self):
        if getattr(self, "_bootstrapped", False):
            return
        self.provider = settings.LLM_PROVIDER
        self.model = settings.LLM_MODEL
        self.client: Optional[AsyncOpenAI] = None
        self._tokenizer = None
        self._tokenizer_checked = False
        self._bootstrapped = True

    def _is_enabled(self) -> bool:
        return settings.ENABLE_LLM_MINUTES and bool(settings.LLM_API_KEY)

    def _build_local_minutes(
        self,
        transcript: str,
        segments: Optional[list[dict]] = None,
    ) -> dict:
        stripped = transcript.strip()
        preview = stripped[:180]
        if len(stripped) > 180:
            preview = f"{preview}..."

        key_points = []
        excerpt_candidates = []
        if segments:
            excerpt_candidates = [
                self._segment_to_line(segment)
                for segment in segments
                if self._segment_to_line(segment)
            ]
        if not excerpt_candidates and stripped:
            excerpt_candidates = [part.strip() for part in stripped.splitlines() if part.strip()]
        if not excerpt_candidates and stripped:
            excerpt_candidates = [stripped]

        for index, item in enumerate(excerpt_candidates[:5], start=1):
            key_points.append(
                {
                    "title": f"转录片段 {index}",
                    "content": item[:220],
                }
            )

        summary = (
            "本地模式未启用 LLM 纪要生成，以下结果以语音转写摘录为主。"
            if not preview
            else f"本地模式未启用 LLM 纪要生成。转写摘要：{preview}"
        )
        return {
            "summary": summary,
            "key_points": key_points,
            "action_items": [],
            "decisions": [],
            "model_used": "local-transcript-only",
            "tokens_used": 0,
        }

    def _ensure_client(self) -> AsyncOpenAI:
        if self.client is not None:
            return self.client

        if not settings.LLM_API_KEY:
            raise RuntimeError("LLM_API_KEY is not configured.")

        if self.provider == "qwen":
            self.client = AsyncOpenAI(
                api_key=settings.LLM_API_KEY,
                base_url=settings.LLM_BASE_URL
                or "https://dashscope.aliyuncs.com/compatible-mode/v1",
            )
        elif self.provider == "openai":
            self.client = AsyncOpenAI(
                api_key=settings.LLM_API_KEY,
                base_url=settings.LLM_BASE_URL,
            )
        else:
            self.client = AsyncOpenAI(
                api_key=settings.LLM_API_KEY,
                base_url=settings.LLM_BASE_URL,
            )

        logger.info(
            "LLM service initialized: provider=%s, model=%s",
            self.provider,
            self.model,
        )
        return self.client

    def _extract_json(self, content: str) -> dict:
        text = (content or "").strip()
        if not text:
            return {}

        try:
            return json.loads(text)
        except json.JSONDecodeError:
            start = text.find("{")
            end = text.rfind("}")
            if start == -1 or end == -1 or end <= start:
                raise
            return json.loads(text[start : end + 1])

    def _should_retry_without_response_format(self, exc: Exception) -> bool:
        message = str(exc).lower()
        return any(
            keyword in message
            for keyword in (
                "response_format",
                "json_object",
                "unsupported",
                "not support",
                "invalid parameter",
                "extra inputs are not permitted",
            )
        )

    def _get_tokenizer(self):
        if self._tokenizer_checked:
            return self._tokenizer

        self._tokenizer_checked = True
        try:
            import tiktoken

            try:
                self._tokenizer = tiktoken.encoding_for_model(self.model)
            except Exception:
                self._tokenizer = tiktoken.get_encoding("cl100k_base")
        except Exception:
            self._tokenizer = None

        return self._tokenizer

    def _estimate_tokens(self, text: str) -> int:
        if not text:
            return 0

        tokenizer = self._get_tokenizer()
        if tokenizer is not None:
            try:
                return len(tokenizer.encode(text))
            except Exception:
                logger.debug("Tokenizer encode failed; falling back to heuristic token estimate")

        non_ascii_chars = sum(1 for char in text if ord(char) > 127)
        ascii_chars = len(text) - non_ascii_chars
        ascii_tokens = max(1, ascii_chars // 4)
        non_ascii_tokens = max(1, non_ascii_chars)
        return ascii_tokens + non_ascii_tokens

    async def _request_json(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.3,
        max_tokens: Optional[int] = None,
    ) -> tuple[dict, int]:
        client = self._ensure_client()
        request = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
        }
        if max_tokens is not None:
            request["max_tokens"] = max_tokens

        response = None
        try:
            response = await client.chat.completions.create(
                **request,
                response_format={"type": "json_object"},
            )
        except Exception as exc:
            if not self._should_retry_without_response_format(exc):
                raise
            logger.warning(
                "Falling back to plain-text JSON parsing because response_format is unsupported: %s",
                exc,
            )
            response = await client.chat.completions.create(**request)

        try:
            payload = self._extract_json(response.choices[0].message.content or "{}")
        except json.JSONDecodeError as exc:
            raise RuntimeError("Model response was not valid JSON.") from exc
        tokens_used = response.usage.total_tokens if response.usage else 0
        return payload, tokens_used

    def _normalize_minutes(self, data: dict) -> dict:
        return {
            "summary": data.get("summary"),
            "key_points": data.get("key_points") or [],
            "action_items": data.get("action_items") or [],
            "decisions": data.get("decisions") or [],
        }

    def _segment_to_line(self, segment: dict) -> str:
        speaker = segment.get("speaker_label") or segment.get("speaker") or "SPEAKER"
        text = (segment.get("text") or "").strip()
        return f"{speaker}: {text}" if text else ""

    def _chunk_segments(
        self,
        segments: list[dict],
        max_chars: int = MAX_CHARS_PER_CHUNK,
        max_tokens: int = MAX_INPUT_TOKENS,
    ) -> list[str]:
        chunks: list[str] = []
        current_lines: list[str] = []
        current_chars = 0
        current_tokens = 0

        for segment in segments:
            line = self._segment_to_line(segment)
            if not line:
                continue

            line_length = len(line) + 1
            line_tokens = self._estimate_tokens(line)
            if current_lines and (
                current_chars + line_length > max_chars
                or current_tokens + line_tokens > max_tokens
            ):
                chunks.append("\n".join(current_lines))
                current_lines = [line]
                current_chars = line_length
                current_tokens = line_tokens
            else:
                current_lines.append(line)
                current_chars += line_length
                current_tokens += line_tokens

        if current_lines:
            chunks.append("\n".join(current_lines))

        return chunks

    def _chunk_text(
        self,
        transcript: str,
        max_chars: int = MAX_CHARS_PER_CHUNK,
        max_tokens: int = MAX_INPUT_TOKENS,
    ) -> list[str]:
        text = transcript.strip()
        if not text:
            return []

        paragraphs = [part.strip() for part in text.split("\n") if part.strip()] or [text]
        chunks: list[str] = []
        current_parts: list[str] = []
        current_chars = 0
        current_tokens = 0

        for paragraph in paragraphs:
            paragraph_length = len(paragraph) + 1
            paragraph_tokens = self._estimate_tokens(paragraph)
            if current_parts and (
                current_chars + paragraph_length > max_chars
                or current_tokens + paragraph_tokens > max_tokens
            ):
                chunks.append("\n".join(current_parts))
                current_parts = [paragraph]
                current_chars = paragraph_length
                current_tokens = paragraph_tokens
            else:
                current_parts.append(paragraph)
                current_chars += paragraph_length
                current_tokens += paragraph_tokens

        if current_parts:
            chunks.append("\n".join(current_parts))

        return chunks

    def _chunk_documents(
        self,
        documents: list[dict],
        max_chars: int = MAX_MERGE_PAYLOAD_CHARS,
        max_tokens: int = MAX_MERGE_PAYLOAD_TOKENS,
    ) -> list[list[dict]]:
        groups: list[list[dict]] = []
        current_group: list[dict] = []
        current_chars = 0
        current_tokens = 0

        for document in documents:
            encoded = json.dumps(document, ensure_ascii=False)
            encoded_length = len(encoded) + 2
            encoded_tokens = self._estimate_tokens(encoded)
            if current_group and (
                current_chars + encoded_length > max_chars
                or current_tokens + encoded_tokens > max_tokens
            ):
                groups.append(current_group)
                current_group = [document]
                current_chars = encoded_length
                current_tokens = encoded_tokens
            else:
                current_group.append(document)
                current_chars += encoded_length
                current_tokens += encoded_tokens

        if current_group:
            groups.append(current_group)

        return groups

    async def _generate_minutes_for_text(self, transcript: str) -> tuple[dict, int]:
        return await self._request_json(
            [
                {
                    "role": "system",
                    "content": "你是一个专业的会议纪要助手，擅长提取会议关键信息并生成结构化纪要。",
                },
                {
                    "role": "user",
                    "content": MINUTES_PROMPT.format(transcript=transcript),
                },
            ]
        )

    async def _merge_minutes_documents(self, documents: list[dict]) -> tuple[dict, int]:
        if not documents:
            return self._normalize_minutes({}), 0
        if len(documents) == 1:
            return self._normalize_minutes(documents[0]), 0

        merged_documents = []
        total_tokens = 0

        for group in self._chunk_documents(documents):
            merged, tokens = await self._request_json(
                [
                    {
                        "role": "system",
                        "content": "你是一个严谨的会议纪要编辑，擅长去重、合并和归纳多份结构化纪要。",
                    },
                    {
                        "role": "user",
                        "content": MERGE_PROMPT.format(
                            documents=json.dumps(group, ensure_ascii=False, indent=2)
                        ),
                    },
                ]
            )
            merged_documents.append(self._normalize_minutes(merged))
            total_tokens += tokens

        if len(merged_documents) == 1:
            return merged_documents[0], total_tokens

        final_document, recursive_tokens = await self._merge_minutes_documents(merged_documents)
        return final_document, total_tokens + recursive_tokens

    async def generate_minutes(
        self,
        transcript: str,
        segments: Optional[list[dict]] = None,
    ) -> dict:
        """根据转录内容生成会议纪要，长文本自动分块归并"""
        if not transcript.strip():
            return {
                "summary": None,
                "key_points": [],
                "action_items": [],
                "decisions": [],
                "model_used": self.model,
                "tokens_used": 0,
            }

        if not self._is_enabled():
            return self._build_local_minutes(transcript, segments)

        chunks = (
            self._chunk_segments(segments)
            if segments
            else self._chunk_text(transcript)
        )
        if not chunks:
            chunks = [transcript]

        total_tokens = 0
        if len(chunks) == 1:
            result, tokens = await self._generate_minutes_for_text(chunks[0])
            normalized = self._normalize_minutes(result)
            normalized["model_used"] = self.model
            normalized["tokens_used"] = tokens
            return normalized

        partial_documents = []
        for chunk in chunks:
            result, tokens = await self._generate_minutes_for_text(chunk)
            partial_documents.append(self._normalize_minutes(result))
            total_tokens += tokens

        final_document, merge_tokens = await self._merge_minutes_documents(partial_documents)
        final_document["model_used"] = self.model
        final_document["tokens_used"] = total_tokens + merge_tokens
        return final_document

    async def summarize_speakers(self, segments: list[dict]) -> dict[str, str]:
        """为所有说话人批量生成角色标签，失败时回退为原 speaker 标识"""
        if not segments:
            return {}

        if not self._is_enabled():
            return {
                segment["speaker"]: segment["speaker"]
                for segment in segments
                if segment.get("speaker")
            }

        speaker_texts: dict[str, list[str]] = {}
        for segment in segments:
            speaker = segment["speaker"]
            speaker_texts.setdefault(speaker, []).append(segment["text"])

        speaker_samples = {
            speaker: " ".join(texts[:3])[:320]
            for speaker, texts in speaker_texts.items()
        }

        try:
            result, _ = await self._request_json(
                [
                    {
                        "role": "system",
                        "content": "你擅长根据发言判断会议角色，并以 JSON 返回简洁的角色标签。",
                    },
                    {
                        "role": "user",
                        "content": SPEAKER_PROMPT.format(
                            speaker_samples=json.dumps(
                                speaker_samples,
                                ensure_ascii=False,
                                indent=2,
                            )
                        ),
                    },
                ],
                max_tokens=200,
            )
        except Exception as exc:
            logger.warning("Failed to summarize speaker labels: %s", exc)
            return {speaker: speaker for speaker in speaker_texts}

        speaker_labels = {}
        for speaker in speaker_texts:
            label = result.get(speaker)
            if not isinstance(label, str) or not label.strip():
                label = speaker
            speaker_labels[speaker] = label.strip()[:8]

        return speaker_labels


llm_service = LLMService()
