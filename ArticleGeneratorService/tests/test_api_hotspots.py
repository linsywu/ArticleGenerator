"""
热点 API 测试用例
"""
import pytest


def test_list_hotspots_empty(client):
    """空列表时返回 { data: [], total: 0 }"""
    r = client.get("/api/hotspots")
    assert r.status_code == 200
    j = r.json()
    assert "data" in j and "total" in j
    assert j["data"] == []
    assert j["total"] == 0


def test_create_hotspot(client):
    """创建热点成功"""
    r = client.post("/api/hotspots", json={
        "title": "测试热点",
        "source": "微博热搜",
        "heat": 10000,
    })
    assert r.status_code == 200
    data = r.json()
    assert data["title"] == "测试热点"
    assert data["source"] == "微博热搜"
    assert data["heat"] == 10000
    assert data["status"] == "unselected"


def test_batch_create_hotspots(client):
    """批量创建热点，去重"""
    items = [
        {"title": "热点1", "source": "微博", "heat": 100},
        {"title": "热点2", "source": "微博", "heat": 200},
        {"title": "热点1", "source": "微博", "heat": 300},  # 重复
    ]
    r = client.post("/api/hotspots/batch", json=items)
    assert r.status_code == 200
    assert r.json()["created"] == 2
    assert r.json()["total"] == 3


def test_get_hotspot(client):
    """获取热点详情"""
    create_r = client.post("/api/hotspots", json={"title": "T", "source": "S", "heat": 1})
    hid = create_r.json()["id"]
    r = client.get(f"/api/hotspots/{hid}")
    assert r.status_code == 200
    assert r.json()["title"] == "T"


def test_get_hotspot_not_found(client):
    """获取不存在的热点返回 404"""
    r = client.get("/api/hotspots/99999")
    assert r.status_code == 404


def test_list_hotspots_with_filter(client):
    """热点列表支持 source 筛选"""
    client.post("/api/hotspots", json={"title": "A", "source": "微博", "heat": 1})
    client.post("/api/hotspots", json={"title": "B", "source": "知乎", "heat": 2})
    r = client.get("/api/hotspots", params={"source": "微博"})
    assert r.status_code == 200
    j = r.json()
    assert "data" in j and "total" in j
    assert all(h["source"] == "微博" for h in j["data"])
    assert j["total"] == 1


def test_list_hotspots_sources(client):
    """获取热点来源列表"""
    client.post("/api/hotspots", json={"title": "A", "source": "微博热搜", "heat": 1})
    client.post("/api/hotspots", json={"title": "B", "source": "知乎热榜", "heat": 2})
    r = client.get("/api/hotspots/sources")
    assert r.status_code == 200
    assert "sources" in r.json()
    assert "微博热搜" in r.json()["sources"]
    assert "知乎热榜" in r.json()["sources"]
