"""
Adapter 注册表：按 provider name 查找对应 Adapter
"""
from typing import Dict, Type
from .base import BaseAdapter


_registry: Dict[str, Type[BaseAdapter]] = {}


def register(name: str):
    """装饰器：注册 adapter"""
    def decorator(cls: Type[BaseAdapter]):
        _registry[name.lower()] = cls
        return cls
    return decorator


def get_adapter(name: str) -> BaseAdapter:
    """按名称获取 adapter 实例"""
    key = name.lower()
    if key not in _registry:
        raise ValueError(f"Unsupported provider: {name}. Available: {list(_registry.keys())}")
    return _registry[key]()


def available_providers():
    return list(_registry.keys())
