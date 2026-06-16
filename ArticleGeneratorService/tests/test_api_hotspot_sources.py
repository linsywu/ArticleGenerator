"""
热点源配置 API 测试用例
"""
import pytest
from app.config import settings


def test_list_sources_empty(client):
    """空列表时返回 []（使用爬虫密钥）"""
    r = client.get("/api/hotspot-sources", headers={"X-API-Key": settings.crawler_api_key})
    assert r.status_code == 200
    assert r.json() == []


def test_create_source(auth_client):
    """创建热点源成功"""
    r = auth_client.post("/api/hotspot-sources", json={
        "name": "微博API",
        "type": "API",
        "config": "{}",
        "enabled": True,
    })
    assert r.status_code == 200
    data = r.json()
    assert data["name"] == "微博API"
    assert data["type"] == "API"
    assert data["enabled"] is True


def test_get_source_not_found(client):
    """获取不存在的热点源返回 404（使用爬虫密钥）"""
    r = client.get("/api/hotspot-sources/99999", headers={"X-API-Key": settings.crawler_api_key})
    assert r.status_code == 404
