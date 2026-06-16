"""
供应商管理 API 测试用例
"""


def test_unauthenticated_returns_403(client):
    """无 token 访问受保护端点应拒绝"""
    resp = client.get("/api/providers")
    assert resp.status_code in (401, 403)


def test_create_provider(auth_client):
    """创建供应商成功"""
    r = auth_client.post("/api/providers", json={
        "name": "测试供应商",
        "base_url": "https://api.example.com",
        "api_key": "sk-real-key-12345",
        "models": '["gpt-4"]',
    })
    assert r.status_code == 200
    data = r.json()
    assert data["name"] == "测试供应商"
    assert data["api_key"] != "sk-real-key-12345"  # 返回时掩码
    assert "***" in data["api_key"]
    assert "id" in data


def test_list_providers(auth_client):
    """列表返回供应商"""
    auth_client.post("/api/providers", json={
        "name": "供应商A",
        "base_url": "https://a.example.com",
        "api_key": "sk-a-key",
    })
    r = auth_client.get("/api/providers")
    assert r.status_code == 200
    assert len(r.json()) == 1


def test_update_provider_preserves_api_key(auth_client):
    """PUT 时不传 api_key 应保留原值"""
    r = auth_client.post("/api/providers", json={
        "name": "保留测试",
        "base_url": "https://keep.example.com",
        "api_key": "sk-should-keep-999",
    })
    pid = r.json()["id"]

    # PUT 没有传 api_key
    r2 = auth_client.put(f"/api/providers/{pid}", json={"name": "保留测试改名"})
    assert r2.status_code == 200

    # 验证 api_key 未被覆盖（掩码格式：前3字符+***+后4字符）
    r3 = auth_client.get(f"/api/providers/{pid}")
    assert r3.json()["api_key"] == "sk-***-999"


def test_update_provider_masked_key_skipped(auth_client):
    """PUT 传入掩码 key 应跳过更新，保留真实 key"""
    r = auth_client.post("/api/providers", json={
        "name": "掩码测试",
        "base_url": "https://mask.example.com",
        "api_key": "sk-real-key-88888",
    })
    pid = r.json()["id"]

    # GET 拿到掩码后的 key
    r_get = auth_client.get(f"/api/providers/{pid}")
    masked = r_get.json()["api_key"]
    assert "***" in masked

    # PUT 把掩码 key 传回去 — 不应覆盖
    r_put = auth_client.put(f"/api/providers/{pid}", json={
        "name": "掩码测试",
        "base_url": "https://mask.example.com",
        "api_key": masked,
    })
    assert r_put.status_code == 200

    # 真实 key 应保留
    r_final = auth_client.get(f"/api/providers/{pid}")
    # 数据库中的真实 key 的掩码形式应与原始一致
    assert r_final.json()["api_key"] == "sk-***8888"


def test_delete_provider(auth_client):
    """删除供应商"""
    r = auth_client.post("/api/providers", json={
        "name": "待删除",
        "base_url": "https://del.example.com",
        "api_key": "sk-del-key",
    })
    pid = r.json()["id"]
    r2 = auth_client.delete(f"/api/providers/{pid}")
    assert r2.status_code == 200
    assert auth_client.get(f"/api/providers/{pid}").status_code == 404
