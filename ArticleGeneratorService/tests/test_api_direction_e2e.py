"""Direction API E2E tests — full API → Task → Result flow"""
from unittest.mock import patch, MagicMock, PropertyMock


def test_post_returns_task_id(auth_client):
    """API 返回 task_id 和 pending 状态（有真实账号时）"""
    acc = auth_client.post("/api/accounts", json={
        "platform": "test", "account_name": "test_direction_e2e"
    }).json()

    with patch("app.api.generate.trigger_direction_generation.delay") as mock_delay:
        mock_task = MagicMock()
        mock_task.id = "test-direction-task-123"
        mock_delay.return_value = mock_task

        resp = auth_client.post("/api/generate/directions", json={
            "account_id": acc["id"], "idea": "测试想法"
        })

    assert resp.status_code == 200
    data = resp.json()
    assert data["task_id"] == "test-direction-task-123"
    assert data["status"] == "pending"


def test_post_empty_idea_rejected(auth_client):
    """空想法返回 400"""
    acc = auth_client.post("/api/accounts", json={
        "platform": "test", "account_name": "test_empty_idea"
    }).json()

    resp = auth_client.post("/api/generate/directions", json={
        "account_id": acc["id"], "idea": "  "
    })
    assert resp.status_code == 400
    assert "不能为空" in resp.json()["detail"]


def test_post_nonexistent_account_rejected(auth_client):
    """不存在的账号返回 404"""
    resp = auth_client.post("/api/generate/directions", json={
        "account_id": 0, "idea": "测试"
    })
    assert resp.status_code == 404


def test_task_result_structure(auth_client):
    """成功任务返回符合 DirectionsResponse 的结构"""
    acc = auth_client.post("/api/accounts", json={
        "platform": "test", "account_name": "test_structure"
    }).json()

    mock_result = {
        "account_id": acc["id"],
        "directions": [
            {"id": "A", "title": "情感切入"},
            {"id": "B", "title": "数据切入"},
            {"id": "C", "title": "社会热点视角"},
        ]
    }

    with patch("app.api.generate.trigger_direction_generation.delay") as mock_delay:
        mock_task = MagicMock()
        mock_task.id = "test-structure-task"
        mock_delay.return_value = mock_task

        resp = auth_client.post("/api/generate/directions", json={
            "account_id": acc["id"], "idea": "测试"
        })
        assert resp.status_code == 200

    # Mock Celery AsyncResult — state is a property, use type() to set it
    mock_result_instance = MagicMock()
    type(mock_result_instance).state = PropertyMock(return_value="SUCCESS")
    mock_result_instance.result = mock_result
    mock_result_instance.successful.return_value = True

    with patch("celery.result.AsyncResult", return_value=mock_result_instance):
        result_resp = auth_client.get("/api/generate/task/test-structure-task/result")
        assert result_resp.status_code == 200
        data = result_resp.json()
        assert data["status"] == "success"
        assert "result" in data
        assert len(data["result"]["directions"]) == 3

        for d in data["result"]["directions"]:
            assert "id" in d and "title" in d
            assert isinstance(d["id"], str) and len(d["id"]) == 1
            assert isinstance(d["title"], str) and len(d["title"]) > 0


def test_empty_directions_still_valid(auth_client):
    """空 directions 仍为合法响应"""
    acc = auth_client.post("/api/accounts", json={
        "platform": "test", "account_name": "test_empty"
    }).json()

    mock_result = {"account_id": acc["id"], "directions": []}

    with patch("app.api.generate.trigger_direction_generation.delay") as mock_delay:
        mock_task = MagicMock()
        mock_task.id = "test-empty-task"
        mock_delay.return_value = mock_task
        auth_client.post("/api/generate/directions", json={
            "account_id": acc["id"], "idea": "测试"
        })

    mock_result_instance = MagicMock()
    type(mock_result_instance).state = PropertyMock(return_value="SUCCESS")
    mock_result_instance.result = mock_result
    mock_result_instance.successful.return_value = True

    with patch("celery.result.AsyncResult", return_value=mock_result_instance):
        result_resp = auth_client.get("/api/generate/task/test-empty-task/result")
        data = result_resp.json()
        assert data["status"] == "success"
        assert data["result"]["directions"] == []
