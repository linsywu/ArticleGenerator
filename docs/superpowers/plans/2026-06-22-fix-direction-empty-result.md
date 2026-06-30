# Fix Direction Empty Result Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 修复素材中心"创作方向"偶发返回空 `directions: []` 的问题——prompt 模板加 JSON 格式指令 + 增强备用解析器支持中文格式。

**Architecture:** 改动两处：(1) `tasks.py` 备用解析器 + 最终兜底；(2) `seed_providers.py` 种子模板 + 数据库 `direction` 场景配置。不改 API 接口、不改前端、不改 Celery 任务调用方式。

**Tech Stack:** Python, Celery, re (标准库)

---

## 文件结构

| 操作 | 文件 | 职责 |
|------|------|------|
| 修改 | `ArticleGeneratorService/app/tasks.py:470-511` | 增强备用解析器 + 保守兜底 |
| 修改 | `scripts/seed_providers.py:62-76` | 更新 direction 场景种子模板 |
| 新建 | `ArticleGeneratorService/tests/test_direction_task.py` | 单元测试解析器各种 LLM 输出格式 |
| 新建 | `ArticleGeneratorService/tests/test_api_direction_e2e.py` | API 端到端测试：完整 API → Task → 解析链路 |

---

### Task 1: 更新 prompt 模板 + 种子数据

**Files:**
- Modify: `scripts/seed_providers.py:66-71`

模板改动：去掉 `风格要求：` 前缀（空值时产生 dangling label），加上 JSON 格式输出指令。

- [ ] **Step 1: 更新种子模板**

将当前代码：
```python
        "system_prompt_template": (
            "你是一个专业的内容策划。根据给定的想法和账号写作风格，生成3-5个不同的写作方向。\n\n"
            "每个方向应该是一个不同的切入角度，用一句话描述。\n\n"
            "风格要求：{{style_profile}}\n"
            "想法：{{idea}}"
        ),
```

替换为：
```python
        "system_prompt_template": (
            "你是一个专业的内容策划。根据给定的想法，生成3-5个不同的写作方向。\n\n"
            "每个方向是一个不同的切入角度，用一句话描述。\n\n"
            "{{style_profile}}"
            "想法：{{idea}}\n\n"
            "请以JSON数组格式输出：[{\"id\": \"A\", \"title\": \"切入角度\"}, {\"id\": \"B\", \"title\": \"切入角度\"}, ...]"
        ),
```

- [ ] **Step 2: 同步更新数据库**

在管理后台 `/scenario-configs` 页面，编辑 `direction` 场景的 `system_prompt_template`，粘贴上述内容。

- [ ] **Step 3: Commit**

```bash
git add scripts/seed_providers.py
git commit -m "fix: add JSON format instruction to direction scenario template"
```

---

### Task 2: 增强备用解析器 + 保守最终兜底

**Files:**
- Modify: `ArticleGeneratorService/app/tasks.py:494-511`

当 JSON 解析和 markdown code block 解析都失败时，备用解析器需要支持更多中文格式。最终兜底仅在 ≥3 个候选行时启用，否则抛错让用户重试。

- [ ] **Step 1: 替换备用解析逻辑（第 494-511 行）**

将当前代码：
```python
        # Fallback: parse numbered/bulleted text lines into directions
        if not directions:
            text_lines = []
            for line in content.strip().split("\n"):
                line = line.strip()
                # Match "1. title" or "1. **title**: description" or "- title" or "• title"
                m = re.match(r'^(?:\d+[\.\)]\s*(?:\*\*)?|[-•]\s+)(.+)', line)
                if m:
                    title = m.group(1).rstrip("*").strip()
                    if title:
                        text_lines.append(title)
            if text_lines:
                labels = []
                for i, t in enumerate(text_lines):
                    labels.append({"id": chr(65 + i), "title": t})
                directions = labels

        return {"account_id": account_id, "directions": directions}
```

