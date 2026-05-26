"""
热点源：从各平台 API 抓取热点
使用免费聚合 API：https://api-v2.cenguigui.cn/api/juhe/hotlist.php
支持：weibo, zhihu, baidu, douyin, bilihot 等
"""
import re
import httpx
from typing import List, Dict, Any

API_BASE = "https://api-v2.cenguigui.cn/api/juhe/hotlist.php"

# 热度字符串转数值：如 "111.7万" -> 1117000
def parse_heat(s: str) -> int:
    if not s:
        return 0
    s = str(s).strip()
    if "万" in s:
        try:
            return int(float(re.sub(r"[^\d.]", "", s)) * 10000)
        except ValueError:
            return 0
    if "亿" in s:
        try:
            return int(float(re.sub(r"[^\d.]", "", s)) * 100000000)
        except ValueError:
            return 0
    try:
        return int(re.sub(r"[^\d]", "", s) or 0)
    except ValueError:
        return 0


def fetch_hotlist(source_type: str, limit: int = 50) -> List[Dict[str, Any]]:
    """
    从聚合 API 抓取热榜
    source_type: weibo, zhihu, baidu, douyin, bilihot 等
    返回格式: [{"title": str, "source": str, "heat": int, "url": str}, ...]
    """
    source_names = {
        "weibo": "微博热搜",
        "zhihu": "知乎热榜",
        "baidu": "百度热点",
        "douyin": "抖音热搜",
        "bilihot": "哔哩哔哩热搜",
    }
    source_name = source_names.get(source_type, source_type)

    try:
        with httpx.Client(timeout=15.0) as client:
            resp = client.get(API_BASE, params={"type": source_type})
            resp.raise_for_status()
            data = resp.json()
    except Exception as e:
        return []

    if not data.get("success") or not data.get("data"):
        return []

    items = []
    for i, row in enumerate(data["data"][:limit]):
        title = row.get("title", "").strip()
        if not title:
            continue
        heat = parse_heat(row.get("hot", "0"))
        url = row.get("url") or row.get("mobilUrl") or ""
        items.append({
            "title": title,
            "source": source_name,
            "heat": heat,
            "summary": None,
            "url": url,
        })
    return items


def fetch_all_sources(sources: List[str] = None, limit_per: int = 30) -> List[Dict[str, Any]]:
    """
    从多个源抓取，合并去重（按 title 简单去重）
    """
    sources = sources or ["weibo", "zhihu"]
    all_items = []
    seen_titles = set()
    for st in sources:
        items = fetch_hotlist(st, limit=limit_per)
        for it in items:
            # 简单去重：标题完全一致则跳过
            key = (it["title"][:50], it["source"])
            if key in seen_titles:
                continue
            seen_titles.add(key)
            all_items.append(it)
    # 按热度排序
    all_items.sort(key=lambda x: x["heat"], reverse=True)
    return all_items
