"""
全流程集成测试：Mock LLM，串联完整文章创作流程
流程：选择账号 → 输入想法 → 创作方向 → 生成大纲 → 生成标题 → 生成全文 → 评审 → 微调 → 发布
"""
from unittest.mock import patch, MagicMock, PropertyMock
import pytest
import json
from app.models import Article, GenerationTask, RefineTask
from tests.conftest import TestingSessionLocal


# ── 辅助：模拟 LLM 返回 ──

def _mock_direction_response():
    return {"content": '[{"id": "A", "title": "技术伦理视角"}, {"id": "B", "title": "社会影响分析"}, {"id": "C", "title": "个人隐私保护"}]'}


def _mock_outline_response():
    return {"content": '["引言：AI时代的伦理挑战", "核心论点：技术发展的双刃剑", "案例一：数据隐私泄露事件", "案例二：算法歧视问题", "解决路径：多方共治框架", "结论：以人为本的科技发展观"]'}


def _mock_title_response():
    return {"content": '["AI时代的技术伦理：我们该如何选择？", "当算法决定一切：技术伦理的三重困境", "不完美的代码：AI决策中的偏见与救赎", "数据隐私的边界在哪里？一个普通人的思考"]'}


def _mock_generate_response():
    return {"content": "# AI时代的技术伦理：我们该如何选择？\n\n在这个算法无处不在的时代...\n\n文章内容充实有力..."}


def _mock_refine_response():
    return {"content": "微调优化后的文章内容，语言更加精炼..."}


# ── 全流程集成测试 ──