替换为：
```python
        # Fallback: parse numbered/bulleted text lines into directions
        if not directions:
            text_lines = []
            for line in content.strip().split("\n"):
                line = line.strip()
                if not line:
                    continue
                # Match "1. title" / "1) title" / "- title" / "• title"
                m = re.match(r'^(?:\d+[\.\)]\s*|[-•]\s+)(.+)', line)
                if m:
                    title = re.sub(r'\*+$', '', m.group(1)).strip()
                    if title:
                        text_lines.append(title)
                        continue
                # Match "方向一：title" / "角度1：title"
                m = re.match(r'^(?:方向|角度)\s*[一二三四五六七八九十\d]+\s*[：:]\s*(.+)', line)
                if m:
                    title = m.group(1).strip()
                    if title:
                        text_lines.append(title)
                        continue
                # Match "**A. title**" / "A) title" / "A. title"
                m = re.match(r'^(?:\*\*)?([A-E])[\.\)]\s*(.+?)(?:\*\*)?$', line)
                if m:
                    title = m.group(2).rstrip("*").strip()
                    if title:
                        text_lines.append(title)
                        continue
            if text_lines:
                labels = []
                for i, t in enumerate(text_lines[:5]):
                    labels.append({"id": chr(65 + i), "title": t})
                directions = labels

        # Final fallback: 所有解析器失败时，若 ≥3 个候选行才兜底，否则抛错
        if not directions and content.strip():
            candidates = [
                l.strip() for l in content.strip().split("\n")
                if l.strip() and 2 < len(l.strip()) < 200
            ]
            if len(candidates) >= 3:
                directions = [
                    {"id": chr(65 + i), "title": candidates[i]}
                    for i in range(min(len(candidates), 5))
                ]

        if not directions:
            raise ValueError(f"方向生成返回内容无法解析: {content[:200]}")

        return {"account_id": account_id, "directions": directions}
```

- [ ] **Step 2: Commit**

```bash
git add ArticleGeneratorService/app/tasks.py
git commit -m "fix: enhance direction fallback parser with Chinese format support"
```

---

### Task 3: 解析器单元测试

**Files:**
- Create: `ArticleGeneratorService/tests/test_direction_task.py`

测试各种 LLM 输出格式能否被正确解析。遵循 `test_distill_task.py` 的 mock 模式。

- [ ] **Step 1: 创建测试文件**

```python
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
```

- [ ] **Step 2: 运行测试确认全部通过**

```bash
cd ArticleGeneratorService && python3 -m pytest tests/test_direction_task.py -v
```

- [ ] **Step 3: Commit**

```bash
git add ArticleGeneratorService/tests/test_direction_task.py
git commit -m "test: add direction task parser tests for all formats"
```

---

### Task 4: API 端到端测试

**Files:**
- Modify: `ArticleGeneratorService/tests/test_api_direction_e2e.py` (新建)

测试完整 API 链路：`POST /api/generate/directions` → Celery 任务（同步执行）→ 轮询结果 → 验证 directions 非空且格式正确。

需配合 `CELERY_TASK_ALWAYS_EAGER=True` 使 Celery 同步执行，mock httpx 控制 LLM 返回值。

- [ ] **Step 1: 创建 E2E 测试文件**

