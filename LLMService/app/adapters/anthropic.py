"""
Anthropic Messages API 适配器
"""
import time
from typing import Any, Dict, List
from anthropic import Anthropic
from .base import BaseAdapter, ChatMessage, ChatResult
from .registry import register


@register("anthropic")
class AnthropicAdapter(BaseAdapter):
    def chat(
        self,
        base_url: str,
        api_key: str,
        model: str,
        messages: List[ChatMessage],
        params: Dict[str, Any],
    ) -> ChatResult:
        client = Anthropic(api_key=api_key, base_url=base_url)
        system_prompt = ""
        user_messages = []
        for m in messages:
            if m.role == "system":
                system_prompt += m.content + "\n"
            else:
                user_messages.append({"role": m.role, "content": m.content})

        start = time.time()
        resp = client.messages.create(
            model=model,
            system=system_prompt.strip() or None,
            messages=user_messages,
            max_tokens=params.get("max_tokens", 4096),
            temperature=params.get("temperature", 0.7),
        )
        elapsed = int((time.time() - start) * 1000)

        return ChatResult(
            content=resp.content[0].text,
            prompt_tokens=resp.usage.input_tokens,
            completion_tokens=resp.usage.output_tokens,
            latency_ms=elapsed,
        )