def test_full_creation_flow_mocked(auth_client):
    """Mock LLM，完整串联 direction→outline→title→generate→review→refine→publish"""

    # ═══ Step 0: 创建账号 ═══
    acc = auth_client.post("/api/accounts", json={
        "platform": "公众号", "account_name": "全流程测试账号"
    }).json()
    account_id = acc["id"]

    # ═══ Step 1-2: 生成写作方向 ═══
    with patch("app.api.generate.trigger_direction_generation.delay") as mock_dir:
        mock_dir_task = MagicMock()
        mock_dir_task.id = "e2e-direction-task"
        mock_dir.return_value = mock_dir_task

        resp = auth_client.post("/api/generate/directions", json={
            "account_id": account_id,
            "idea": "AI 技术伦理问题",
        })
        assert resp.status_code == 200
        assert resp.json()["task_id"] == "e2e-direction-task"

    # 模拟 Celery 任务成功
    mock_dir_result = MagicMock()
    type(mock_dir_result).state = PropertyMock(return_value="SUCCESS")
    mock_dir_result.result = {
        "account_id": account_id,
        "directions": [
            {"id": "A", "title": "技术伦理视角"},
            {"id": "B", "title": "社会影响分析"},
            {"id": "C", "title": "个人隐私保护"},
        ]
    }
    mock_dir_result.successful.return_value = True

    with patch("celery.result.AsyncResult", return_value=mock_dir_result):
        result_resp = auth_client.get("/api/generate/task/e2e-direction-task/result")
        assert result_resp.json()["status"] == "success"
        directions = result_resp.json()["result"]["directions"]
        assert len(directions) == 3

    selected_direction = directions[0]["title"]

    # ═══ Step 3: 生成大纲 ═══
    with patch("app.api.generate.trigger_outline_generation.delay") as mock_outline:
        mock_outline_task = MagicMock()
        mock_outline_task.id = "e2e-outline-task"
        mock_outline.return_value = mock_outline_task

        resp = auth_client.post("/api/generate/outline", json={
            "account_id": account_id,
            "idea": "AI 技术伦理问题",
            "direction": selected_direction,
        })
        assert resp.status_code == 200
        assert resp.json()["task_id"] == "e2e-outline-task"

    # 模拟大纲任务成功
    mock_outline_result = MagicMock()
    type(mock_outline_result).state = PropertyMock(return_value="SUCCESS")
    mock_outline_result.result = {
        "account_id": account_id,
        "outline": ["引言", "核心论点", "案例一", "案例二", "结论"],
    }
    mock_outline_result.successful.return_value = True

    with patch("celery.result.AsyncResult", return_value=mock_outline_result):
        result_resp = auth_client.get("/api/generate/task/e2e-outline-task/result")
        assert result_resp.json()["status"] == "success"
        outline_points = result_resp.json()["result"]["outline"]
        assert len(outline_points) >= 3

    # ═══ Step 4: 生成标题 ═══
    with patch("app.api.generate.trigger_title_generation.delay") as mock_title:
        mock_title_task = MagicMock()
        mock_title_task.id = "e2e-title-task"
        mock_title.return_value = mock_title_task

        resp = auth_client.post("/api/generate/titles", json={
            "account_id": account_id,
            "idea": "AI 技术伦理问题",
            "direction": selected_direction,
            "outline": outline_points,
        })
        assert resp.status_code == 200
        assert resp.json()["task_id"] == "e2e-title-task"

    # 模拟标题任务成功
    mock_title_result = MagicMock()
    type(mock_title_result).state = PropertyMock(return_value="SUCCESS")
    mock_title_result.result = {
        "account_id": account_id,
        "titles": [
            "AI时代的技术伦理：我们该如何选择？",
            "当算法决定一切：技术伦理的三重困境",
        ]
    }
    mock_title_result.successful.return_value = True

    with patch("celery.result.AsyncResult", return_value=mock_title_result):
        result_resp = auth_client.get("/api/generate/task/e2e-title-task/result")
        assert result_resp.json()["status"] == "success"
        titles = result_resp.json()["result"]["titles"]
        assert len(titles) >= 2
        selected_title = titles[0]

    # ═══ Step 5-6: 生成全文 ═══
    with patch("app.services.generate_service.trigger_generate.delay") as mock_gen:
        mock_gen_task = MagicMock()
        mock_gen_task.id = "e2e-generate-task"
        mock_gen.return_value = mock_gen_task

        resp = auth_client.post("/api/generate/trigger", json={
            "hotspot_ids": [],
            "account_id": account_id,
            "custom_topic": f"{selected_title}\n\nAI 技术伦理问题",
            "outline": outline_points,
        })
        assert resp.status_code == 200
        assert len(resp.json()["tasks"]) == 1

    # 验证 GenerationTask 已写入
    db = TestingSessionLocal()
    gt = db.query(GenerationTask).filter(GenerationTask.task_id == "e2e-generate-task").first()
    assert gt is not None
    assert gt.status == "pending"

    # 模拟全文生成完成
    article = Article(
        title=selected_title,
        content="这是 AI 生成的文章全文内容，讲述技术伦理相关问题...",
        status="pending_review",
        account_id=account_id,
    )
    db.add(article)
    db.commit()
    db.refresh(article)
    article_id = article.id
    gt.status = "success"
    gt.article_id = article_id
    db.commit()
    db.close()

    # 验证文章已创建
    resp = auth_client.get(f"/api/articles/{article_id}")
    assert resp.status_code == 200
    assert resp.json()["status"] == "pending_review"

    # ═══ Step 7: 评审 — 通过 ═══
    resp = auth_client.patch(f"/api/articles/{article_id}/status", json={"status": "approved"})
    assert resp.status_code == 200
    assert "更新成功" in resp.json()["message"]

    db = TestingSessionLocal()
    art = db.query(Article).filter(Article.id == article_id).first()
    assert art.status == "approved"
    db.close()

    # ═══ Step 8: 微调 ═══
    with patch("app.api.generate.trigger_refine.delay") as mock_refine:
        mock_refine_task = MagicMock()
        mock_refine_task.id = "e2e-refine-task"
        mock_refine.return_value = mock_refine_task

        resp = auth_client.post(f"/api/generate/refine/{article_id}", json={
            "keywords": "增加数据案例，优化结论部分"
        })
        assert resp.status_code == 200
        assert resp.json()["task_id"] == "e2e-refine-task"

    # 模拟微调完成：更新内容 + 重置状态
    db = TestingSessionLocal()
    art = db.query(Article).filter(Article.id == article_id).first()
    art.content = "微调后的文章内容，增加了数据案例..."
    art.status = "pending_review"
    art.refine_history = json.dumps([{"keywords": "增加数据案例，优化结论部分", "prev_len": 30}])

    rt = db.query(RefineTask).filter(RefineTask.task_id == "e2e-refine-task").first()
    assert rt is not None
    rt.status = "success"
    db.commit()
    db.close()

    # 验证微调后状态回到 pending_review
    db = TestingSessionLocal()
    art = db.query(Article).filter(Article.id == article_id).first()
    assert art.status == "pending_review"
    assert "数据案例" in art.content
    assert art.refine_history is not None
    db.close()

    # ═══ Step 9: 再次评审通过 → 发布 ═══
    resp = auth_client.patch(f"/api/articles/{article_id}/status", json={"status": "approved"})
    assert resp.status_code == 200

    resp = auth_client.patch(f"/api/articles/{article_id}/status", json={"status": "published"})
    assert resp.status_code == 200
    assert "更新成功" in resp.json()["message"]

    # 验证最终状态
    db = TestingSessionLocal()
    art = db.query(Article).filter(Article.id == article_id).first()
    assert art.status == "published"
    assert art.published_at is not None
    db.close()

    # ── 验证全流程数据完整性 ──
    db = TestingSessionLocal()
    art = db.query(Article).filter(Article.id == article_id).first()
    assert art.status == "published"
    assert art.title == selected_title
    assert art.content is not None and len(art.content) > 0
    assert art.account_id == account_id
    assert art.published_at is not None

    # 验证相关任务记录
    gt = db.query(GenerationTask).filter(GenerationTask.task_id == "e2e-generate-task").first()
    assert gt.status == "success"
    assert gt.article_id == article_id

    rt = db.query(RefineTask).filter(RefineTask.task_id == "e2e-refine-task").first()
    assert rt.status == "success"
    db.close()


