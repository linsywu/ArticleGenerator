"""
标题生成 — 完整测试：API 端点 + Celery 任务 + 解析器覆盖
"""
from unittest.mock import patch, MagicMock
import pytest
from app.tasks import trigger_title_generation


# ── 辅助函数 ──

def _mock_llm_response(content: str):
    """构建 mock httpx 响应"""
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = {"content": content}
    return mock_resp


# ── API 端点测试 ──

def test_post_titles_returns_task_id(auth_client):
    """POST /generate/titles 返回 task_id"""
    acc = auth_client.post("/api/accounts", json={
        "platform": "test", "account_name": "title_test"
    }).json()

    with patch("app.api.generate.trigger_title_generation.delay") as mock_delay:
        mock_task = MagicMock()
        mock_task.id = "title-task-001"
        mock_delay.return_value = mock_task
        resp = auth_client.post("/api/generate/titles", json={
            "account_id": acc["id"],
            "idea": "AI 编程工具",
            "direction": "效率提升",
            "outline": ["工具演进", "开发者角色变化"],
        })

    assert resp.status_code == 200
    data = resp.json()
    assert data["task_id"] == "title-task-001"
    assert data["status"] == "pending"


def test_post_titles_account_not_found(auth_client):
    """不存在的账号返回 404"""
    resp = auth_client.post("/api/generate/titles", json={
        "account_id": 99999,
        "idea": "测试",
        "direction": "方向",
        "outline": ["要点1"],
    })
    assert resp.status_code == 404


def test_post_titles_empty_idea_rejected(auth_client):
    """空白 idea 返回 400"""
    acc = auth_client.post("/api/accounts", json={
        "platform": "test", "account_name": "title_empty"
    }).json()

    resp = auth_client.post("/api/generate/titles", json={
        "account_id": acc["id"],
        "idea": "  ",
        "direction": "方向",
        "outline": ["要点1"],
    })
    assert resp.status_code == 400


# ── Celery 任务：解析器覆盖 ──

def test_title_task_json_array():
    """LLM 直接返回 JSON 字符串数组"""
    with patch("app.tasks.httpx.Client") as mock_client:
        mock_instance = MagicMock()
        mock_client.return_value.__enter__.return_value = mock_instance
        mock_instance.post.return_value = _mock_llm_response(
            '["AI 编程工具：程序员的终结者还是加速器？", "当代码不再需要手写，我们该如何定位自己？", "技术焦虑时代的生存指南"]'
        )
        result = trigger_title_generation(
            account_id=1, idea="AI 编程", direction="效率提升", outline=["要点1", "要点2"]
        )

    assert len(result["titles"]) == 3
    assert "终结者" in result["titles"][0]


def test_title_task_markdown_code_block():
    """LLM 返回 markdown 代码块包裹的 JSON"""
    with patch("app.tasks.httpx.Client") as mock_client:
        mock_instance = MagicMock()
        mock_client.return_value.__enter__.return_value = mock_instance
        mock_instance.post.return_value = _mock_llm_response(
            '```json\n["标题方案A", "标题方案B"]\n```'
        )
        result = trigger_title_generation(
            account_id=1, idea="测试", direction="方向", outline=["要点1"]
        )

    assert len(result["titles"]) == 2


def test_title_task_empty_fallback_to_idea():
    """LLM 返回无法解析的内容 → 回退到 idea 作为唯一标题"""
    with patch("app.tasks.httpx.Client") as mock_client:
        mock_instance = MagicMock()
        mock_client.return_value.__enter__.return_value = mock_instance
        # 返回非 JSON、非代码块的内容
        mock_instance.post.return_value = _mock_llm_response("这是普通的文本回复，不是JSON格式")

        result = trigger_title_generation(
            account_id=1, idea="AI 编程工具的未来趋势", direction="方向", outline=["要点1"]
        )

    assert len(result["titles"]) == 1
    # 回退标题是 idea 的前 50 字符
    assert "AI 编程" in result["titles"][0]


def test_title_task_filter_non_string_items():
    """JSON 数组中混入非字符串项 → 过滤掉"""
    with patch("app.tasks.httpx.Client") as mock_client:
        mock_instance = MagicMock()
        mock_client.return_value.__enter__.return_value = mock_instance
        mock_instance.post.return_value = _mock_llm_response(
            '["有效标题1", 123, "有效标题2", null]'
        )
        result = trigger_title_generation(
            account_id=1, idea="测试", direction="方向", outline=["要点1"]
        )

    # 只保留字符串类型
    assert len(result["titles"]) == 2
    assert "有效标题1" in result["titles"]
    assert "有效标题2" in result["titles"]


def test_title_task_user_prompt_included():
    """验证 user_prompt、idea、direction、outline 被传入 LLM 请求"""
    captured_vars = None

    with patch("app.tasks.httpx.Client") as mock_client:
        mock_instance = MagicMock()
        mock_client.return_value.__enter__.return_value = mock_instance

        def capture_post(*args, **kwargs):
            nonlocal captured_vars
            captured_vars = kwargs.get("json", {}).get("variables", {})
            return _mock_llm_response('["标题1", "标题2"]')
        mock_instance.post.side_effect = capture_post

        trigger_title_generation(
            account_id=1, idea="AI 安全", direction="技术伦理", outline=["数据隐私", "算法公平"]
        )

    assert captured_vars is not None, "LLM 请求未被捕获"
    assert "user_prompt" in captured_vars, f"user_prompt 缺失，实际变量: {list(captured_vars.keys())}"
    assert "AI 安全" in captured_vars["user_prompt"]
    assert "技术伦理" in captured_vars["user_prompt"]
    assert "数据隐私" in captured_vars["user_prompt"], "大纲内容应在 user_prompt 中"


def test_title_task_empty_content_raises():
    """LLM 返回空内容抛出 ValueError"""
    with patch("app.tasks.httpx.Client") as mock_client:
        mock_instance = MagicMock()
        mock_client.return_value.__enter__.return_value = mock_instance
        mock_instance.post.return_value = _mock_llm_response("")

        with pytest.raises(ValueError, match="标题生成返回内容为空"):
            trigger_title_generation(
                account_id=1, idea="我的想法", direction="方向", outline=["要点1"]
            )
