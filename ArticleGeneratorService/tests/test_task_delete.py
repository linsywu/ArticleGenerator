"""测试 DELETE /api/generate/tasks/{task_id}"""
import json
from app.models import GenerationTask, GenerationLog


class TestDeleteTask:
    def test_delete_success_task(self, auth_client, db_session):
        """删除已成功的任务"""
        gt = GenerationTask(task_id="del-test-1", account_id=1, status="success")
        db_session.add(gt)
        db_session.add(GenerationLog(scenario="generate", task_id="del-test-1", status="success", prompt_tokens=10, completion_tokens=20, latency_ms=100))
        db_session.commit()

        resp = auth_client.delete(f"/api/generate/tasks/del-test-1")
        assert resp.status_code == 200
        assert resp.json()["message"] == "已删除"

        assert db_session.query(GenerationTask).filter(GenerationTask.task_id == "del-test-1").first() is None
        assert db_session.query(GenerationLog).filter(GenerationLog.task_id == "del-test-1").first() is None

    def test_delete_running_task_fails(self, auth_client, db_session):
        """运行中的任务不可删除"""
        gt = GenerationTask(task_id="del-test-2", account_id=1, status="running")
        db_session.add(gt)
        db_session.commit()

        resp = auth_client.delete(f"/api/generate/tasks/del-test-2")
        assert resp.status_code == 400
        assert "请先取消" in resp.json()["detail"]

    def test_delete_not_found(self, auth_client):
        resp = auth_client.delete("/api/generate/tasks/nonexistent")
        assert resp.status_code == 404
