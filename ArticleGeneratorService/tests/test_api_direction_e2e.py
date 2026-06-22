"""Direction API E2E tests — full API → Task → Result flow"""
from unittest.mock import patch, MagicMock


class TestDirectionAPI:
    """POST /api/generate/directions → poll result → verify"""

    def test_post_returns_task_id(self, auth_client):
        """API 返回 task_id 和 pending 状态"""
        with patch("app.api.generate.trigger_direction_generation.delay") as mock_delay:
            mock_task = MagicMock()
            mock_task.id = "test-direction-task-123"
            mock_delay.return_value = mock_task

            resp = auth_client.post("/api/generate/directions", json={
                "account_id": 0, "idea": "测试想法"
            })

        assert resp.status_code == 200
        data = resp.json()
        assert data["task_id"] == "test-direction-task-123"
        assert data["status"] == "pending"

    def test_post_empty_idea_rejected(self, auth_client):
        """空想法返回 400"""
        resp = auth_client.post("/api/generate/directions", json={
            "account_id": 0, "idea": "  "
        })
        assert resp.status_code == 400
        assert "不能为空" in resp.json()["detail"]

    def test_task_result_has_correct_structure(self, auth_client):
        """任务结果返回 structure 符合 DirectionsResponse schema"""
        mock_result = {
            "account_id": 0,
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
                "account_id": 0, "idea": "测试"
            })
            assert resp.status_code == 200

        # Mock the Celery AsyncResult to return our pre-built result
        with patch("app.api.generate.AsyncResult") as mock_async_result:
            mock_async_result.return_value.status = "SUCCESS"
            mock_async_result.return_value.result = mock_result
            mock_async_result.return_value.successful.return_value = True

            result_resp = auth_client.get("/api/generate/task/test-structure-task/result")
            assert result_resp.status_code == 200
            data = result_resp.json()
            assert data["status"] == "success"
            assert "result" in data
            assert "directions" in data["result"]
            assert len(data["result"]["directions"]) == 3

            for d in data["result"]["directions"]:
                assert "id" in d
                assert "title" in d
                assert isinstance(d["id"], str) and len(d["id"]) == 1
                assert isinstance(d["title"], str) and len(d["title"]) > 0

    def test_empty_directions_still_valid_response(self, auth_client):
        """空 directions 仍为合法响应（前端自行处理空列表）"""
        mock_result = {"account_id": 0, "directions": []}

        with patch("app.api.generate.trigger_direction_generation.delay") as mock_delay:
            mock_task = MagicMock()
            mock_task.id = "test-empty-task"
            mock_delay.return_value = mock_task

            auth_client.post("/api/generate/directions", json={
                "account_id": 0, "idea": "测试"
            })

        with patch("app.api.generate.AsyncResult") as mock_async_result:
            mock_async_result.return_value.status = "SUCCESS"
            mock_async_result.return_value.result = mock_result
            mock_async_result.return_value.successful.return_value = True

            result_resp = auth_client.get("/api/generate/task/test-empty-task/result")
            data = result_resp.json()
            assert data["status"] == "success"
            assert data["result"]["directions"] == []
