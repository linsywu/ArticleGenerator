"""
账号管理 API 测试用例
"""
import pytest


def test_unauthenticated_returns_403(client):
    """无 token 访问受保护端点应拒绝"""
    resp = client.get("/api/accounts")
    assert resp.status_code in (401, 403)


def test_list_accounts_empty(auth_client):
    """空列表时返回 []"""
    r = auth_client.get("/api/accounts")
    assert r.status_code == 200
    assert r.json() == []


def test_create_account(auth_client):
    """创建账号成功"""
    r = auth_client.post("/api/accounts", json={
        "platform": "公众号",
        "account_name": "测试账号",
        "lora_path": "/path/to/lora",
    })
    assert r.status_code == 200
    data = r.json()
    assert data["platform"] == "公众号"
    assert data["account_name"] == "测试账号"
    assert data["lora_path"] == "/path/to/lora"
    assert "id" in data
    assert "created_at" in data


def test_get_account(auth_client):
    """获取账号详情"""
    create_r = auth_client.post("/api/accounts", json={"platform": "小红书", "account_name": "小红"})
    aid = create_r.json()["id"]
    r = auth_client.get(f"/api/accounts/{aid}")
    assert r.status_code == 200
    assert r.json()["account_name"] == "小红"


def test_get_account_not_found(auth_client):
    """获取不存在的账号返回 404"""
    r = auth_client.get("/api/accounts/99999")
    assert r.status_code == 404


def test_update_account(auth_client):
    """更新账号"""
    create_r = auth_client.post("/api/accounts", json={"platform": "A", "account_name": "B"})
    aid = create_r.json()["id"]
    r = auth_client.put(f"/api/accounts/{aid}", json={"account_name": "B2"})
    assert r.status_code == 200
    assert r.json()["account_name"] == "B2"


def test_delete_account(auth_client):
    """删除账号"""
    create_r = auth_client.post("/api/accounts", json={"platform": "X", "account_name": "Y"})
    aid = create_r.json()["id"]
    r = auth_client.delete(f"/api/accounts/{aid}")
    assert r.status_code == 200
    assert auth_client.get(f"/api/accounts/{aid}").status_code == 404
