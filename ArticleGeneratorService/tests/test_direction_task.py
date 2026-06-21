"""Test direction task parsing with various LLM response formats"""
from unittest.mock import patch, MagicMock
import pytest
from app.tasks import trigger_direction_generation


def _mock_chat_response(content: str):
    """Helper: build a mock httpx response for the LLM /chat call"""
    mock_resp = MagicMock()
    mock_resp.raise_for_status.return_value = None
    mock_resp.json.return_value = {"content": content}
    return mock_resp


def test_parse_json_array():
    """LLM 返回 JSON 数组格式"""
    with patch("app.tasks.httpx.Client") as mock_client:
        mock_instance = MagicMock()
        mock_client.return_value.__enter__.return_value = mock_instance
        mock_instance.post.return_value = _mock_chat_response(
            '[{"id": "A", "title": "情感切入"}, {"id": "B", "title": "数据切入"}]'
        )
        result = trigger_direction_generation(0, "测试想法")

    assert len(result["directions"]) == 2
    assert result["directions"][0]["id"] == "A"
    assert result["directions"][0]["title"] == "情感切入"


def test_parse_json_with_directions_key():
    """LLM 返回 {"directions": [...]} 格式"""
    with patch("app.tasks.httpx.Client") as mock_client:
        mock_instance = MagicMock()
        mock_client.return_value.__enter__.return_value = mock_instance
        mock_instance.post.return_value = _mock_chat_response(
            '{"directions": [{"id": "1", "title": "方向一"}]}'
        )
        result = trigger_direction_generation(0, "测试想法")

    assert len(result["directions"]) == 1


def test_parse_markdown_code_block():
    """LLM 返回 markdown ```json 代码块"""
    with patch("app.tasks.httpx.Client") as mock_client:
        mock_instance = MagicMock()
        mock_client.return_value.__enter__.return_value = mock_instance
        mock_instance.post.return_value = _mock_chat_response(
            '```json\n[{"id": "A", "title": "标题A"}]\n```'
        )
        result = trigger_direction_generation(0, "测试想法")

    assert len(result["directions"]) == 1
    assert result["directions"][0]["id"] == "A"


def test_parse_numbered_list():
    """LLM 返回英文编号列表"""
    with patch("app.tasks.httpx.Client") as mock_client:
        mock_instance = MagicMock()
        mock_client.return_value.__enter__.return_value = mock_instance
        mock_instance.post.return_value = _mock_chat_response(
            "1. 情感共鸣切入\n2. 数据驱动分析\n3. 社会热点视角"
        )
        result = trigger_direction_generation(0, "测试想法")

    assert len(result["directions"]) == 3
    assert result["directions"][0]["title"] == "情感共鸣切入"


def test_parse_chinese_direction_format():
    """LLM 返回"方向一：xxx"中文格式"""
    with patch("app.tasks.httpx.Client") as mock_client:
        mock_instance = MagicMock()
        mock_client.return_value.__enter__.return_value = mock_instance
        mock_instance.post.return_value = _mock_chat_response(
            "方向一：从情感角度切入\n方向二：以数据为支撑分析\n方向三：结合时事热点"
        )
        result = trigger_direction_generation(0, "测试想法")

    assert len(result["directions"]) == 3
    assert result["directions"][0]["title"] == "从情感角度切入"


def test_parse_chinese_angle_format():
    """LLM 返回"角度1：xxx"中文格式"""
    with patch("app.tasks.httpx.Client") as mock_client:
        mock_instance = MagicMock()
        mock_client.return_value.__enter__.return_value = mock_instance
        mock_instance.post.return_value = _mock_chat_response(
            "角度1：情感维度\n角度2：理性分析维度"
        )
        result = trigger_direction_generation(0, "测试想法")

    assert len(result["directions"]) == 2


def test_parse_letter_prefix():
    """LLM 返回"A. xxx"字母编号格式"""
    with patch("app.tasks.httpx.Client") as mock_client:
        mock_instance = MagicMock()
        mock_client.return_value.__enter__.return_value = mock_instance
        mock_instance.post.return_value = _mock_chat_response(
            "A. 第一方向\nB. 第二方向\nC. 第三方向"
        )
        result = trigger_direction_generation(0, "测试想法")

    assert len(result["directions"]) == 3


def test_final_fallback_with_enough_candidates():
    """≥3 个候选行时启用兜底"""
    with patch("app.tasks.httpx.Client") as mock_client:
        mock_instance = MagicMock()
        mock_client.return_value.__enter__.return_value = mock_instance
        mock_instance.post.return_value = _mock_chat_response(
            "我觉得可以从以下几个角度来写这篇文章\n情感角度是一个很好的切入点\n数据支撑会更有说服力\n结合热点事件能增加传播性"
        )
        result = trigger_direction_generation(0, "测试想法")

    assert len(result["directions"]) >= 3
    assert len(result["directions"]) <= 5
    for d in result["directions"]:
        assert "id" in d
        assert "title" in d
        assert len(d["id"]) == 1


def test_final_fallback_insufficient_candidates_raises():
    """不足 3 个候选行时抛错"""
    with patch("app.tasks.httpx.Client") as mock_client:
        mock_instance = MagicMock()
        mock_client.return_value.__enter__.return_value = mock_instance
        mock_instance.post.return_value = _mock_chat_response(
            "Based on your idea, here is a suggestion:\nConsider using emotional angles."
        )

        with pytest.raises(ValueError, match="方向生成返回内容无法解析"):
            trigger_direction_generation(0, "测试想法")


def test_account_id_zero_returns_directions():
    """素材中心路径 account_id=0 应正常返回方向"""
    with patch("app.tasks.httpx.Client") as mock_client:
        mock_instance = MagicMock()
        mock_client.return_value.__enter__.return_value = mock_instance
        mock_instance.post.return_value = _mock_chat_response(
            '[{"id": "A", "title": "测试方向"}]'
        )
        result = trigger_direction_generation(0, "测试想法")

    assert result["account_id"] == 0
    assert len(result["directions"]) >= 1


def test_empty_content_raises():
    """LLM 返回空内容时抛出异常"""
    with patch("app.tasks.httpx.Client") as mock_client:
        mock_instance = MagicMock()
        mock_client.return_value.__enter__.return_value = mock_instance
        mock_instance.post.return_value = _mock_chat_response("")

        try:
            trigger_direction_generation(0, "测试想法")
            assert False, "应该抛出异常"
        except ValueError as e:
            assert "方向生成返回内容为空" in str(e)
