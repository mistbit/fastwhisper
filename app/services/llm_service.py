import json
import logging
from typing import Optional

from openai import AsyncOpenAI

from app.core.config import settings

logger = logging.getLogger(__name__)


MINUTES_PROMPT = """你是一个专业的会议纪要助手。请根据以下会议转录内容生成结构化的会议纪要。

## 转录内容
{transcript}

## 输出要求
请按照以下 JSON 格式输出：

```json
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
```

注意：
1. 提取关键信息，去除无关的口语化表达
2. 保留具体的数字、日期、人名等重要信息
3. 如果信息不明确，标注为"待确认"
4. 使用简洁专业的语言
5. 如果是中英混合内容，保持原有语言风格"""


class LLMService:
    """LLM 会议纪要生成服务"""

    def __init__(self):
        self.provider = settings.LLM_PROVIDER
        self.model = settings.LLM_MODEL

        # 初始化客户端
        if self.provider == "qwen":
            # 通义千问使用 OpenAI 兼容接口
            self.client = AsyncOpenAI(
                api_key=settings.LLM_API_KEY,
                base_url=settings.LLM_BASE_URL
                or "https://dashscope.aliyuncs.com/compatible-mode/v1",
            )
        elif self.provider == "openai":
            self.client = AsyncOpenAI(api_key=settings.LLM_API_KEY, base_url=settings.LLM_BASE_URL)
        else:
            # 其他兼容 OpenAI API 的服务
            self.client = AsyncOpenAI(
                api_key=settings.LLM_API_KEY,
                base_url=settings.LLM_BASE_URL,
            )

        logger.info(f"LLM service initialized: provider={self.provider}, model={self.model}")

    async def generate_minutes(self, transcript: str) -> dict:
        """
        根据转录内容生成会议纪要

        Args:
            transcript: 会议转录文本

        Returns:
            {
                "summary": "摘要",
                "key_points": [...],
                "action_items": [...],
                "decisions": [...],
                "model_used": "qwen-max",
                "tokens_used": 1000
            }
        """
        prompt = MINUTES_PROMPT.format(transcript=transcript)

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "你是一个专业的会议纪要助手，擅长提取会议关键信息并生成结构化纪要。"},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,  # 低温度，更稳定
                response_format={"type": "json_object"},
            )

            result = json.loads(response.choices[0].message.content)
            result["model_used"] = self.model
            result["tokens_used"] = response.usage.total_tokens if response.usage else 0

            return result

        except Exception as e:
            logger.error(f"Failed to generate minutes: {e}")
            raise

    async def summarize_speakers(self, segments: list[dict]) -> dict[str, str]:
        """
        为每个说话人生成简要描述

        Args:
            segments: 带说话人信息的转录片段

        Returns:
            {"SPEAKER_01": "主持人", "SPEAKER_02": "开发组长"}
        """
        # 收集每个说话人的发言
        speaker_texts = {}
        for seg in segments:
            speaker = seg["speaker"]
            if speaker not in speaker_texts:
                speaker_texts[speaker] = []
            speaker_texts[speaker].append(seg["text"])

        # 为每个说话人生成标签
        speaker_labels = {}
        for speaker, texts in speaker_texts.items():
            combined_text = " ".join(texts[:5])  # 取前5段发言
            try:
                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {
                            "role": "system",
                            "content": "根据发言内容，用2-4个字概括说话人的角色，如：主持人、开发、产品、客户等。只输出角色名称。",
                        },
                        {"role": "user", "content": combined_text[:500]},
                    ],
                    temperature=0.3,
                    max_tokens=10,
                )
                speaker_labels[speaker] = response.choices[0].message.content.strip()
            except Exception as e:
                logger.warning(f"Failed to label speaker {speaker}: {e}")
                speaker_labels[speaker] = speaker

        return speaker_labels


# 单例实例
llm_service = LLMService()