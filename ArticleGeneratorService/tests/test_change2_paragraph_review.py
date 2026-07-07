"""Change 2：段落级质量评审 JSON 解析测试。"""
import json
import re


# ---- 解析逻辑（从 tasks.py 抽取，测试驱动开发） ----

def _parse_quality_review(text: str) -> dict:
    """从 LLM 输出中提取段落级评审 JSON。容错：优先 ```json 块 → 纯文本 regex → 旧 _parse_score 回退。"""
    # 1) 尝试提取 ```json ... ``` 代码块
    m = re.search(r"```json\s*([\s\S]*?)\s*```", text)
    if m:
        try:
            return json.loads(m.group(1))
        except json.JSONDecodeError:
            pass

    # 2) 尝试直接找最外层 JSON 对象
    m2 = re.search(r"\{[\s\S]*\"overall_score\"[\s\S]*\}", text)
    if m2:
        try:
            return json.loads(m2.group(0))
        except json.JSONDecodeError:
            pass

    # 3) 回退：只取总分
    score = _parse_score_fallback(text)
    return {"overall_score": score, "dimensions": {}, "weak_paragraphs": []}


def _parse_score_fallback(text: str) -> int:
    """旧 _parse_score 逻辑（兼容非 JSON 输出）。"""
    total_match = re.search(r"总分[：:\s]*(\d{1,3})", text)
    if total_match:
        s = int(total_match.group(1))
        if 0 <= s <= 100:
            return s
    overall = re.search(r"(?:综合|最终)(?:评分|得分)[：:\s]*(\d{1,3})", text)
    if overall:
        s = int(overall.group(1))
        if 0 <= s <= 100:
            return s
    nums = re.findall(r"\b([0-9]{1,3})\b", text)
    scores = [int(n) for n in nums if 0 <= int(n) <= 100]
    return scores[-1] if scores else 0


# ---- 测试用例 ----

VALID_JSON = """{
  "overall_score": 85,
  "dimensions": {"originality": 22, "logic": 21, "readability": 22, "info_density": 20},
  "weak_paragraphs": [
    {"index": 3, "severity": "high", "issue": "套话堆砌", "suggestion": "用具体数据替换"}
  ]
}"""


def test_parse_pure_json():
    """纯 JSON 直接解析。"""
    r = _parse_quality_review(VALID_JSON)
    assert r["overall_score"] == 85
    assert r["dimensions"]["originality"] == 22
    assert len(r["weak_paragraphs"]) == 1
    assert r["weak_paragraphs"][0]["index"] == 3


def test_parse_json_in_code_block():
    """LLM 输出包裹在 ```json 中。"""
    text = f"好的，以下是评审结果：\n```json\n{VALID_JSON}\n```\n希望对您有帮助。"
    r = _parse_quality_review(text)
    assert r["overall_score"] == 85
    assert len(r["weak_paragraphs"]) == 1


def test_parse_no_json_fallback():
    """非 JSON 输出回退到旧 _parse_score。"""
    text = "原创性：22分\n逻辑性：21分\n可读性：22分\n信息密度：20分\n总分：85"
    r = _parse_quality_review(text)
    assert r["overall_score"] == 85
    assert r["dimensions"] == {}
    assert r["weak_paragraphs"] == []


def test_parse_empty():
    """空内容返回 0。"""
    r = _parse_quality_review("")
    assert r["overall_score"] == 0


def test_parse_malformed_json_with_score():
    """JSON 解析失败但能提取总分。"""
    text = "总分：72\n{broken json"
    r = _parse_quality_review(text)
    assert r["overall_score"] == 72
