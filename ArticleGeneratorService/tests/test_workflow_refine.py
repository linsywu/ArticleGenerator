"""
微调 — API 端点 + DB 验证 + 集成测试
"""
from unittest.mock import patch, MagicMock
import pytest
from app.models import Article, RefineTask
from tests.conftest import TestingSessionLocal


# ── API 端点测试 ──

def test_refine_article_not_found(auth_client):
    """不存在的文章返回 404"""
    resp = auth_client.post("/api/generate/refine/99999", json={"keywords": "增加幽默感"})
    assert resp.status_code == 404


def test_refine_creates_refine_task_db_record(auth_client):
    """触发微调后 RefineTask 写入 DB"""
    from app.models import Article
    from tests.conftest import TestingSessionLocal

    acc = auth_client.post("/api/accounts", json={
        "platform": "test", "account_name": "refine_db"
    }).json()

    db = TestingSessionLocal()
    art = Article(
        title="待微调文章",
        content="原始内容",
        status="pending_review",
        account_id=acc["id"],
    )
    db.add(art)
    db.commit()
    db.refresh(art)
    art_id = art.id
    db.close()

    with patch("app.api.generate.trigger_refine.delay") as mock_delay:
        mock_task = MagicMock()
        mock_task.id = "refine-task-db-001"
        mock_delay.return_value = mock_task
        resp = auth_client.post(f"/api/generate/refine/{art_id}", json={"keywords": "增加幽默感"})

    assert resp.status_code == 200
    assert resp.json()["task_id"] == "refine-task-db-001"

    db = TestingSessionLocal()
    rt = db.query(RefineTask).filter(RefineTask.task_id == "refine-task-db-001").first()
    assert rt is not None
    assert rt.article_id == art_id
    assert rt.status == "pending"
    db.close()


def test_refine_task_status_endpoint(auth_client):
    """GET /generate/refine-task/{id} 返回任务状态"""
    from app.models import Article, RefineTask
    from tests.conftest import TestingSessionLocal

    acc = auth_client.post("/api/accounts", json={
        "platform": "test", "account_name": "refine_status"
    }).json()

    db = TestingSessionLocal()
    art = Article(
        title="状态查询文章",
        content="内容",
        status="pending_review",
        account_id=acc["id"],
    )
    db.add(art)
    db.commit()
    db.refresh(art)
    saved_art_id = art.id  # 在 session 关闭前保存

    rt = RefineTask(
        task_id="refine-status-001",
        article_id=saved_art_id,
        status="pending",
    )
    db.add(rt)
    db.commit()
    db.close()

    resp = auth_client.get("/api/generate/refine-task/refine-status-001")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "pending"
    assert data["article_id"] == saved_art_id


def test_refine_task_status_unknown(auth_client):
    """未知微调任务返回 status unknown"""
    resp = auth_client.get("/api/generate/refine-task/nonexistent-xyz")
    assert resp.status_code == 200
    assert resp.json()["status"] == "unknown"


# ── 集成测试：refine 完整流程（通过 API mock Celery task）──

def test_refine_full_flow(auth_client):
    """完整微调流程：创建文章 → 触发 refine → 模拟 task 完成 → 验证状态"""
    from app.models import Article, RefineTask, Account
    from app.database import SessionLocal
    import json

    # 1. 创建账号和已通过的 article
    acc = auth_client.post("/api/accounts", json={
        "platform": "test", "account_name": "refine_flow"
    }).json()

    db = SessionLocal()
    art = Article(
        title="待微调文章",
        content="原始文章内容，需要微调优化",
        status="approved",
        account_id=acc["id"],
    )
    db.add(art)
    db.commit()
    db.refresh(art)
    art_id = art.id
    db.close()

    # 2. 触发 refine API
    with patch("app.api.generate.trigger_refine.delay") as mock_delay:
        mock_task = MagicMock()
        mock_task.id = "refine-flow-task"
        mock_delay.return_value = mock_task
        resp = auth_client.post(f"/api/generate/refine/{art_id}", json={"keywords": "增加幽默感"})
        assert resp.status_code == 200

    # 3. 验证 RefineTask 写入
    db = SessionLocal()
    rt = db.query(RefineTask).filter(RefineTask.task_id == "refine-flow-task").first()
    assert rt is not None
    assert rt.article_id == art_id
    assert rt.status == "pending"

    # 4. 模拟 Celery task 完成后的 DB 更新
    art = db.query(Article).filter(Article.id == art_id).first()
    art.content = "微调后的新内容，更加幽默"
    art.status = "pending_review"
    art.refine_history = json.dumps([{"keywords": "增加幽默感", "prev_len": 8}], ensure_ascii=False)
    rt.status = "success"
    db.commit()
    db.close()

    # 5. 验证状态变更
    db = SessionLocal()
    art = db.query(Article).filter(Article.id == art_id).first()
    assert art.status == "pending_review"
    assert "微调后" in art.content

    rt = db.query(RefineTask).filter(RefineTask.task_id == "refine-flow-task").first()
    assert rt.status == "success"
    db.close()


def test_refine_resets_status_to_pending_review(auth_client):
    """微调完成后文章状态回到 pending_review"""
    from app.models import Article
    from app.database import SessionLocal
    import json

    acc = auth_client.post("/api/accounts", json={
        "platform": "test", "account_name": "refine_reset"
    }).json()

    db = SessionLocal()
    art = Article(
        title="已通过待微调",
        content="内容",
        status="approved",
        account_id=acc["id"],
    )
    db.add(art)
    db.commit()
    db.refresh(art)
    art_id = art.id

    rt = RefineTask(task_id="refine-reset-task", article_id=art_id, status="pending")
    db.add(rt)
    db.commit()

    # 模拟 refine task 完成
    art.status = "pending_review"
    art.content = "微调后内容"
    art.refine_history = json.dumps([{"keywords": "优化", "prev_len": 2}])
    rt.status = "success"
    db.commit()
    db.close()

    # 验证
    db = SessionLocal()
    art = db.query(Article).filter(Article.id == art_id).first()
    assert art.status == "pending_review"
    db.close()


def test_refine_task_failure_records_error(auth_client):
    """微调任务失败时记录错误信息"""
    from app.models import Article
    from app.database import SessionLocal

    acc = auth_client.post("/api/accounts", json={
        "platform": "test", "account_name": "refine_fail"
    }).json()

    db = SessionLocal()
    art = Article(
        title="失败测试",
        content="内容",
        status="pending_review",
        account_id=acc["id"],
    )
    db.add(art)
    db.commit()
    db.refresh(art)
    art_id = art.id

    rt = RefineTask(task_id="refine-fail-task", article_id=art_id, status="pending")
    db.add(rt)
    db.commit()

    # 模拟任务失败
    rt.status = "failed"
    rt.error_message = "LLM 返回内容为空"
    db.commit()
    db.close()

    # 验证错误信息已持久化
    db = SessionLocal()
    rt = db.query(RefineTask).filter(RefineTask.task_id == "refine-fail-task").first()
    assert rt.status == "failed"
    assert "返回内容为空" in rt.error_message
    db.close()
