"""Test distill task progress updates"""
from unittest.mock import patch, MagicMock
from app.tasks import trigger_distill
from app.models import Account
from app.database import SessionLocal
import json


def test_distill_task_updates_progress():
    """蒸馏任务应逐维度更新进度"""
    db = SessionLocal()
    account = Account(platform="test", account_name="test_progress")
    db.add(account)
    db.commit()
    acc_id = account.id
    db.close()

    mock_dim_contents = [
        "理性分析型，擅长逻辑推理",
        "开门见山，三段式结构",
        "长短句交替，善用排比",
        "偏好理性词汇，较少口语",
        "大量引用数据和研究",
        "避免人身攻击，保持客观",
        "结尾留白，引发思考",
    ]

    with patch("app.tasks.httpx.Client") as mock_client:
        mock_instance = MagicMock()
        mock_client.return_value.__enter__.return_value = mock_instance

        mock_responses = []
        for content_text in mock_dim_contents:
            mock_resp = MagicMock()
            mock_resp.raise_for_status.return_value = None
            mock_resp.json.return_value = {"content": content_text}
            mock_responses.append(mock_resp)

        mock_instance.post.side_effect = mock_responses

        result = trigger_distill(acc_id, ["## Test\n\nContent here"], 1)

        assert result["status"] == "ready"
        assert mock_instance.post.call_count == 7

    db = SessionLocal()
    account = db.query(Account).filter(Account.id == acc_id).first()
    assert account.style_profile_status == "ready"
    assert account.style_profile_version >= 1

    structured = json.loads(account.style_profile_structured)
    assert structured["thinking_pattern"] == "理性分析型，擅长逻辑推理"
    assert structured["structure_pattern"] == "开门见山，三段式结构"
    assert "_progress" not in structured
    db.close()


def test_distill_task_failure_marks_failed():
    """蒸馏失败应标记为 failed"""
    db = SessionLocal()
    account = Account(platform="test", account_name="test_fail")
    db.add(account)
    db.commit()
    acc_id = account.id
    db.close()

    with patch("app.tasks.httpx.Client") as mock_client:
        mock_instance = MagicMock()
        mock_client.return_value.__enter__.return_value = mock_instance

        mock_resp_ok = MagicMock()
        mock_resp_ok.raise_for_status.return_value = None
        mock_resp_ok.json.return_value = {"content": "Good response"}

        mock_instance.post.side_effect = [mock_resp_ok, Exception("LLM timeout")]

        try:
            trigger_distill(acc_id, ["## Test\n\nContent"], 1)
        except Exception:
            pass

    db = SessionLocal()
    account = db.query(Account).filter(Account.id == acc_id).first()
    assert account.style_profile_status == "failed"
    assert "LLM timeout" in (account.style_profile or "")
    db.close()