```python
"""Direction API E2E tests — full API → Task → Parser flow"""
from unittest.mock import patch, MagicMock
import pytest
from app.models import Account
from app.database import SessionLocal


def _mock_chat_response(content: str):
    mock_resp = MagicMock()
    mock_resp.raise_for_status.return_value = None
    mock_resp.json.return_value = {"content": content}
    return mock_resp


class TestDirectionAPI:
    """POST /api/generate/directions → poll result → verify parsing"""

    def test_json_array_response(self, auth_client):
        """LLM 返回标准 JSON 数组 → API 返回 directions"""
        with patch("app.tasks.httpx.Client") as mock_client:
            mock_instance = MagicMock()
            mock_client.return_value.__enter__.return_value = mock_instance
            mock_instance.post.return_value = _mock_chat_response(
                '[{"id": "A", "title": "情感切入"}, {"id": "B", "title": "数据切入"}]'
            )

            resp = auth_client.post("/api/generate/directions", json={
                "account_id": 0, "idea": "测试想法"
            })
            assert resp.status_code == 200
            task_id = resp.json()["task_id"]

            # 轮询结果
            result = auth_client.get(f"/api/generate/task/{task_id}/result")
            assert result.status_code == 200
            data = result.json()
            assert data["status"] == "success"
            assert len(data["result"]["directions"]) == 2
            assert data["result"]["directions"][0]["title"] == "情感切入"

    def test_chinese_format_fallback(self, auth_client):
        """LLM 返回"方向一：xxx"中文格式 → 备用解析器提取"""
        with patch("app.tasks.httpx.Client") as mock_client:
            mock_instance = MagicMock()
            mock_client.return_value.__enter__.return_value = mock_instance
            mock_instance.post.return_value = _mock_chat_response(
                "方向一：从情感角度切入\n方向二：以数据为支撑分析\n方向三：结合时事热点"
            )

            resp = auth_client.post("/api/generate/directions", json={
                "account_id": 0, "idea": "测试想法"
            })
            task_id = resp.json()["task_id"]

            result = auth_client.get(f"/api/generate/task/{task_id}/result")
            data = result.json()
            assert data["status"] == "success"
            assert len(data["result"]["directions"]) == 3

    def test_unparseable_response_fails(self, auth_client):
        """LLM 返回不可解析内容 → 任务标记失败"""
        with patch("app.tasks.httpx.Client") as mock_client:
            mock_instance = MagicMock()
            mock_client.return_value.__enter__.return_value = mock_instance
            mock_instance.post.return_value = _mock_chat_response(
                "Here is a suggestion\nThe end"
            )

            resp = auth_client.post("/api/generate/directions", json={
                "account_id": 0, "idea": "测试想法"
            })
            task_id = resp.json()["task_id"]

            result = auth_client.get(f"/api/generate/task/{task_id}/result")
            data = result.json()
            assert data["status"] == "failed"

    def test_every_direction_has_id_and_title(self, auth_client):
        """返回的每个方向都有 id 和 title 字段"""
        with patch("app.tasks.httpx.Client") as mock_client:
            mock_instance = MagicMock()
            mock_client.return_value.__enter__.return_value = mock_instance
            mock_instance.post.return_value = _mock_chat_response(
                '[{"id": "A", "title": "方向A"}, {"id": "B", "title": "方向B"}, {"id": "C", "title": "方向C"}]'
            )

            resp = auth_client.post("/api/generate/directions", json={
                "account_id": 0, "idea": "测试想法"
            })
            task_id = resp.json()["task_id"]

            result = auth_client.get(f"/api/generate/task/{task_id}/result")
            data = result.json()
            assert data["status"] == "success"

            for d in data["result"]["directions"]:
                assert "id" in d
                assert "title" in d
                assert isinstance(d["id"], str) and len(d["id"]) == 1
                assert isinstance(d["title"], str) and len(d["title"]) > 0
```

- [ ] **Step 2: 运行 E2E 测试**

```bash
cd ArticleGeneratorService && CELERY_TASK_ALWAYS_EAGER=True python3 -m pytest tests/test_api_direction_e2e.py -v
```

- [ ] **Step 3: Commit**

```bash
git add ArticleGeneratorService/tests/test_api_direction_e2e.py
git commit -m "test: add direction API E2E tests for full flow"
```

---

### Task 5: 验证

- [ ] **Step 1: 重启 Celery worker**

```bash
cd ArticleGeneratorService
pkill -f "celery.*worker" || true
celery -A app.tasks:celery_app worker -l info &
```

- [ ] **Step 2: 浏览器验证 - 素材中心（account_id=0）**

1. 打开素材中心页面
2. 选一篇有摘要的素材，点击"💡 创作方向"
3. 确认弹窗显示"正在生成创作方向..." 后出现 3-5 个方向卡片
4. 重复 2-3 次，确认不再出现空列表

- [ ] **Step 3: 浏览器验证 - 创建页面（有账号风格）**

1. 打开 `/create`，选择一个有风格画像的账号
2. 输入想法，点击"生成写作方向"
3. 确认生成的方向体现账号风格特征

---

## 自检清单

**1. Spec coverage:**
- ✅ Prompt 模板加 JSON 格式指令 → Task 1
- ✅ 备用解析器支持中文格式 → Task 2
- ✅ 不可解析内容不静默返回空 → Task 2 最终兜底（≥3 行启用，否则抛错）

**2. Placeholder scan:** 无 TBD/TODO/占位符。

**3. Type consistency:** `DirectionItem.id` 始终为 `chr(65 + i)`（A-E），与前端 `types.ts` 一致。
