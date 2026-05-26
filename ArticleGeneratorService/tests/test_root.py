"""
根路由测试
"""
def test_root(client):
    """根路径返回 API 信息"""
    r = client.get("/")
    assert r.status_code == 200
    assert "ArticleGenerator" in r.json()["message"]
