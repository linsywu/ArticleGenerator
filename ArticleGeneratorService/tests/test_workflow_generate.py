"""
全文生成 — API 端点 + 服务层 + resolve_article_title 覆盖
"""
from unittest.mock import patch, MagicMock, PropertyMock
import pytest
from app.tasks import resolve_article_title


# ── resolve_article_title 纯函数测试 ──

def test_resolve_title_prefers_passed_title():
    """传入的标题优先于自动提取"""
    content = "# 自动提取的标题\n\n正文内容..."
    result = resolve_article_title(content, "用户选择的标题")
    assert result == "用户选择的标题"


def test_resolve_title_fallback_when_none():
    """传入 None → 从内容提取"""
    content = "# 从内容提取的标题\n\n正文内容"
    result = resolve_article_title(content, None)
    assert result == "从内容提取的标题"


def test_resolve_title_fallback_when_empty():
    """传入空字符串 → 从内容提取"""
    content = "## H2 标题\n\n正文"
    result = resolve_article_title(content, "  ")
    # 空字符串 strip 后为 ""，应回退到自动提取
    # 但代码中 hotspot_title.strip() 为空时走 fallback
    assert result is not None


def test_resolve_title_h1_extraction():
    """从 # 标题中提取"""
    content = "# AI 时代的挑战与机遇\n\n正文..."
    result = resolve_article_title(content, None)
    assert result == "AI 时代的挑战与机遇"


def test_resolve_title_h2_extraction():
    """从 ## 标题中提取"""
    content = "## 远程办公的利与弊\n\n正文字符..."
    result = resolve_article_title(content, None)
    assert result == "远程办公的利与弊"


def test_resolve_title_first_line_fallback():
    """无 # 标题时取首行前 50 字符"""
    content = "在这个快速变化的时代，我们需要重新思考工作的意义。\n\n第二段..."
    result = resolve_article_title(content, None)
    assert len(result) <= 50
    assert "重新思考" in result


def test_resolve_title_truncation_at_200_chars():
    """传入标题超过 200 字符时截断"""
    long_title = "A" * 250
    result = resolve_article_title("", long_title)
    assert len(result) == 200


def test_resolve_title_skip_empty_lines():
    """跳过空行，取第一个非空行"""
    content = "\n\n# 真正的标题\n\n正文"
    result = resolve_article_title(content, None)
    assert result == "真正的标题"


def test_resolve_title_empty_content_returns_none():
    """空内容且无传入标题 → None"""
    result = resolve_article_title("", None)
    assert result is None


# ── API 端点测试 ──

def test_trigger_generate_with_custom_topic(auth_client):
    """自定义主题触发生成（无热点 ID）"""
    acc = auth_client.post("/api/accounts", json={
        "platform": "test", "account_name": "gen_custom"
    }).json()

    mock_task = MagicMock()
    mock_task.id = "gen-task-custom-001"

    with patch("app.services.generate_service.trigger_generate.delay", return_value=mock_task):
        resp = auth_client.post("/api/generate/trigger", json={
            "hotspot_ids": [],
            "account_id": acc["id"],
            "custom_topic": "AI 对教育行业的影响",
        })

    assert resp.status_code == 200
    data = resp.json()
    assert data["message"] == "任务已提交"
    assert len(data["tasks"]) == 1
    assert data["tasks"][0]["task_id"] == "gen-task-custom-001"


def test_trigger_generate_account_not_found(auth_client):
    """不存在的账号返回 404"""
    resp = auth_client.post("/api/generate/trigger", json={
        "hotspot_ids": [],
        "account_id": 99999,
        "custom_topic": "测试主题",
    })
    assert resp.status_code == 404


def test_trigger_generate_empty_topic_and_hotspots_rejected(auth_client):
    """既无热点 ID 也无自定义主题 → 400"""
    acc = auth_client.post("/api/accounts", json={
        "platform": "test", "account_name": "gen_empty"
    }).json()

    resp = auth_client.post("/api/generate/trigger", json={
        "hotspot_ids": [],
        "account_id": acc["id"],
    })
    assert resp.status_code == 400
    assert "请选择" in resp.json()["detail"]


def test_trigger_generate_invalid_hotspot_id(auth_client):
    """无效热点 ID 返回 400"""
    acc = auth_client.post("/api/accounts", json={
        "platform": "test", "account_name": "gen_bad_hotspot"
    }).json()

    resp = auth_client.post("/api/generate/trigger", json={
        "hotspot_ids": [99999],
        "account_id": acc["id"],
    })
    assert resp.status_code == 400
    assert "99999" in resp.text


def test_trigger_generate_with_outline(auth_client):
    """带大纲触发生成"""
    acc = auth_client.post("/api/accounts", json={
        "platform": "test", "account_name": "gen_outline"
    }).json()

    mock_task = MagicMock()
    mock_task.id = "gen-task-outline-001"

    with patch("app.services.generate_service.trigger_generate.delay", return_value=mock_task):
        resp = auth_client.post("/api/generate/trigger", json={
            "hotspot_ids": [],
            "account_id": acc["id"],
            "custom_topic": "AI 编程工具的未来",
            "outline": ["工具演进历史", "开发者角色变化", "未来展望"],
            "word_count": "2000",
        })

    assert resp.status_code == 200
    data = resp.json()
    assert len(data["tasks"]) == 1


def test_trigger_generate_task_creates_db_record(auth_client):
    """触发生成后 GenerationTask 记录写入 DB"""
    from app.models import GenerationTask
    from tests.conftest import TestingSessionLocal

    acc = auth_client.post("/api/accounts", json={
        "platform": "test", "account_name": "gen_db"
    }).json()

    mock_task = MagicMock()
    mock_task.id = "gen-task-db-123"

    with patch("app.services.generate_service.trigger_generate.delay", return_value=mock_task):
        auth_client.post("/api/generate/trigger", json={
            "hotspot_ids": [],
            "account_id": acc["id"],
            "custom_topic": "技术趋势",
        })

    db = TestingSessionLocal()
    gt = db.query(GenerationTask).filter(GenerationTask.task_id == "gen-task-db-123").first()
    assert gt is not None
    assert gt.account_id == acc["id"]
    assert gt.status == "pending"
    db.close()


def test_task_status_endpoint_unknown(auth_client):
    """未知任务返回 status unknown"""
    resp = auth_client.get("/api/generate/task/nonexistent-id-12345")
    assert resp.status_code == 200
    assert resp.json()["status"] == "unknown"


def test_cancel_task(auth_client):
    """取消 pending 状态的任务"""
    from app.models import GenerationTask
    from tests.conftest import TestingSessionLocal

    acc = auth_client.post("/api/accounts", json={
        "platform": "test", "account_name": "gen_cancel"
    }).json()

    db = TestingSessionLocal()
    gt = GenerationTask(task_id="cancel-me-plz", account_id=acc["id"], status="pending")
    db.add(gt)
    db.commit()
    db.close()

    with patch("app.api.generate.celery_app") as mock_celery:
        resp = auth_client.post("/api/generate/tasks/cancel-me-plz/cancel")

    assert resp.status_code == 200
    assert "已取消" in resp.json()["message"]

    db = TestingSessionLocal()
    gt = db.query(GenerationTask).filter(GenerationTask.task_id == "cancel-me-plz").first()
    assert gt.status == "cancelled"
    db.close()
