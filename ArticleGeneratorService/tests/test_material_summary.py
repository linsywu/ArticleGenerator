"""Test material summary generation task"""
from unittest.mock import patch, MagicMock
import pytest
from app.tasks import trigger_material_summary
from app.models import MpMaterial, MpAccount
from app.database import SessionLocal


def _mock_chat_response(content: str):
    mock_resp = MagicMock()
    mock_resp.raise_for_status.return_value = None
    mock_resp.json.return_value = {"content": content}
    return mock_resp


def test_generate_summary_saves_to_db():
    """摘要生成后落库"""
    db = SessionLocal()
    acc = MpAccount(name="test_summary", fakeid="test123")
    db.add(acc)
    db.commit()

    material = MpMaterial(
        account_id=acc.id,
        title="测试文章",
        original_url="https://example.com/test",
        content_markdown="这是一篇测试文章的内容。",
    )
    db.add(material)
    db.commit()
    mat_id = material.id
    db.close()

    with patch("app.tasks.httpx.Client") as mock_client:
        mock_instance = MagicMock()
        mock_client.return_value.__enter__.return_value = mock_instance
        mock_instance.post.return_value = _mock_chat_response("AI 生成的摘要内容")

        result = trigger_material_summary(mat_id, "测试文章", "内容...")

    assert result["summary"] == "AI 生成的摘要内容"

    db = SessionLocal()
    mat = db.query(MpMaterial).filter(MpMaterial.id == mat_id).first()
    assert mat.summary == "AI 生成的摘要内容"
    db.close()


def test_empty_response_raises():
    """LLM 返回空内容时抛错"""
    db = SessionLocal()
    acc = MpAccount(name="test_empty", fakeid="test456")
    db.add(acc)
    db.commit()
    material = MpMaterial(
        account_id=acc.id,
        title="空测试",
        original_url="https://example.com/empty",
        content_markdown="空内容测试",
    )
    db.add(material)
    db.commit()
    mat_id = material.id
    db.close()

    with patch("app.tasks.httpx.Client") as mock_client:
        mock_instance = MagicMock()
        mock_client.return_value.__enter__.return_value = mock_instance
        mock_instance.post.return_value = _mock_chat_response("")

        with pytest.raises(ValueError, match="摘要生成返回内容为空"):
            trigger_material_summary(mat_id, "空测试", "空")
