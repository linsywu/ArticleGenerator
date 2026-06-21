"""Test word_count fields CRUD"""
from app.models import Account


def test_update_word_count(auth_client, db_session):
    """更新账号字数配置"""
    account = Account(platform="test", account_name="wc_test")
    db_session.add(account)
    db_session.commit()
    acc_id = account.id

    resp = auth_client.put(f"/api/accounts/{acc_id}", json={
        "word_count_options": '["500","1000"]',
        "word_count": 500,
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["word_count"] == 500
