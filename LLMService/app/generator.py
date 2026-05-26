"""
Mock fallback：当后端 API 不可达时使用的占位生成逻辑
"""
from typing import Optional


def mock_generate(hotspot_title: str, account_id: int) -> str:
    """占位生成——仅在后端 API 或 LLM Provider 未配置时使用"""
    return f"""# {hotspot_title}

【占位文章】请先在管理后台配置：
1. API 供应商（/providers）
2. 场景路由（/scenario-configs）
3. 为账号 {account_id} 蒸馏风格画像

完成配置后，重新触发生成即可获得真实文章。
"""


def mock_refine(content: str, keywords: str) -> str:
    """占位微调"""
    return f"""{content}

---
【占位微调】要求关键词：{keywords}
请完成配置后重试。
"""
