"""
文章发布 — API 端点 + 状态转换 + 文章更新
"""
import pytest
from app.models import Article
from app.services.article_service import update_article_status
from tests.conftest import TestingSessionLocal


# ── API 端点测试 ──

def test_api_publish_article(auth_client):
    """PATCH /articles/{id}/status → published"""
    acc = auth_client.post("/api/accounts", json={
        "platform": "test", "account_name": "publish_api"
    }).json()

    db = TestingSessionLocal()
    article = Article(
        title="待发布文章",
        content="发布内容",
        status="approved",
        account_id=acc["id"],
    )
    db.add(article)
    db.commit()
    db.refresh(article)
    art_id = article.id
    db.close()

    resp = auth_client.patch(f"/api/articles/{art_id}/status", json={"status": "published"})
    assert resp.status_code == 200
    assert "更新成功" in resp.json()["message"]

    db = TestingSessionLocal()
    art = db.query(Article).filter(Article.id == art_id).first()
    assert art.status == "published"
    assert art.published_at is not None
    db.close()


def test_api_publish_from_pending_review_rejected(auth_client):
    """pending_review → published 应返回 400"""
    acc = auth_client.post("/api/accounts", json={
        "platform": "test", "account_name": "publish_skip"
    }).json()

    db = TestingSessionLocal()
    article = Article(
        title="跳过评审",
        content="内容",
        status="pending_review",
        account_id=acc["id"],
    )
    db.add(article)
    db.commit()
    db.refresh(article)
    art_id = article.id
    db.close()

    resp = auth_client.patch(f"/api/articles/{art_id}/status", json={"status": "published"})
    assert resp.status_code == 400


def test_api_list_articles_by_status_approved(auth_client):
    """GET /articles?status=approved 筛选已通过文章"""
    acc = auth_client.post("/api/accounts", json={
        "platform": "test", "account_name": "pub_list"
    }).json()

    db = TestingSessionLocal()
    for i in range(5):
        art = Article(
            title=f"文章{i}",
            content=f"内容{i}",
            status="approved" if i < 3 else "pending_review",
            account_id=acc["id"],
        )
        db.add(art)
    db.commit()
    db.close()

    resp = auth_client.get("/api/articles", params={"status": "approved"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 3
    for item in data["data"]:
        assert item["status"] == "approved"


def test_api_published_articles_appear_in_list(auth_client):
    """已发布文章出现在 status=published 筛选中"""
    acc = auth_client.post("/api/accounts", json={
        "platform": "test", "account_name": "pub_published"
    }).json()

    db = TestingSessionLocal()
    article = Article(
        title="已发布文章",
        content="已发布内容",
        status="published",
        account_id=acc["id"],
    )
    db.add(article)
    db.commit()
    db.close()

    resp = auth_client.get("/api/articles", params={"status": "published"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1


def test_update_article_content(auth_client):
    """PUT /articles/{id} 更新文章内容"""
    acc = auth_client.post("/api/accounts", json={
        "platform": "test", "account_name": "update_art"
    }).json()

    db = TestingSessionLocal()
    article = Article(
        title="原始文章",
        content="原始内容",
        status="approved",
        account_id=acc["id"],
    )
    db.add(article)
    db.commit()
    db.refresh(article)
    art_id = article.id
    db.close()

    resp = auth_client.put(f"/api/articles/{art_id}", json={
        "content": "更新后的内容",
        "review_notes": "编辑了开头段落",
    })
    assert resp.status_code == 200

    db = TestingSessionLocal()
    art = db.query(Article).filter(Article.id == art_id).first()
    assert art.content == "更新后的内容"
    assert "编辑了开头段落" in art.review_notes
    db.close()


def test_update_article_not_found(auth_client):
    """PUT 不存在的文章返回 404"""
    resp = auth_client.put("/api/articles/99999", json={"content": "新内容"})
    assert resp.status_code == 404
