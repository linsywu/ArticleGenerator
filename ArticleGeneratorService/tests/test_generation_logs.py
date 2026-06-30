"""
测试 generation_logs：完整提示词记录 + task_id 关联 + 子任务链查询
"""
import json
import pytest
from app.models import GenerationLog, GenerationTask, Account, Provider, ScenarioConfig


class TestGenerationLogCreate:
    """POST /api/generation-logs — 创建日志（含完整提示词）"""

    def test_create_log_with_full_prompt(self, auth_client, db_session):
        p = Provider(name="test", base_url="http://x", api_key="k", enabled=True)
        db_session.add(p)
        db_session.commit()

        payload = {
            "scenario": "generate",
            "task_id": "celery-task-abc-123",
            "provider_id": p.id,
            "model": "deepseek-chat",
            "system_prompt": "你是一个专业的内容创作者。\n## 文章主题\n深度阅读的价值",
            "user_prompt": "请开始创作。",
            "prompt_tokens": 500,
            "completion_tokens": 1200,
            "latency_ms": 8500,
            "status": "success",
        }
        resp = auth_client.post("/api/generation-logs", json=payload)
        assert resp.status_code == 200

        log = db_session.query(GenerationLog).order_by(GenerationLog.id.desc()).first()
        assert log is not None
        assert log.scenario == "generate"
        assert log.task_id == "celery-task-abc-123"
        assert log.system_prompt == payload["system_prompt"]
        assert log.user_prompt == "请开始创作。"
        assert log.prompt_tokens == 500
        assert log.latency_ms == 8500

    def test_create_log_without_prompt(self, auth_client, db_session):
        """兼容旧调用：不带 task_id 和 prompt"""
        p = Provider(name="old", base_url="http://x", api_key="k", enabled=True)
        db_session.add(p)
        db_session.commit()

        resp = auth_client.post("/api/generation-logs", json={
            "scenario": "refine",
            "provider_id": p.id,
            "model": "gpt-4",
            "prompt_tokens": 100,
            "completion_tokens": 200,
            "latency_ms": 3000,
            "status": "failed",
            "error_message": "timeout",
        })
        assert resp.status_code == 200

        log = db_session.query(GenerationLog).filter(GenerationLog.scenario == "refine").first()
        assert log is not None
        assert log.task_id is None
        assert log.system_prompt is None
        assert log.status == "failed"


class TestGenerationLogList:
    """GET /api/generation-logs — 按 task_id / scenario 筛选"""

    def _seed_logs_via_api(self, auth_client):
        """通过 API 写入测试数据"""
        entries = [
            {"scenario": "generate", "task_id": "task-1", "status": "success", "prompt_tokens": 100, "completion_tokens": 200, "latency_ms": 1000},
            {"scenario": "humanize", "task_id": "task-2", "status": "success", "prompt_tokens": 50, "completion_tokens": 150, "latency_ms": 500},
            {"scenario": "quality_review", "task_id": "task-3", "status": "failed", "error_message": "err", "prompt_tokens": 10, "completion_tokens": 5, "latency_ms": 100},
            {"scenario": "compliance_review", "task_id": "task-3", "status": "success", "prompt_tokens": 8, "completion_tokens": 3, "latency_ms": 80},
        ]
        for e in entries:
            resp = auth_client.post("/api/generation-logs", json=e)
            assert resp.status_code == 200

    def test_list_all(self, auth_client):
        self._seed_logs_via_api(auth_client)
        resp = auth_client.get("/api/generation-logs")
        assert resp.status_code == 200
        assert resp.json()["total"] == 4

    def test_filter_by_task_id(self, auth_client):
        self._seed_logs_via_api(auth_client)
        resp = auth_client.get("/api/generation-logs?task_id=task-3")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert len(data) == 2
        scenarios = {d["scenario"] for d in data}
        assert scenarios == {"quality_review", "compliance_review"}

    def test_filter_by_scenario(self, auth_client):
        self._seed_logs_via_api(auth_client)
        resp = auth_client.get("/api/generation-logs?scenario=generate")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert len(data) == 1
        assert data[0]["scenario"] == "generate"

    def test_filter_by_task_id_not_found(self, auth_client):
        resp = auth_client.get("/api/generation-logs?task_id=nonexistent")
        assert resp.status_code == 200
        assert resp.json()["total"] == 0


class TestGenerationLogsByTask:
    """GET /api/generation-logs/by-generation-task/{id} — 含子任务链"""

    def _seed_generation_task(self, db_session, task_id="root-task", sub_task_ids=None):
        gt = GenerationTask(
            task_id=task_id,
            account_id=1,
            status="success",
            sub_task_ids=json.dumps(sub_task_ids) if sub_task_ids else None,
        )
        db_session.add(gt)
        db_session.commit()
        return gt

    def _seed_logs_via_api(self, auth_client, task_ids):
        for tid in task_ids:
            resp = auth_client.post("/api/generation-logs", json={
                "scenario": "generate" if tid == "root-task" else "humanize",
                "task_id": tid,
                "status": "success",
                "system_prompt": f"prompt for {tid}",
                "user_prompt": "请开始创作。",
                "prompt_tokens": 100,
                "completion_tokens": 200,
                "latency_ms": 1000,
            })
            assert resp.status_code == 200

    def test_logs_with_sub_tasks(self, auth_client, db_session):
        gt = self._seed_generation_task(
            db_session,
            task_id="root-task",
            sub_task_ids=["sub-humanize", "sub-quality", "sub-compliance"],
        )
        self._seed_logs_via_api(auth_client, ["root-task", "sub-humanize", "sub-quality", "sub-compliance"])

        resp = auth_client.get(f"/api/generation-logs/by-generation-task/{gt.id}")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert len(data) == 4
        task_ids = {d["task_id"] for d in data}
        assert "root-task" in task_ids
        assert "sub-humanize" in task_ids

    def test_logs_without_sub_tasks(self, auth_client, db_session):
        gt = self._seed_generation_task(db_session, task_id="solo-task")
        self._seed_logs_via_api(auth_client, ["solo-task"])

        resp = auth_client.get(f"/api/generation-logs/by-generation-task/{gt.id}")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert len(data) == 1
        assert data[0]["task_id"] == "solo-task"

    def test_not_found_returns_empty(self, auth_client):
        resp = auth_client.get("/api/generation-logs/by-generation-task/99999")
        assert resp.status_code == 200
        assert resp.json()["data"] == []


class TestGenerationTaskSubTaskIds:
    """GenerationTask.sub_task_ids 字段"""

    def test_sub_task_ids_default_null(self, db_session):
        gt = GenerationTask(task_id="no-subs", account_id=1, status="pending")
        db_session.add(gt)
        db_session.commit()
        assert gt.sub_task_ids is None

    def test_sub_task_ids_store(self, db_session):
        sub_ids = ["task-a", "task-b"]
        gt = GenerationTask(
            task_id="with-subs", account_id=1, status="success",
            sub_task_ids=json.dumps(sub_ids),
        )
        db_session.add(gt)
        db_session.commit()
        assert json.loads(gt.sub_task_ids) == sub_ids
