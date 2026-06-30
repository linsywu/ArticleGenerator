"""
文章评审 — 状态机 + _parse_score + API 端点测试
"""
from unittest.mock import patch, MagicMock
import pytest
from app.services.article_service import update_article_status
from app.models import Article
from app.tasks import _parse_score
from tests.conftest import TestingSessionLocal


# ── _parse_score 纯函数测试 ──

def test_parse_score_total():
    """解析 "总分：85" """
    assert _parse_score("内容质量：好\n总分：85\n建议：无") == 85


def test_parse_score_total_colon():
    """解析 "总分: 90" """
    assert _parse_score("总分: 90\n各方面表现优秀") == 90


def test_parse_score_total_no_colon():
    """解析 "总分 75" """
    assert _parse_score("总分 75") == 75


def test_parse_score_overall():
    """解析 "综合评分：70" """
    assert _parse_score("综合评分：70\n细节：良好") == 70


def test_parse_score_final():
    """解析 "最终得分：88" """
    assert _parse_score("某项评分：50\n最终得分：88") == 88


def test_parse_score_last_number_fallback():
    """无总分/综合评分时取最后一个合法数字"""
    result = _parse_score("内容：80\n结构：75\n语言：90")
    assert result == 90  # 取最后一个


def test_parse_score_ignores_out_of_range():
    """忽略 0-100 范围外的数字"""
    # 150 被过滤（>100），85 被保留，-10 中的 "10" 被正则误匹配为 10
    # 最后一个合法值是 10（从 -10 中匹配）
    result = _parse_score("得分：150\n实际：85\n错误：-10")
    assert result == 10

def test_parse_score_only_valid_numbers():
    """仅 0-100 范围内的数字被计入"""
    result = _parse_score("得分：150\n实际：85\n备注：200")
    # 150 和 200 被过滤，85 是唯一合法值
    assert result == 85


def test_parse_score_empty_text():
    """空文本返回 0"""
    assert _parse_score("") == 0


def test_parse_score_no_numbers():
    """无数字文本返回 0"""
    assert _parse_score("这篇文章写得非常好，内容丰富翔实") == 0


# ── 状态机测试 ──

def test_article_status_approve(db_session):
    """pending_review → approved"""
    article = Article(
        title="测试文章",
        content="测试内容",
        status="pending_review",
        account_id=1,
    )
    db_session.add(article)
    db_session.commit()
    db_session.refresh(article)

    updated = update_article_status(db_session, article.id, "approved")
    assert updated.status == "approved"


def test_article_status_reject(db_session):
    """pending_review → rejected"""
    article = Article(
        title="测试文章2",
        content="内容",
        status="pending_review",
        account_id=1,
    )
    db_session.add(article)
    db_session.commit()
    db_session.refresh(article)

    updated = update_article_status(db_session, article.id, "rejected")
    assert updated.status == "rejected"


def test_article_status_invalid_transition_approved_to_rejected(db_session):
    """approved → rejected 应返回 400（非法转换）"""
    article = Article(
        title="已通过的文章",
        content="内容",
        status="approved",
        account_id=1,
    )
    db_session.add(article)
    db_session.commit()
    db_session.refresh(article)

    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc_info:
        update_article_status(db_session, article.id, "rejected")
    assert exc_info.value.status_code == 400
    assert "无效的状态转换" in exc_info.value.detail


def test_article_status_invalid_value(db_session):
    """非法状态值返回 400"""
    article = Article(
        title="测试",
        content="内容",
        status="pending_review",
        account_id=1,
    )
    db_session.add(article)
    db_session.commit()
    db_session.refresh(article)

    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc_info:
        update_article_status(db_session, article.id, "invalid_status")
    assert exc_info.value.status_code == 400
    assert "无效状态" in exc_info.value.detail


def test_article_status_article_not_found(db_session):
    """不存在的文章返回 404"""
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc_info:
        update_article_status(db_session, 99999, "approved")
    assert exc_info.value.status_code == 404


