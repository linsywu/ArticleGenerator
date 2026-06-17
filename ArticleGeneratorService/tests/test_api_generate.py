"""
文章生成 API 测试用例（mock Celery）
"""
from unittest.mock import MagicMock, patch


def test_trigger_generate_account_not_found(auth_client):
    """账号不存在时返回 404"""
    r = auth_client.post("/api/generate/trigger", json={
        "hotspot_ids": [1],
        "account_id": 99999,
    })
    assert r.status_code == 404


def test_trigger_generate_success(auth_client):
    """触发生成成功，返回任务列表"""
    acc = auth_client.post("/api/accounts", json={"platform": "P", "account_name": "A"}).json()
    hot = auth_client.post("/api/hotspots", json={"title": "H", "source": "S", "heat": 1}).json()
    mock_task = MagicMock()
    mock_task.id = "mock-task-id-123"

    with patch("app.services.generate_service.trigger_generate") as m:
        m.delay.return_value = mock_task
        r = auth_client.post("/api/generate/trigger", json={
            "hotspot_ids": [hot["id"]],
            "account_id": acc["id"],
        })
    assert r.status_code == 200
    assert "tasks" in r.json()
    assert len(r.json()["tasks"]) == 1


def test_trigger_refine_article_not_found(auth_client):
    """文章不存在时返回 404"""
    r = auth_client.post("/api/generate/refine/99999", json={"keywords": "测试"})
    assert r.status_code == 404


def test_get_task_status_unknown(auth_client):
    """未知任务返回 status unknown"""
    r = auth_client.get("/api/generate/task/unknown-id")
    assert r.status_code == 200
    assert r.json()["status"] == "unknown"


def test_get_tasks_batch(auth_client):
    """批量查询任务状态"""
    r = auth_client.get("/api/generate/tasks", params={"task_ids": "id1,id2,id3"})
    assert r.status_code == 200
    j = r.json()
    assert "tasks" in j
    assert j["tasks"] == []


def test_trigger_refine_creates_refine_task(auth_client):
    """微调触发时创建 RefineTask 记录"""
    from app.models import Article, RefineTask
    from tests.conftest import TestingSessionLocal

    acc = auth_client.post("/api/accounts", json={"platform": "P", "account_name": "A"}).json()
    hot = auth_client.post("/api/hotspots", json={"title": "H", "source": "S", "heat": 1}).json()
    acc_id, hot_id = acc["id"], hot["id"]
    db = TestingSessionLocal()
    art = Article(hotspot_id=hot_id, account_id=acc_id, content="内容", status="pending_review")
    db.add(art)
    db.commit()
    db.refresh(art)
    art_id = art.id
    db.close()

    with patch("app.api.generate.trigger_refine") as m:
        mock_task = MagicMock()
        mock_task.id = "refine-task-123"
        m.delay.return_value = mock_task
        r = auth_client.post(f"/api/generate/refine/{art_id}", json={"keywords": "测试"})
    assert r.status_code == 200
    assert r.json().get("task_id") == "refine-task-123"

    db = TestingSessionLocal()
    rt = db.query(RefineTask).filter(RefineTask.task_id == "refine-task-123").first()
    assert rt is not None
    assert rt.article_id == art_id
    assert rt.status == "pending"
    db.close()

    # 可查询微调任务状态
    r2 = auth_client.get("/api/generate/refine-task/refine-task-123")
    assert r2.status_code == 200
    assert r2.json()["status"] == "pending"


def test_task_list_empty(auth_client):
    """任务列表空时返回空"""
    r = auth_client.get("/api/generate/tasks/list")
    assert r.status_code == 200
    assert r.json()["data"] == []
    assert r.json()["total"] == 0


def test_task_list_with_tasks(auth_client):
    """任务列表返回任务"""
    from app.models import GenerationTask
    from tests.conftest import TestingSessionLocal

    acc = auth_client.post("/api/accounts", json={"platform": "P", "account_name": "A"}).json()
    hot = auth_client.post("/api/hotspots", json={"title": "H", "source": "S", "heat": 1}).json()
    db = TestingSessionLocal()
    gt = GenerationTask(task_id="t1", hotspot_id=hot["id"], account_id=acc["id"], status="success", article_id=1)
    db.add(gt)
    db.commit()
    db.close()

    r = auth_client.get("/api/generate/tasks/list")
    assert r.status_code == 200
    assert len(r.json()["data"]) == 1
    assert r.json()["data"][0]["status"] == "success"
    assert r.json()["total"] == 1


def test_cancel_task(auth_client):
    """取消任务"""
    from app.models import GenerationTask
    from tests.conftest import TestingSessionLocal

    acc = auth_client.post("/api/accounts", json={"platform": "P", "account_name": "A"}).json()
    hot = auth_client.post("/api/hotspots", json={"title": "H", "source": "S", "heat": 1}).json()
    db = TestingSessionLocal()
    gt = GenerationTask(task_id="cancel-me", hotspot_id=hot["id"], account_id=acc["id"], status="pending")
    db.add(gt)
    db.commit()
    db.close()

    with patch("app.api.generate.celery_app") as mock_celery:
        r = auth_client.post("/api/generate/tasks/cancel-me/cancel")
    assert r.status_code == 200
    assert r.json()["message"] == "已取消"

    db = TestingSessionLocal()
    gt = db.query(GenerationTask).filter(GenerationTask.task_id == "cancel-me").first()
    assert gt.status == "cancelled"
    db.close()
