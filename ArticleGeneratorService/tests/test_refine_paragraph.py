"""Change 3 v2：标记包裹微调（_wrap_paragraphs / _unwrap_paragraphs）测试。"""
import json
from app.tasks import (
    _split_paragraphs,
    _parse_weak_paragraphs,
    _wrap_paragraphs,
    _unwrap_paragraphs,
)


# ══ _split_paragraphs ══

def test_split_paragraphs_normal():
    content = "我是标题\n\n正文第一段内容。\n\n第二段，继续说事。\n\n第三段收尾。"
    pairs, title = _split_paragraphs(content)
    assert title == "我是标题"
    assert len(pairs) == 3
    assert pairs[0] == (1, "正文第一段内容。")


def test_split_paragraphs_only_title():
    pairs, content_out = _split_paragraphs("只有一段")
    assert pairs == []


# ══ _parse_weak_paragraphs ══

def test_parse_weak_paragraphs_valid():
    detail = json.dumps({"weak_paragraphs": [{"index": 3, "severity": "high"}]})
    result = _parse_weak_paragraphs(detail)
    assert len(result) == 1


def test_parse_weak_paragraphs_empty():
    assert _parse_weak_paragraphs("") == []
    assert _parse_weak_paragraphs(None) == []


# ══ _wrap_paragraphs ══

SAMPLE_CONTENT = "标题\n\n段1内容较长需要足够长度方便测试。\n\n段2是问题段落需要修改优化。\n\n段3结尾段。"


def test_wrap_paragraphs_mark_weak():
    body, title = _split_paragraphs(SAMPLE_CONTENT)
    weak = [{"index": 2, "severity": "medium", "issue": "太短", "suggestion": "展开"}]
    marked, before = _wrap_paragraphs(title, body, weak)
    # 段2 被标记
    assert "〖¶2〗" in marked
    assert "段2是问题段落" in marked
    assert "〖/¶2〗" in marked
    # 段1、段3 没被标记
    assert "〖¶1〗" not in marked
    assert "〖¶3〗" not in marked
    # before 记录正确
    assert len(before) == 1
    assert before[0]["index"] == 2


def test_wrap_paragraphs_no_weak():
    body, title = _split_paragraphs(SAMPLE_CONTENT)
    marked, before = _wrap_paragraphs(title, body, [])
    # 无标记
    assert "〖¶" not in marked
    assert before == []


def test_wrap_paragraphs_multiple_weak():
    body, title = _split_paragraphs(SAMPLE_CONTENT)
    weak = [{"index": 1}, {"index": 3}]
    marked, before = _wrap_paragraphs(title, body, weak)
    assert "〖¶1〗" in marked
    assert "〖¶3〗" in marked
    assert len(before) == 2


# ══ _unwrap_paragraphs ══

def test_unwrap_extract_and_replace():
    body, title = _split_paragraphs(SAMPLE_CONTENT)
    weak = [{"index": 2}]
    _, before = _wrap_paragraphs(title, body, weak)

    # 模拟 LLM 返回：只改了标记内的段2
    llm_output = "标题\n\n段1内容较长需要足够长度方便测试。\n\n〖¶2〗\n改写的段2内容。\n〖/¶2〗\n\n段3结尾段。"
    new_content, changes = _unwrap_paragraphs(title, body, llm_output, before)

    assert "改写的段2内容" in new_content
    assert "段1内容" in new_content  # 未动
    assert "段3结尾" in new_content  # 未动
    assert "〖¶2〗" not in new_content  # 标记已去除
    assert len(changes) == 1
    assert changes[0]["index"] == 2
    assert changes[0]["status"] == "rewritten"


def test_unwrap_llm_no_change():
    """LLM 没改任何段"""
    body, title = _split_paragraphs(SAMPLE_CONTENT)
    weak = [{"index": 2}]
    _, before = _wrap_paragraphs(title, body, weak)

    # LLM 返回原样
    new_content, changes = _unwrap_paragraphs(title, body, SAMPLE_CONTENT, before)
    assert changes[0]["status"] == "skipped"


def test_unwrap_llm_lost_marker():
    """LLM 丢了标记"""
    body, title = _split_paragraphs(SAMPLE_CONTENT)
    weak = [{"index": 2}]
    _, before = _wrap_paragraphs(title, body, weak)

    llm_output = "标题\n\n段1没动。\n\n段2也没标记直接返回了。\n\n段3。"
    new_content, changes = _unwrap_paragraphs(title, body, llm_output, before)
    # 段2 没被替换（标记丢失）
    assert changes[0]["status"] == "skipped"
    assert "reason" in changes[0]


# ══ refine_history 结构 ══

def test_history_paragraph_mode():
    entry = {"keywords": "温和", "mode": "paragraph", "changes": [
        {"index": 2, "before": "原文", "after": "新文", "status": "rewritten"}
    ]}
    assert entry["mode"] == "paragraph"
    assert entry["changes"][0]["status"] == "rewritten"
    assert "before" in entry["changes"][0]


def test_history_skipped_entry():
    entry = {"keywords": "", "mode": "paragraph", "changes": [
        {"index": 5, "before": "文", "after": "文", "status": "skipped", "reason": "LLM 未返回改写"}
    ]}
    assert entry["changes"][0]["status"] == "skipped"
    assert "reason" in entry["changes"][0]
