"""Test distill status endpoint — status enum (extracting/synthesizing)"""


def test_distill_status_idle(auth_client, db_session):
    """未蒸馏的账号返回 idle"""
    from app.models import Account
    account = Account(platform="test", account_name="test_acc")
    db_session.add(account)
    db_session.commit()
    acc_id = account.id

    resp = auth_client.get(f"/api/accounts/{acc_id}/distill/status")
    assert resp.status_code == 200
    assert resp.json()["status"] == "idle"


def test_distill_status_extracting(auth_client, db_session):
    """Stage 1 运行中返回 running + stage 1"""
    from app.models import Account
    account = Account(
        platform="test", account_name="test_acc",
        style_profile_status="extracting",
    )
    db_session.add(account)
    db_session.commit()
    acc_id = account.id

    resp = auth_client.get(f"/api/accounts/{acc_id}/distill/status")
    data = resp.json()
    assert data["status"] == "running"
    assert data["stage"] == 1
    assert "提取" in data["stage_name"]


def test_distill_status_synthesizing(auth_client, db_session):
    """Stage 2 运行中返回 running + stage 2"""
    from app.models import Account
    account = Account(
        platform="test", account_name="test_acc",
        style_profile_status="synthesizing",
    )
    db_session.add(account)
    db_session.commit()
    acc_id = account.id

    resp = auth_client.get(f"/api/accounts/{acc_id}/distill/status")
    data = resp.json()
    assert data["status"] == "running"
    assert data["stage"] == 2
    assert "凝练" in data["stage_name"]


def test_distill_status_completed(auth_client, db_session):
    """蒸馏完成返回 completed + version"""
    from app.models import Account
    account = Account(
        platform="test", account_name="test_acc",
        style_profile_status="ready", style_profile_version=2,
    )
    db_session.add(account)
    db_session.commit()
    acc_id = account.id

    resp = auth_client.get(f"/api/accounts/{acc_id}/distill/status")
    data = resp.json()
    assert data["status"] == "completed"
    assert data["style_profile_version"] == 2


def test_distill_status_failed(auth_client, db_session):
    """蒸馏失败返回 failed + error"""
    from app.models import Account
    account = Account(
        platform="test", account_name="test_acc",
        style_profile_status="failed", style_profile="LLM 超时",
    )
    db_session.add(account)
    db_session.commit()
    acc_id = account.id

    resp = auth_client.get(f"/api/accounts/{acc_id}/distill/status")
    data = resp.json()
    assert data["status"] == "failed"
    assert "error" in data


def test_distill_status_404(auth_client):
    """不存在的账号返回 404"""
    resp = auth_client.get("/api/accounts/99999/distill/status")
    assert resp.status_code == 404
