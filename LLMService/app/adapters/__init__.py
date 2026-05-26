from .base import BaseAdapter, ChatMessage, ChatResult
from .registry import register, get_adapter, available_providers

# 导入所有 adapter 以触发 @register 装饰器
from . import openai   # noqa
from . import deepseek   # noqa
from . import anthropic   # noqa

# CrazyRouter 是 OpenAI 兼容协议，注册别名
from .openai import OpenAIAdapter
register("crazyrouter")(OpenAIAdapter)
