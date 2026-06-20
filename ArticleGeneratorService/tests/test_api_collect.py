"""
采集管线 API 回归测试
"""
import os
os.environ["CELERY_TASK_ALWAYS_EAGER"] = "True"

import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

from app.main import app
from app.database import SessionLocal
from app.models import (
    MpCredential, CollectTask, MpAccount, Track, MpMaterial, CollectLog,
)
from app.config import settings
from app.auth import get_password_hash
from app.models import User


def _create_seed_user():
    db = SessionLocal()
    try:
        existing = db.query(User).filter(User.username == settings.seed_username).first()
        if not existing:
            user = User(
                username=settings.seed_username,
                password_hash=get_password_hash(settings.seed_password),
            )
            db.add(user)
            db.commit()
    finally:
        db.close()

    client = TestClient(app)
    r = client.post("/api/auth/login", json={
        "username": settings.seed_username,
        "password": settings.seed_password,
    })
    return r.json()["access_token"]


@pytest.fixture
def auth_client():
    token = _create_seed_user()
    client = TestClient(app)
    client.headers.update({"Authorization": f"Bearer {token}"})
    return client


@pytest.fixture(autouse=True)
def _clean_collect_tables():
    db = SessionLocal()
    try:
        for t in [CollectLog, MpMaterial, CollectTask, MpCredential, MpAccount, Track]:
            db.query(t).delete()
        db.commit()
    finally:
        db.close()


@pytest.fixture
def credential():
    db = SessionLocal()
    c = MpCredential(name="test-cred", token="tok-abc12345678", cookie="cookie-abcdefghijklmnopqrstuvwxyz")
    db.add(c)
    db.commit()
    db.refresh(c)
    db.close()
    return c


@pytest.fixture
def task(credential):
    db = SessionLocal()
    t = CollectTask(name="test-task", credential_id=credential.id, collect_mode="incremental", schedule_type="manual")
    db.add(t)
    db.commit()
    db.refresh(t)
    db.close()
    return t


@pytest.fixture
def account():
    db = SessionLocal()
    a = MpAccount(name="test-mp", fakeid="fake123", track_ids='[]')
    db.add(a)
    db.commit()
    db.refresh(a)
    db.close()
    return a


# ── Execute Tests ────────────────────────────────────────

class TestCollectTaskExecute:

    def test_execute_dispatches_without_500(self, auth_client, task):
        """执行按钮不再返回 500（mock 整个 shared_task 避免 kombu broker 连接）"""
        mock_result = MagicMock()
        mock_result.id = "mock-task-id"

        with patch("app.tasks.celery_app.send_task") as mock_send:
            mock_send.return_value = mock_result
            r = auth_client.post(f"/api/collect-tasks/{task.id}/execute")

        assert r.status_code == 200, f"Got {r.status_code}: {r.text}"
        data = r.json()
        assert data["celery_task_id"] == "mock-task-id"
        assert data["message"] == "采集任务已提交"

    def test_execute_nonexistent_task_404(self, auth_client):
        r = auth_client.post("/api/collect-tasks/99999/execute")
        assert r.status_code == 404

    def test_execute_already_running_400(self, auth_client, task):
        db = SessionLocal()
        db.query(CollectTask).filter(CollectTask.id == task.id).update({"status": "running"})
        db.commit()
        db.close()
        with patch("app.tasks.celery_app.send_task"):
            r = auth_client.post(f"/api/collect-tasks/{task.id}/execute")
        assert r.status_code == 400


# ── Credential Check Tests ───────────────────────────────

class TestCredentialCheck:

    def test_check_endpoint_no_crash(self, auth_client, credential):
        """检测端点应返回 200，含 status + healthy 字段，不崩溃"""
        r = auth_client.post(f"/api/credentials/{credential.id}/check")
        assert r.status_code == 200
        data = r.json()
        assert "status" in data
        assert "healthy" in data
        assert isinstance(data["healthy"], bool)

    def test_check_nonexistent_404(self, auth_client):
        r = auth_client.post("/api/credentials/99999/check")
        assert r.status_code == 404


# ── Materials Schema Tests ───────────────────────────────

class TestMaterialsSchema:

    def _seed(self, account):
        db = SessionLocal()
        m = MpMaterial(
            account_id=account.id, title="测试文章", author="作者",
            original_url="https://mp.weixin.qq.com/s/test",
            raw_html="<p>hello</p>", word_count=500, is_original=1,
            content_hash="abc",
        )
        db.add(m)
        db.commit()
        db.refresh(m)
        db.close()
        return m

    def test_list_has_data_and_total(self, auth_client, account):
        self._seed(account)
        r = auth_client.get("/api/materials")
        assert r.status_code == 200
        body = r.json()
        assert "data" in body and "total" in body and body["total"] >= 1
        item = body["data"][0]
        assert item["title"] == "测试文章"
        assert "account" in item

    def test_detail_has_raw_html_and_account(self, auth_client, account):
        m = self._seed(account)
        r = auth_client.get(f"/api/materials/{m.id}")
        assert r.status_code == 200
        body = r.json()
        assert "raw_html" in body
        assert "account" in body
        assert body["account"]["name"] == "test-mp"

    def test_parse_generates_markdown(self, auth_client, account):
        m = self._seed(account)
        r = auth_client.post(f"/api/materials/{m.id}/parse")
        assert r.status_code == 200
        body = r.json()
        assert "hello" in body["content_markdown"]
        assert body["cached"] is False

    def test_parse_cached_on_rerun(self, auth_client, account):
        m = self._seed(account)
        auth_client.post(f"/api/materials/{m.id}/parse")
        r = auth_client.post(f"/api/materials/{m.id}/parse")
        assert r.json()["cached"] is True


# ── Collect Logs Schema Tests ────────────────────────────

class TestCollectLogsSchema:

    def test_list_has_data_and_total(self, auth_client, task):
        db = SessionLocal()
        db.add(CollectLog(task_id=task.id, account_id=1, total_count=10, success_count=8, fail_count=2))
        db.commit()
        db.close()
        r = auth_client.get("/api/collect-logs")
        assert r.status_code == 200
        body = r.json()
        assert "data" in body and "total" in body
        item = body["data"][0]
        assert item["task_name"] is not None
        assert item["total_count"] == 10
