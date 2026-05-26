"""
将抓取的热点同步到后端 API
优先从 /api/hotspot-sources 读取启用的热点源，若无则使用环境变量 CRAWL_SOURCES
"""
import os
import httpx
from typing import List, Dict, Any, Optional

from .sources import fetch_all_sources


def _get_sources_from_api(api_base: str) -> Optional[List[str]]:
    """从后端 API 获取启用的热点源类型列表"""
    try:
        with httpx.Client(timeout=10.0) as client:
            resp = client.get(f"{api_base}/api/hotspot-sources")
            resp.raise_for_status()
            data = resp.json()
    except Exception:
        return None
    if not isinstance(data, list):
        return None
    # 只取启用的，type 字段作为 source key（weibo, zhihu 等）
    return [s.get("type") for s in data if s.get("enabled") and s.get("type")]


def sync_hotspots(
    api_base: str = None,
    sources: List[str] = None,
) -> Dict[str, Any]:
    """
    抓取热点并 POST 到后端 /api/hotspots/batch
    api_base: 如 http://localhost:8000
    sources: 若未指定，优先从 /api/hotspot-sources 读取，否则用环境变量 CRAWL_SOURCES
    """
    api_base = (api_base or os.environ.get("API_BASE", "http://localhost:8000")).rstrip("/")
    if sources is None:
        sources = _get_sources_from_api(api_base)
    if sources is None:
        env_sources = os.environ.get("CRAWL_SOURCES", "weibo,zhihu")
        sources = [s.strip() for s in env_sources.split(",") if s.strip()]
    items = fetch_all_sources(sources=sources)
    if not items:
        return {"created": 0, "total": 0, "message": "无新热点"}

    try:
        with httpx.Client(timeout=30.0) as client:
            resp = client.post(
                f"{api_base}/api/hotspots/batch",
                json=items,
            )
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        return {"created": 0, "total": len(items), "error": str(e)}


if __name__ == "__main__":
    # 命令行执行：python -m crawler.sync_to_backend
    import sys
    api = sys.argv[1] if len(sys.argv) > 1 else None
    result = sync_hotspots(api_base=api)
    print(result)
