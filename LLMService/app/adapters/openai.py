"""
OpenAI Chat Completions API 适配器
"""
import time
from typing import Any, Dict, List
from openai import OpenAI
from .base import BaseAdapter, ChatMessage, ChatResult
from .registry import register


@register("openai")
class OpenAIAdapter(BaseAdapter):
    def chat(
        self,
        base_url: str,
        api_key: str,
        model: str,
        messages: List[ChatMessage],
        params: Dict[str, Any],
    ) -> ChatResult:
        client = OpenAI(api_key=api_key, base_url=base_url)
        openai_messages = [{"role": m.role, "content": m.content} for m in messages]

        start = time.time()
        resp = client.chat.completions.create(
            model=model,
            messages=openai_messages,
            max_tokens=params.get("max_tokens", 4096),
            temperature=params.get("temperature", 0.7),
            top_p=params.get("top_p", 1.0),
            frequency_penalty=params.get("frequency_penalty", 0.0),
            presence_penalty=params.get("presence_penalty", 0.0),
        )
        elapsed = int((time.time() - start) * 1000)

        return ChatResult(
            content=resp.choices[0].message.content or "",
            prompt_tokens=resp.usage.prompt_tokens if resp.usage else 0,
            completion_tokens=resp.usage.completion_tokens if resp.usage else 0,
            latency_ms=elapsed,
        )
