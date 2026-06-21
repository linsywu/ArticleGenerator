"""Test distill status endpoint"""
from app.models import Account


def test_distill_status_idle(auth_client, db_session):
    """未蒸馏的账号返回 idle"""
    account = Account(platform="test", account_name="test_acc")
    db_session.add(account)
    db_session.commit()
    acc_id = account.id

    resp = auth_client.get(f"/api/accounts/{acc_id}/distill/status")
    assert resp.status_code == 200
    assert resp.json()["status"] == "idle"


def test_distill_status_running(auth_client, db_session):
    """蒸馏中的账号返回 running + progress"""
    account = Account(
        platform="test",
        account_name="test_acc",
        style_profile_status="running",
        style_profile_structured='{"_progress": {"completed": 3, "total": 7, "current_dimension": "句式特征"}, "thinking_pattern": "test"}'
    )
    db_session.add(account)
    db_session.commit()
    acc_id = account.id

    resp = auth_client.get(f"/api/accounts/{acc_id}/distill/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "running"
    assert data["progress"]["completed"] == 3
    assert data["progress"]["current_dimension"] == "句式特征"


def test_distill_status_completed(auth_client, db_session):
    """蒸馏完成的账号返回 completed"""
    account = Account(
        platform="test",
        account_name="test_acc",
        style_profile_status="ready",
        style_profile_version=2,
    )
    db_session.add(account)
    db_session.commit()
    acc_id = account.id

    resp = auth_client.get(f"/api/accounts/{acc_id}/distill/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "completed"
    assert data["style_profile_version"] == 2


def test_distill_status_failed(auth_client, db_session):
    """蒸馏失败的账号返回 failed + error"""
    account = Account(
        platform="test",
        account_name="test_acc",
        style_profile_status="failed",
        style_profile="LLM 返回格式异常"
    )
    db_session.add(account)
    db_session.commit()
    acc_id = account.id

    resp = auth_client.get(f"/api/accounts/{acc_id}/distill/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "failed"
    assert "error" in data


def test_distill_status_404(auth_client):
    """不存在的账号返回 404"""
    resp = auth_client.get("/api/accounts/99999/distill/status")
    assert resp.status_code == 404
