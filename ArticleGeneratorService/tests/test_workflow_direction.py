"""
写作方向生成 — 完整测试：API 端点 + Celery 任务 + 解析器覆盖
"""
from unittest.mock import patch, MagicMock, PropertyMock
import pytest
from app.tasks import trigger_direction_generation


# ── 辅助函数 ──

def _mock_llm_response(content: str):
    """构建 mock httpx 响应（/chat 端点）"""
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = {"content": content}
    return mock_resp


# ── API 端点测试 ──

def test_post_directions_returns_task_id(auth_client):
    """POST /generate/directions 返回 task_id 和 pending 状态"""
    acc = auth_client.post("/api/accounts", json={
        "platform": "test", "account_name": "dir_test_1"
    }).json()

    with patch("app.api.generate.trigger_direction_generation.delay") as mock_delay:
        mock_task = MagicMock()
        mock_task.id = "dir-task-001"
        mock_delay.return_value = mock_task
        resp = auth_client.post("/api/generate/directions", json={
            "account_id": acc["id"], "idea": "AI 对就业市场的影响"
        })

    assert resp.status_code == 200
    data = resp.json()
    assert data["task_id"] == "dir-task-001"
    assert data["status"] == "pending"
    assert "方向生成" in data["message"]


def test_post_directions_empty_idea_rejected(auth_client):
    """空白 idea 返回 400 错误"""
    acc = auth_client.post("/api/accounts", json={
        "platform": "test", "account_name": "dir_empty_idea"
    }).json()

    # 纯空格
    resp = auth_client.post("/api/generate/directions", json={
        "account_id": acc["id"], "idea": "   "
    })
    assert resp.status_code == 400
    assert "不能为空" in resp.json()["detail"]


def test_post_directions_account_id_zero_accepted(auth_client):
    """素材中心路径 account_id=0 正常接受"""
    with patch("app.api.generate.trigger_direction_generation.delay") as mock_delay:
        mock_task = MagicMock()
        mock_task.id = "dir-task-zero"
        mock_delay.return_value = mock_task
        resp = auth_client.post("/api/generate/directions", json={
            "account_id": 0, "idea": "测试想法"
        })
    assert resp.status_code == 200


# ── Celery 任务：解析器覆盖 ──

def test_direction_task_json_array_format():
    """LLM 直接返回 JSON 数组 [{id, title}]"""
    with patch("app.tasks.httpx.Client") as mock_client:
        mock_instance = MagicMock()
        mock_client.return_value.__enter__.return_value = mock_instance
        mock_instance.post.return_value = _mock_llm_response(
            '[{"id": "A", "title": "情感切入"}, {"id": "B", "title": "数据切入"}]'
        )
        result = trigger_direction_generation(account_id=1, idea="测试")

    assert len(result["directions"]) == 2
    assert result["directions"][0]["id"] == "A"
    assert result["directions"][1]["title"] == "数据切入"


def test_direction_task_json_object_format():
    """LLM 返回 {"directions": [...]} 包装对象"""
    with patch("app.tasks.httpx.Client") as mock_client:
        mock_instance = MagicMock()
        mock_client.return_value.__enter__.return_value = mock_instance
        mock_instance.post.return_value = _mock_llm_response(
            '{"directions": [{"id": "1", "title": "技术视角"}, {"id": "2", "title": "人文视角"}]}'
        )
        result = trigger_direction_generation(account_id=1, idea="测试")

    assert len(result["directions"]) == 2
    assert result["directions"][0]["id"] == "1"


def test_direction_task_markdown_code_block():
    """LLM 返回 markdown 代码块包裹的 JSON"""
    with patch("app.tasks.httpx.Client") as mock_client:
        mock_instance = MagicMock()
        mock_client.return_value.__enter__.return_value = mock_instance
        mock_instance.post.return_value = _mock_llm_response(
            '```json\n[{"id": "A", "title": "角度一"}]\n```'
        )
        result = trigger_direction_generation(account_id=1, idea="测试")

    assert len(result["directions"]) == 1
    assert result["directions"][0]["title"] == "角度一"


def test_direction_task_numbered_list_fallback():
    """编号列表回退解析 1. title / 2) title"""
    with patch("app.tasks.httpx.Client") as mock_client:
        mock_instance = MagicMock()
        mock_client.return_value.__enter__.return_value = mock_instance
        mock_instance.post.return_value = _mock_llm_response(
            "1. AI 将重塑教育行业\n2) 远程办公的利与弊\n3. 技术焦虑与心理健康"
        )
        result = trigger_direction_generation(account_id=1, idea="测试")

    assert len(result["directions"]) == 3
    assert result["directions"][0]["id"] == "A"
    assert result["directions"][0]["title"] == "AI 将重塑教育行业"
    assert result["directions"][2]["title"] == "技术焦虑与心理健康"


def test_direction_task_chinese_numbered_fallback():
    """中文编号「方向一：title」「角度1：title」"""
    with patch("app.tasks.httpx.Client") as mock_client:
        mock_instance = MagicMock()
        mock_client.return_value.__enter__.return_value = mock_instance
        mock_instance.post.return_value = _mock_llm_response(
            "方向一：技术变革中的机遇\n角度2：个人成长的新路径"
        )
        result = trigger_direction_generation(account_id=1, idea="测试")

    assert len(result["directions"]) == 2
    assert "技术变革" in result["directions"][0]["title"]
    assert "个人成长" in result["directions"][1]["title"]


