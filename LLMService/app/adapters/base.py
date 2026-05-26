"""
Provider Adapter 基类
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List


class ChatMessage:
    """统一消息格式"""
    def __init__(self, role: str, content: str):
        self.role = role  # system / user / assistant
        self.content = content


class ChatResult:
    """统一返回格式"""
    def __init__(self, content: str, prompt_tokens: int = 0, completion_tokens: int = 0, latency_ms: int = 0):
        self.content = content
        self.prompt_tokens = prompt_tokens
        self.completion_tokens = completion_tokens
        self.latency_ms = latency_ms


class BaseAdapter(ABC):
    """Provider 适配器基类"""

    @abstractmethod
    def chat(
        self,
        base_url: str,
        api_key: str,
        model: str,
        messages: List[ChatMessage],
        params: Dict[str, Any],
    ) -> ChatResult:
        """发送消息并返回统一结果"""
        ...
