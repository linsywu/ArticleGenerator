"""
大纲生成 — 完整测试：API 端点 + Celery 任务 + 解析器覆盖
"""
from unittest.mock import patch, MagicMock
import pytest
from app.tasks import trigger_outline_generation


# ── 辅助函数 ──

def _mock_llm_response(content: str):
    """构建 mock httpx 响应"""
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = {"content": content}
    return mock_resp


# ── API 端点测试 ──

def test_post_outline_returns_task_id(auth_client):
    """POST /generate/outline 返回 task_id"""
    acc = auth_client.post("/api/accounts", json={
        "platform": "test", "account_name": "outline_test"
    }).json()

    with patch("app.api.generate.trigger_outline_generation.delay") as mock_delay:
        mock_task = MagicMock()
        mock_task.id = "outline-task-001"
        mock_delay.return_value = mock_task
        resp = auth_client.post("/api/generate/outline", json={
            "account_id": acc["id"],
            "idea": "远程办公趋势",
            "direction": "工作效率与生活平衡",
        })

    assert resp.status_code == 200
    data = resp.json()
    assert data["task_id"] == "outline-task-001"
    assert data["status"] == "pending"


def test_post_outline_account_not_found(auth_client):
    """不存在的账号返回 404"""
    resp = auth_client.post("/api/generate/outline", json={
        "account_id": 99999,
        "idea": "测试",
        "direction": "测试方向",
    })
    assert resp.status_code == 404
    assert "账号不存在" in resp.json()["detail"]


def test_post_outline_empty_idea_rejected(auth_client):
    """空白 idea 返回 400"""
    acc = auth_client.post("/api/accounts", json={
        "platform": "test", "account_name": "outline_empty"
    }).json()

    resp = auth_client.post("/api/generate/outline", json={
        "account_id": acc["id"],
        "idea": "  ",
        "direction": "有效的方向",
    })
    assert resp.status_code == 400
    assert "不能为空" in resp.json()["detail"]


def test_post_outline_empty_direction_rejected(auth_client):
    """空白 direction 返回 400"""
    acc = auth_client.post("/api/accounts", json={
        "platform": "test", "account_name": "outline_empty_dir"
    }).json()

    resp = auth_client.post("/api/generate/outline", json={
        "account_id": acc["id"],
        "idea": "有效的想法",
        "direction": "  ",
    })
    assert resp.status_code == 400
    assert "不能为空" in resp.json()["detail"]


# ── Celery 任务：解析器覆盖 ──

def test_outline_task_json_array():
    """LLM 返回 JSON 字符串数组"""
    with patch("app.tasks.httpx.Client") as mock_client:
        mock_instance = MagicMock()
        mock_client.return_value.__enter__.return_value = mock_instance
        mock_instance.post.return_value = _mock_llm_response(
            '["引言：远程办公的兴起", "核心论点：效率悖论", "案例研究：微软与谷歌", "结论：混合办公是未来"]'
        )
        result = trigger_outline_generation(account_id=1, idea="远程办公", direction="效率")

    assert len(result["outline"]) == 4
    assert result["outline"][0] == "引言：远程办公的兴起"


def test_outline_task_json_object():
    """LLM 返回 {"outline": [...]} 包装对象"""
    with patch("app.tasks.httpx.Client") as mock_client:
        mock_instance = MagicMock()
        mock_client.return_value.__enter__.return_value = mock_instance
        mock_instance.post.return_value = _mock_llm_response(
            '{"outline": ["要点1", "要点2", "要点3"]}'
        )
        result = trigger_outline_generation(account_id=1, idea="测试", direction="测试")

    assert len(result["outline"]) == 3
    assert result["outline"] == ["要点1", "要点2", "要点3"]


def test_outline_task_markdown_code_block():
    """LLM 返回 markdown 代码块包裹的 JSON"""
    with patch("app.tasks.httpx.Client") as mock_client:
        mock_instance = MagicMock()
        mock_client.return_value.__enter__.return_value = mock_instance
        mock_instance.post.return_value = _mock_llm_response(
            '这是大纲：\n```json\n["第一步：了解背景", "第二步：分析原因"]\n```\n共2个要点'
        )
        result = trigger_outline_generation(account_id=1, idea="测试", direction="测试")

    assert len(result["outline"]) == 2
    assert "了解背景" in result["outline"][0]


def test_outline_task_user_prompt_included():
    """验证 user_prompt 被传入 LLM 请求变量中"""
    captured_vars = None

    with patch("app.tasks.httpx.Client") as mock_client:
        mock_instance = MagicMock()
        mock_client.return_value.__enter__.return_value = mock_instance

        def capture_post(*args, **kwargs):
            nonlocal captured_vars
            captured_vars = kwargs.get("json", {}).get("variables", {})
            return _mock_llm_response('["要点1", "要点2"]')
        mock_instance.post.side_effect = capture_post

        trigger_outline_generation(account_id=1, idea="AI 安全性", direction="技术伦理")

    assert captured_vars is not None, "LLM 请求未被捕获"
    assert "user_prompt" in captured_vars, f"user_prompt 缺失，实际变量: {list(captured_vars.keys())}"
    assert "AI 安全性" in captured_vars["user_prompt"]
    assert "技术伦理" in captured_vars["user_prompt"]


def test_outline_task_empty_content_raises():
    """LLM 返回空内容抛出 ValueError"""
    with patch("app.tasks.httpx.Client") as mock_client:
        mock_instance = MagicMock()
        mock_client.return_value.__enter__.return_value = mock_instance
        mock_instance.post.return_value = _mock_llm_response("")

        with pytest.raises(ValueError, match="大纲生成返回内容为空"):
            trigger_outline_generation(account_id=1, idea="测试", direction="测试")
