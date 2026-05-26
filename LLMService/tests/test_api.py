"""
LLM 服务 API 测试用例
"""
import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


def test_root(client):
    """根路径返回服务信息"""
    r = client.get("/")
    assert r.status_code == 200
    assert "mock_mode" in r.json()


def test_generate_mock(client):
    """模拟模式下生成文章"""
    r = client.post("/generate", json={"hotspot_title": "测试热点", "account_id": 1})
    assert r.status_code == 200
    data = r.json()
    assert "content" in data
    assert "测试热点" in data["content"]
    assert "模拟生成" in data["content"]


def test_refine_mock(client):
    """模拟模式下微调文章"""
    r = client.post("/refine", json={
        "article_id": 1,
        "content": "原文内容",
        "keywords": "增加幽默感",
    })
    assert r.status_code == 200
    data = r.json()
    assert "content" in data
    assert "原文内容" in data["content"]
    assert "增加幽默感" in data["content"]