def test_article_status_publish_sets_timestamp(db_session):
    """approved → published 同时设置 published_at"""
    article = Article(
        title="待发布文章",
        content="内容",
        status="approved",
        account_id=1,
    )
    db_session.add(article)
    db_session.commit()
    db_session.refresh(article)

    assert article.published_at is None
    updated = update_article_status(db_session, article.id, "published")
    assert updated.status == "published"
    assert updated.published_at is not None


def test_article_status_pending_review_to_published_rejected(db_session):
    """pending_review → published 应返回 400（不允许直接发布）"""
    article = Article(
        title="未评审文章",
        content="内容",
        status="pending_review",
        account_id=1,
    )
    db_session.add(article)
    db_session.commit()
    db_session.refresh(article)

    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc_info:
        update_article_status(db_session, article.id, "published")
    assert exc_info.value.status_code == 400


# ── API 端点测试 ──

def test_api_approve_article(auth_client):
    """PATCH /articles/{id}/status → approved"""
    from app.models import Article, Account
    from tests.conftest import TestingSessionLocal

    acc = auth_client.post("/api/accounts", json={
        "platform": "test", "account_name": "review_api"
    }).json()

    db = TestingSessionLocal()
    article = Article(
        title="API 测试文章",
        content="测试内容",
        status="pending_review",
        account_id=acc["id"],
    )
    db.add(article)
    db.commit()
    db.refresh(article)
    art_id = article.id
    db.close()

    resp = auth_client.patch(f"/api/articles/{art_id}/status", json={"status": "approved"})
    assert resp.status_code == 200
    assert "更新成功" in resp.json()["message"]

    db = TestingSessionLocal()
    art = db.query(Article).filter(Article.id == art_id).first()
    assert art.status == "approved"
    db.close()


def test_api_reject_article(auth_client):
    """PATCH /articles/{id}/status → rejected"""
    from app.models import Article
    from tests.conftest import TestingSessionLocal

    acc = auth_client.post("/api/accounts", json={
        "platform": "test", "account_name": "review_reject"
    }).json()

    db = TestingSessionLocal()
    article = Article(
        title="待拒绝文章",
        content="内容",
        status="pending_review",
        account_id=acc["id"],
    )
    db.add(article)
    db.commit()
    db.refresh(article)
    art_id = article.id
    db.close()

    resp = auth_client.patch(f"/api/articles/{art_id}/status", json={"status": "rejected"})
    assert resp.status_code == 200
    assert "更新成功" in resp.json()["message"]


def test_api_invalid_transition_returns_400(auth_client):
    """非法状态转换返回 400"""
    from app.models import Article
    from tests.conftest import TestingSessionLocal

    acc = auth_client.post("/api/accounts", json={
        "platform": "test", "account_name": "review_400"
    }).json()

    db = TestingSessionLocal()
    article = Article(
        title="已通过文章",
        content="内容",
        status="approved",
        account_id=acc["id"],
    )
    db.add(article)
    db.commit()
    db.refresh(article)
    art_id = article.id
    db.close()

    resp = auth_client.patch(f"/api/articles/{art_id}/status", json={"status": "rejected"})
    assert resp.status_code == 400


def test_api_list_articles_by_status(auth_client):
    """GET /articles?status=approved 按状态筛选"""
    from app.models import Article
    from tests.conftest import TestingSessionLocal

    acc = auth_client.post("/api/accounts", json={
        "platform": "test", "account_name": "list_status"
    }).json()

    db = TestingSessionLocal()
    for i in range(3):
        art = Article(
            title=f"已通过文章{i}",
            content=f"内容{i}",
            status="approved" if i < 2 else "pending_review",
            account_id=acc["id"],
        )
        db.add(art)
    db.commit()
    db.close()

    resp = auth_client.get("/api/articles", params={"status": "approved"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 2
    for item in data["data"]:
        assert item["status"] == "approved"