# ── 各步骤输入验证 ──

def test_createview_validation_direction_empty_idea(auth_client):
    """方向生成：空想法被拒绝"""
    resp = auth_client.post("/api/generate/directions", json={
        "account_id": 1, "idea": "  "
    })
    assert resp.status_code == 400


def test_createview_validation_outline_empty_idea(auth_client):
    """大纲生成：空想法被拒绝"""
    acc = auth_client.post("/api/accounts", json={
        "platform": "test", "account_name": "val_outline"
    }).json()
    resp = auth_client.post("/api/generate/outline", json={
        "account_id": acc["id"], "idea": "  ", "direction": "有效方向"
    })
    assert resp.status_code == 400


def test_createview_validation_outline_empty_direction(auth_client):
    """大纲生成：空方向被拒绝"""
    acc = auth_client.post("/api/accounts", json={
        "platform": "test", "account_name": "val_dir_empty"
    }).json()
    resp = auth_client.post("/api/generate/outline", json={
        "account_id": acc["id"], "idea": "有效想法", "direction": "  "
    })
    assert resp.status_code == 400


def test_createview_validation_title_empty_idea(auth_client):
    """标题生成：空想法被拒绝"""
    acc = auth_client.post("/api/accounts", json={
        "platform": "test", "account_name": "val_title"
    }).json()
    resp = auth_client.post("/api/generate/titles", json={
        "account_id": acc["id"], "idea": "  ", "direction": "方向", "outline": ["要点1"]
    })
    assert resp.status_code == 400


def test_createview_validation_generate_empty(auth_client):
    """全文生成：无热点无主题被拒绝"""
    acc = auth_client.post("/api/accounts", json={
        "platform": "test", "account_name": "val_gen"
    }).json()
    resp = auth_client.post("/api/generate/trigger", json={
        "hotspot_ids": [], "account_id": acc["id"]
    })
    assert resp.status_code == 400


# ── 边界场景 ──

def test_article_idempotent_status_update(auth_client):
    """重复状态更新：第一次成功，第二次拒绝"""
    from app.models import Article
    from tests.conftest import TestingSessionLocal

    acc = auth_client.post("/api/accounts", json={
        "platform": "test", "account_name": "idempotent"
    }).json()

    db = TestingSessionLocal()
    art = Article(title="幂等测试", content="内容", status="pending_review", account_id=acc["id"])
    db.add(art)
    db.commit()
    db.refresh(art)
    art_id = art.id
    db.close()

    # 第一次 approve 成功
    resp = auth_client.patch(f"/api/articles/{art_id}/status", json={"status": "approved"})
    assert resp.status_code == 200

    # 第二次 approve 应拒绝（已是 approved，不允许重复转换）
    resp = auth_client.patch(f"/api/articles/{art_id}/status", json={"status": "approved"})
    # approved → approved 不在 ALLOWED_TRANSITIONS 中
    assert resp.status_code == 400


def test_direction_empty_directions_still_valid(auth_client):
    """空 directions 仍是合法响应"""
    acc = auth_client.post("/api/accounts", json={
        "platform": "test", "account_name": "empty_dir"
    }).json()

    with patch("app.api.generate.trigger_direction_generation.delay") as mock_delay:
        mock_task = MagicMock()
        mock_task.id = "empty-dir-task"
        mock_delay.return_value = mock_task
        auth_client.post("/api/generate/directions", json={
            "account_id": acc["id"], "idea": "测试"
        })

    mock_result = MagicMock()
    type(mock_result).state = PropertyMock(return_value="SUCCESS")
    mock_result.result = {"account_id": acc["id"], "directions": []}
    mock_result.successful.return_value = True

    with patch("celery.result.AsyncResult", return_value=mock_result):
        resp = auth_client.get("/api/generate/task/empty-dir-task/result")
        assert resp.status_code == 200
        assert resp.json()["result"]["directions"] == []
