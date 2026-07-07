"""Change 3：段落级微调（切片 + 逐段改写 + 校验）测试。"""
import json
from app.tasks import (
    _split_paragraphs,
    _validate_paragraph,
    _parse_weak_paragraphs,
    _find_paragraph,
)


# ══ _split_paragraphs ══

def test_split_paragraphs_normal():
    """标准文章：标题 + 空行分隔正文段"""
    content = "我是标题\n\n正文第一段内容。\n\n第二段，继续说事。\n\n第三段收尾。"
    pairs, title = _split_paragraphs(content)
    assert title == "我是标题"
    assert len(pairs) == 3
    assert pairs[0] == (1, "正文第一段内容。")
    assert pairs[1] == (2, "第二段，继续说事。")
    assert pairs[2] == (3, "第三段收尾。")


def test_split_paragraphs_only_title():
    """只有标题，无法切分"""
    content = "只有一段，像标题又像正文"
    pairs, content_out = _split_paragraphs(content)
    assert pairs == []
    assert content_out == content


def test_split_paragraphs_empty():
    """空内容"""
    pairs, content_out = _split_paragraphs("")
    assert pairs == []


def test_split_paragraphs_markdown_style():
    """Markdown 格式标题 + 正文"""
    content = "# 我是 Markdown 标题\n\n第一段。\n\n第二段。"
    pairs, title = _split_paragraphs(content)
    assert title == "# 我是 Markdown 标题"
    assert len(pairs) == 2
    assert pairs[0] == (1, "第一段。")
    assert pairs[1] == (2, "第二段。")


# ══ _validate_paragraph ══

def test_validate_normal():
    """正常改写通过"""
    result = _validate_paragraph("改写后的单段文本", "原文较长较长较长较长较长较长较长")
    assert result == "改写后的单段文本"


def test_validate_empty():
    """空文本保留原文"""
    result = _validate_paragraph("", "原文内容")
    assert result == "原文内容"


def test_validate_too_short():
    """改写过短（<30%）保留原文"""
    old = "这是一个非常长的段落，包含很多有价值的内容和信息" * 3
    result = _validate_paragraph("短", old)
    assert result == old


def test_validate_multi_paragraph():
    """含空行（多段输出）保留原文"""
    old = "这是原文段落内容"
    result = _validate_paragraph("改写段1\n\n改写段2", old)
    assert result == old


# ══ _parse_weak_paragraphs ══

def test_parse_weak_paragraphs_valid():
    detail = json.dumps({
        "weak_paragraphs": [
            {"index": 3, "severity": "high", "issue": "套话", "suggestion": "补数据"}
        ]
    })
    result = _parse_weak_paragraphs(detail)
    assert len(result) == 1
    assert result[0]["index"] == 3


def test_parse_weak_paragraphs_empty():
    assert _parse_weak_paragraphs("") == []
    assert _parse_weak_paragraphs(None) == []


def test_parse_weak_paragraphs_invalid_json():
    assert _parse_weak_paragraphs("{not json}") == []


def test_parse_weak_paragraphs_no_weak():
    detail = json.dumps({"weak_paragraphs": []})
    assert _parse_weak_paragraphs(detail) == []


# ══ _find_paragraph ══

def test_find_paragraph_exists():
    pairs = [(1, "段1"), (2, "段2"), (3, "段3")]
    assert _find_paragraph(pairs, 2) == "段2"


def test_find_paragraph_missing():
    pairs = [(1, "段1")]
    assert _find_paragraph(pairs, 99) == ""


# ══ refine_history 结构验证 ══

def test_refine_history_paragraph_mode():
    """段落级模式历史记录结构验证"""
    entry = {
        "keywords": "语气温和",
        "mode": "paragraph",
        "changes": [
            {"index": 2, "before": "原段落", "after": "新段落", "status": "rewritten"},
            {"index": 5, "before": "原段5", "after": "原段5", "status": "skipped"},
        ]
    }
    assert entry["mode"] == "paragraph"
    assert len(entry["changes"]) == 2
    assert entry["changes"][0]["status"] == "rewritten"
    assert entry["changes"][1]["status"] == "skipped"
    assert "before" in entry["changes"][0]
    assert "after" in entry["changes"][0]


def test_refine_history_full_mode():
    """回退整篇模式历史记录结构验证"""
    entry = {
        "keywords": "缩短到500字",
        "mode": "full",
        "changes": []
    }
    assert entry["mode"] == "full"
    assert entry["changes"] == []