def test_direction_task_letter_prefix_fallback():
    """字母前缀 A. title / B) title / **C. title**"""
    with patch("app.tasks.httpx.Client") as mock_client:
        mock_instance = MagicMock()
        mock_client.return_value.__enter__.return_value = mock_instance
        mock_instance.post.return_value = _mock_llm_response(
            "**A. 社会结构变迁**\nB) 经济模式转型\nC. 文化价值重塑"
        )
        result = trigger_direction_generation(account_id=1, idea="测试")

    assert len(result["directions"]) == 3
    assert result["directions"][0]["title"] == "社会结构变迁"


def test_direction_task_candidate_fallback():
    """所有解析器失败但 ≥3 个候选行 → 兜底解析（最终 fallback）"""
    with patch("app.tasks.httpx.Client") as mock_client:
        mock_instance = MagicMock()
        mock_client.return_value.__enter__.return_value = mock_instance
        mock_instance.post.return_value = _mock_llm_response(
            "这是一个关于技术未来的切入点\n另一个角度是社会发展\n第三个视角可以从个人成长来看"
        )
        result = trigger_direction_generation(account_id=1, idea="测试")

    assert len(result["directions"]) >= 3
    assert result["directions"][0]["id"] == "A"


def test_direction_task_empty_content_raises():
    """LLM 返回空内容抛出 ValueError"""
    with patch("app.tasks.httpx.Client") as mock_client:
        mock_instance = MagicMock()
        mock_client.return_value.__enter__.return_value = mock_instance
        mock_instance.post.return_value = _mock_llm_response("")

        with pytest.raises(ValueError, match="方向生成返回内容为空"):
            trigger_direction_generation(account_id=1, idea="测试")


def test_direction_task_unparseable_content_raises():
    """LLM 返回无法解析的内容（候选行 < 3）抛出 ValueError"""
    with patch("app.tasks.httpx.Client") as mock_client:
        mock_instance = MagicMock()
        mock_client.return_value.__enter__.return_value = mock_instance
        # 仅 2 个候选行，不够 3 个触达兜底条件
        mock_instance.post.return_value = _mock_llm_response("只有一句话")

        with pytest.raises(ValueError, match="方向生成返回内容无法解析"):
            trigger_direction_generation(account_id=1, idea="测试")


def test_direction_task_with_account_id_zero():
    """account_id=0 时任务正常运行（素材中心路径）"""
    with patch("app.tasks.httpx.Client") as mock_client:
        mock_instance = MagicMock()
        mock_client.return_value.__enter__.return_value = mock_instance
        mock_instance.post.return_value = _mock_llm_response(
            '[{"id": "A", "title": "免费模式"}, {"id": "B", "title": "付费模式"}]'
        )
        result = trigger_direction_generation(account_id=0, idea="素材内容测试")

    assert len(result["directions"]) == 2
    assert result["account_id"] == 0


# ── Celery AsyncResult 端点测试 ──

def test_task_result_endpoint_success(auth_client):
    """GET /generate/task/{id}/result 成功任务返回正确结构"""
    acc = auth_client.post("/api/accounts", json={
        "platform": "test", "account_name": "dir_result"
    }).json()

    mock_result = {
        "account_id": acc["id"],
        "directions": [
            {"id": "A", "title": "数据隐私"},
            {"id": "B", "title": "算法公平"},
        ]
    }

    with patch("app.api.generate.trigger_direction_generation.delay") as mock_delay:
        mock_task = MagicMock()
        mock_task.id = "result-test-task"
        mock_delay.return_value = mock_task
        auth_client.post("/api/generate/directions", json={
            "account_id": acc["id"], "idea": "AI 伦理"
        })

    mock_async = MagicMock()
    type(mock_async).state = PropertyMock(return_value="SUCCESS")
    mock_async.result = mock_result
    mock_async.successful.return_value = True

    with patch("celery.result.AsyncResult", return_value=mock_async):
        resp = auth_client.get("/api/generate/task/result-test-task/result")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert len(data["result"]["directions"]) == 2


def test_task_result_endpoint_failed(auth_client):
    """GET /generate/task/{id}/result 失败任务返回 error_message"""
    mock_async = MagicMock()
    type(mock_async).state = PropertyMock(return_value="FAILURE")
    mock_async.result = ValueError("方向生成返回内容为空")

    with patch("celery.result.AsyncResult", return_value=mock_async):
        resp = auth_client.get("/api/generate/task/failed-task/result")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "failed"
        assert "error_message" in data


def test_task_result_endpoint_pending(auth_client):
    """GET /generate/task/{id}/result PENDING 状态"""
    mock_async = MagicMock()
    type(mock_async).state = PropertyMock(return_value="PENDING")

    with patch("celery.result.AsyncResult", return_value=mock_async):
        resp = auth_client.get("/api/generate/task/pending-task/result")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "pending"
