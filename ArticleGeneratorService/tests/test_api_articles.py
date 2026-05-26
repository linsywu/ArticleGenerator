"""
文章 API 测试用例
"""
import pytest

from app.models import Article
from tests.conftest import TestingSessionLocal


@pytest.fixture
def account_and_hotspot(client):
    """创建账号和热点供文章使用"""
    acc = client.post("/api/accounts", json={"platform": "P", "account_name": "A"}).json()
    hot = client.post("/api/hotspots", json={"title": "H", "source": "S", "heat": 1}).json()
    return acc["id"], hot["id"]


def test_list_articles_empty(client):
    """空列表时返回 { data: [], total: 0 }"""
    r = client.get("/api/articles")
    assert r.status_code == 200
    j = r.json()
    assert "data" in j and "total" in j
    assert j["data"] == []
    assert j["total"] == 0


def test_update_article_status_approved(client, account_and_hotspot):
    """文章状态更新为通过"""
    aid, hid = account_and_hotspot
    db = TestingSessionLocal()
    art = Article(hotspot_id=hid, account_id=aid, content="内容", status="pending_review")
    db.add(art)
    db.commit()
    db.refresh(art)
    art_id = art.id
    db.close()

    r = client.patch(f"/api/articles/{art_id}/status", json={"status": "approved"})
    assert r.status_code == 200
    assert r.json()["message"] == "更新成功"


def test_update_article_status_invalid(client, account_and_hotspot):
    """无效状态返回 400"""
    aid, hid = account_and_hotspot
    db = TestingSessionLocal()
    art = Article(hotspot_id=hid, account_id=aid, content="内容", status="pending_review")
    db.add(art)
    db.commit()
    db.refresh(art)
    art_id = art.id
    db.close()

    r = client.patch(f"/api/articles/{art_id}/status", json={"status": "invalid"})
    assert r.status_code == 400


def test_get_article_not_found(client):
    """获取不存在的文章返回 404"""
    r = client.get("/api/articles/99999")
    assert r.status_code == 404
