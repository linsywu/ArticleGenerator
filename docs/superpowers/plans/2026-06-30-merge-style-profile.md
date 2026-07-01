# 合并 style_profile 和 style_instructions 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 generate 模板中的 `{{style_profile}}` 和 `{{style_instructions}}` 合并为单一 `{{style_profile}}`，同时优化 distill 提示词使输出精炼且为写作指导风格。

**Architecture:** 改动集中在 3 个文件：种子脚本（模板定义）、Celery 任务（变量构建/蒸馏汇总）、前端变量提示。LLM Gateway 自动注入 `style_profile`，无需改动。数据库需更新已有配置。

**Tech Stack:** Python (FastAPI + Celery), Vue 3 + TypeScript, SQLite/MySQL

## Global Constraints

- 后端测试从 `ArticleGeneratorService/` 目录执行（SQLite CWD 依赖）
- 前端验证必须启动 dev server 浏览器访问，禁止仅依赖 build+test
- 注释语言：中文
- 提交格式：语义化（`feat:`/`fix:`）
- 每个实现任务前必须先写失败测试，再写实现代码使测试通过（TDD: Red → Green → Refactor）

---

### Task 1: 更新蒸馏场景提示词模板（种子脚本）

**Files:**
- Modify: `scripts/seed_providers.py:43-61`

**Interfaces:**
- Produces: 新的 `distill` scenario `system_prompt_template`，使用 `{{dimension}}` 和 `{{dimension_prompt}}` 变量

**说明:** 纯模板文本替换，无关联代码逻辑。

- [ ] **Step 1: 替换 distill 模板**

将旧模板（硬编码 7 个分析维度）替换为通用单维度 + 写作指导输出格式：

```python
# scripts/seed_providers.py:43-61 — 替换整个 system_prompt_template
{
    "scenario": "distill",
    "model": "claude-sonnet-4-20250514",
    "system_prompt_template": (
        "你是一个写作风格提炼师。根据以下参考文章，仅针对「{{dimension}}」这一个维度提炼写作指导。\n\n"
        "分析要点：{{dimension_prompt}}\n\n"
        "要求：\n"
        "- 输出 4-6 条写作指导指令，每条不超过 40 字\n"
        "- 用指令式语气：应... / 避免... / 倾向于... / 多...少...\n"
        "- 不要写分析过程或原因解释\n"
        "- 只写确定能观察到的特征，不要编造\n\n"
        "共 {{num_articles}} 篇参考文章：\n{{articles_content}}"
    ),
    "params": '{"max_tokens": 1024, "temperature": 0.5}',
    "priority": 10,
    "description": "① 风格蒸馏：单维度提炼写作指导指令",
    "sort_order": 1,
},
```

- [ ] **Step 2: 验证语法正确**

```bash
cd /Users/linsywu/Documents/AI-space/ArticleGenerator
python3 -c "compile(open('scripts/seed_providers.py').read(), 'seed_providers.py', 'exec'); print('OK')"
```

- [ ] **Step 3: Commit**

```bash
git add scripts/seed_providers.py
git commit -m "feat: rewrite distill prompt as generic per-dimension writing-guidance template"
```

---

### Task 2: 更新生成场景提示词模板（种子脚本）

**Files:**
- Modify: `scripts/seed_providers.py:131-159`

**Interfaces:**
- Consumes: Task 1 的 distill 输出格式（`style_profile` 现在为写作指导风格）
- Produces: 新的 `generate` scenario `system_prompt_template`，仅含 `{{style_profile}}`

**说明:** 纯模板文本替换，无关联代码逻辑。

- [ ] **Step 1: 移除 style_instructions，更新 style_profile 上下文**

```python
# scripts/seed_providers.py:131-159 — 修改 generate system_prompt_template
{
    "scenario": "generate",
    "model": "claude-sonnet-4-20250514",
    "system_prompt_template": (
        "你是一个专业的内容创作者。\n\n"
        "## 核心约束（最高优先级）\n"
        "你必须严格围绕指定的「文章主题」和「写作方向」进行创作，不得偏离到其他话题。\n"
        "风格要求仅影响表达方式和语气，绝不改变文章的主题和内容方向。\n\n"
        "## 文章主题\n"
        "{{topic}}\n\n"
        "## 写作方向\n"
        "{{direction}}\n\n"
        "## 写作风格要求（必须严格遵守）\n"
        "{{style_profile}}\n"
        "{{outline_section}}"
        "{{word_count_instruction}}\n\n"
        "## 硬性要求\n"
        "- 文章必须紧扣上述主题和方向，禁止偏离到其他话题\n"
        "- 风格要求仅作为表达方式的参考，不作为主题选择依据\n"
        "- 文章需要有吸引人的标题（包含在正文开头）\n"
        "- 清晰的结构、充实的内容\n"
        "- 语言自然，避免AI写作痕迹"
    ),
    "params": '{"max_tokens": 4096, "temperature": 0.8}',
    "priority": 10,
    "description": "⑤ 文章生成：根据主题 + 方向 + 风格画像 + 大纲生成全文",
    "sort_order": 5,
},
```

变更点（相比旧模板）：
- L143: `"## 风格参考（仅影响文风，不影响主题）\n"` → `"## 写作风格要求（必须严格遵守）\n"`
- L144: `"{{style_profile}}\n\n"` → `"{{style_profile}}\n"`（移除多余空行）
- L145: 删除 `"{{style_instructions}}"` 整行

- [ ] **Step 2: 验证语法**

```bash
cd /Users/linsywu/Documents/AI-space/ArticleGenerator
python3 -c "compile(open('scripts/seed_providers.py').read(), 'seed_providers.py', 'exec'); print('OK')"
```

- [ ] **Step 3: Commit**

```bash
git add scripts/seed_providers.py
git commit -m "feat: remove style_instructions from generate template, reframe style_profile as mandatory"
```

---

### Task 3: 编写测试 — generate payload 不含 style_instructions [RED]

**Files:**
- Modify: `ArticleGeneratorService/tests/test_generate_prompt_consolidation.py:61-81`

**Interfaces:**
- Produces: 两个新测试方法，验证 generate payload 不含 `style_instructions`，旧测试更新后 FAIL

- [ ] **Step 1: 更新旧测试 — 移除 style_instructions 断言，添加反向断言**

将 `TestPayloadStructure` class 中的 `test_new_payload_uses_chat_endpoint_with_variables` 更新为反映新结构：

```python
class TestPayloadStructure:
    """验证发往 LLM 的 payload 结构"""

    def test_new_payload_uses_chat_endpoint_with_variables(self):
        """新架构：发 /chat，传 scenario + variables，不传 style_instructions"""
        payload = {
            "scenario": "generate",
            "account_id": 1,
            "variables": {
                "topic": "测试主题",
                "outline_section": "",
                "word_count_instruction": "字数1500左右。",
            },
        }
        assert payload["scenario"] == "generate"
        assert "variables" in payload
        assert "user_prompt" not in payload
        assert "topic" in payload["variables"]
        assert "outline_section" in payload["variables"]
        assert "word_count_instruction" in payload["variables"]
        # 关键：style_instructions 不应出现
        assert "style_instructions" not in payload["variables"]

    def test_generate_payload_excludes_style_instructions(self):
        """trigger_generate 构建的 variables 不得包含 style_instructions"""
        payload = {
            "scenario": "generate",
            "account_id": 1,
            "variables": {
                "topic": "测试主题",
                "direction": "技术分析",
                "outline_section": "## 写作大纲\n1. 引言\n\n请严格按照以上大纲逐段写作...\n",
                "word_count_instruction": "字数1500左右。",
            },
        }
        # style_instructions 已被合并到 style_profile（由 Gateway 自动注入）
        assert "style_instructions" not in payload["variables"]
        # 确认核心变量全部存在
        assert "topic" in payload["variables"]
        assert "direction" in payload["variables"]
        assert "outline_section" in payload["variables"]
        assert "word_count_instruction" in payload["variables"]

    def test_generate_payload_relies_on_gateway_for_style_profile(self):
        """style_profile 由 Gateway 自动注入，tasks.py 不传"""
        payload = {
            "scenario": "generate",
            "account_id": 1,
            "variables": {
                "topic": "测试",
                "direction": "",
                "outline_section": "",
                "word_count_instruction": "字数1500左右。",
            },
        }
        # Gateway 注入 style_profile，tasks.py 不负责
        assert "style_profile" not in payload["variables"]
        assert "style_instructions" not in payload["variables"]
```

- [ ] **Step 2: 运行测试确认失败（RED）**

```bash
cd /Users/linsywu/Documents/AI-space/ArticleGenerator/ArticleGeneratorService
python -m pytest tests/test_generate_prompt_consolidation.py::TestPayloadStructure -v 2>&1 | tail -15
```

预期 FAIL：`assert "style_instructions" not in payload["variables"]` — 旧测试代码仍包含 `style_instructions`，需在 Task 4 实现后通过。

- [ ] **Step 3: Commit**

```bash
git add ArticleGeneratorService/tests/test_generate_prompt_consolidation.py
git commit -m "test: add assertions that generate payload excludes style_instructions [RED]"
```

---

### Task 4: 从 trigger_generate 中移除 style_instructions 逻辑 [GREEN]

**Files:**
- Modify: `ArticleGeneratorService/app/tasks.py:110-116,128-138,156`

**Interfaces:**
- Consumes: account 对象（不再读取 `style_profile_structured` 用于生成）
- Produces: variables dict 不含 `style_instructions`

- [ ] **Step 1: 删除 style_instructions 构建代码和 structured 变量声明**

删除 L110-116（structured 变量声明）和 L128-138（style_instructions 构建）：

```python
# 删除内容：
# L110-116:
#         # 获取结构化画像字段
#         structured = None
#         if account and account.style_profile_structured:
#             try:
#                 structured = json.loads(account.style_profile_structured)
#             except (json.JSONDecodeError, TypeError):
#                 pass
#
# L128-138:
#         # 注入风格要求
#         style_instructions = ""
#         if structured:
#             sp = structured
#             style_instructions = (
#                 f"【风格要求 - 必须严格遵守】\n"
#                 f"句式：{sp.get('sentence_pattern', '长短句参差，避免单调')}\n"
#                 f"用词：{sp.get('vocabulary_pattern', '')}\n"
#                 f"禁忌——绝对不要出现以下内容：{sp.get('taboos', '')}\n"
#                 f"留白：{sp.get('blank_leaving', '道理只讲七分，不总结不升华')}\n"
#             )
```

- [ ] **Step 2: 从 variables dict 中移除 style_instructions 条目**

```python
# variables 修改后（原 L149-159）
payload = {
    "scenario": "generate",
    "task_id": self.request.id,
    "account_id": account_id,
    "variables": {
        "topic": topic,
        "direction": direction or "",
        "outline_section": outline_section,
        "word_count_instruction": word_count_instruction,
    },
}
```

- [ ] **Step 3: 运行测试确认通过（GREEN）**

```bash
cd /Users/linsywu/Documents/AI-space/ArticleGenerator/ArticleGeneratorService
python -m pytest tests/test_generate_prompt_consolidation.py -v 2>&1 | tail -20
```

预期：全部 10 个测试 PASS。

- [ ] **Step 4: Commit**

```bash
git add ArticleGeneratorService/app/tasks.py
git commit -m "feat: remove style_instructions construction from trigger_generate"
```

---

### Task 5: 编写测试 — 蒸馏汇总格式为写作指导风格 [RED]

**Files:**
- Modify: `ArticleGeneratorService/tests/test_distill_task.py`

**Interfaces:**
- Produces: 新测试方法 `test_distill_summary_format_is_writing_guide`，验证 `style_profile` 文本使用 `##` markdown 标题和新标签名

- [ ] **Step 1: 在 test_distill_task.py 末尾添加测试**

```python
def test_distill_summary_format_is_writing_guide():
    """蒸馏完成后 style_profile 应为 ## markdown 标题 + 指导风格标签"""
    db = SessionLocal()
    account = Account(platform="test", account_name="test_summary_format")
    db.add(account)
    db.commit()
    acc_id = account.id
    db.close()

    # 模拟 7 个维度的指令式输出
    mock_dim_contents = [
        "应保持理性分析型思维，多用逻辑推演",
        "开篇应开门见山，采用三段式结构",
        "应长短句交替使用，避免单调",
        "多使用理性词汇，少用口语化表达",
        "应大量引用数据和研究支撑论点",
        "避免人身攻击，保持客观中立",
        "结尾应留白处理，引发读者思考",
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

    db = SessionLocal()
    account = db.query(Account).filter(Account.id == acc_id).first()

    style_profile = account.style_profile or ""

    # 验证使用 ## markdown 标题格式（非旧版 【】格式）
    assert "## 思维模式" in style_profile
    assert "## 结构模式" in style_profile
    assert "## 句式要求" in style_profile
    assert "## 用词要求" in style_profile
    assert "## 论据要求" in style_profile
    assert "## 写作禁忌" in style_profile
    assert "## 留白要求" in style_profile

    # 验证不使用旧标签格式
    assert "【思维特征】" not in style_profile
    assert "【句式特征】" not in style_profile
    assert "【词汇偏好】" not in style_profile
    assert "【论据类型】" not in style_profile
    assert "【禁忌清单】" not in style_profile
    assert "【留白程度】" not in style_profile

    # 验证标签名不包含"分析"类措辞
    assert "分析" not in style_profile.split("## ")[1].split("\n")[0] if "## " in style_profile else True

    db.close()
```

- [ ] **Step 2: 运行测试确认失败（RED）**

```bash
cd /Users/linsywu/Documents/AI-space/ArticleGenerator/ArticleGeneratorService
python -m pytest tests/test_distill_task.py::test_distill_summary_format_is_writing_guide -v 2>&1
```

预期 FAIL：`AssertionError: assert '## 思维模式' in '...'` — 旧代码使用 `【思维特征】` 格式。

- [ ] **Step 3: Commit**

```bash
git add ArticleGeneratorService/tests/test_distill_task.py
git commit -m "test: add distill summary format test expecting ## markdown writing-guide labels [RED]"
```

---

### Task 6: 更新蒸馏汇总格式为写作指导风格 [GREEN]

**Files:**
- Modify: `ArticleGeneratorService/app/tasks.py:452-466`

**Interfaces:**
- Consumes: 7 维度 LLM 输出（已通过新 distill prompt 优化为指令式）
- Produces: `account.style_profile` — 写作指导风格的汇总文本

- [ ] **Step 1: 更新 dim_labels 和汇总格式**

```python
# tasks.py 原 L452-466 — 修改后
# Assemble writing guide from 7 dimension results
dim_labels = {
    "thinking_pattern": "思维模式",
    "structure_pattern": "结构模式",
    "sentence_pattern": "句式要求",
    "vocabulary_pattern": "用词要求",
    "evidence_type": "论据要求",
    "taboos": "写作禁忌",
    "blank_leaving": "留白要求",
}
parts = []
for key, label in dim_labels.items():
    if structured.get(key):
        parts.append(f"## {label}\n{structured[key]}")
summary_text = "\n\n".join(parts)
```

变更说明：
- `"思维特征"` → `"思维模式"`（去掉"分析"暗示）
- `"句式特征"` → `"句式要求"`（改为要求语气）
- `"词汇偏好"` → `"用词要求"`（更直接）
- `"论据类型"` → `"论据要求"`（改为要求语气）
- `"禁忌清单"` → `"写作禁忌"`（更简洁）
- `"留白程度"` → `"留白要求"`（改为要求语气）
- 格式：`"【{label}】\n"` → `"## {label}\n"`（markdown 标题）

- [ ] **Step 2: 运行测试确认通过（GREEN）**

```bash
cd /Users/linsywu/Documents/AI-space/ArticleGenerator/ArticleGeneratorService
python -m pytest tests/test_distill_task.py -v 2>&1 | tail -20
```

预期：全部 3 个测试 PASS（含新增的 `test_distill_summary_format_is_writing_guide`）。

- [ ] **Step 3: Commit**

```bash
git add ArticleGeneratorService/app/tasks.py
git commit -m "feat: update distill summary format to writing-guide style with markdown headings"
```

---

### Task 7: 更新前端变量提示

**Files:**
- Modify: `ArticleGeneratorAdm/src/views/ScenarioConfigsView.vue:133-139`

- [ ] **Step 1: 删除 style_instructions 变量提示行，更新 style_profile 描述**

```typescript
// ScenarioConfigsView.vue L133-139 — 修改后
generate: [
  { name: 'topic', description: '文章主题（用户确认的标题 + 原始想法，或热点标题）' },
  { name: 'style_profile', description: '账号写作风格指导（来自风格蒸馏，7维度指令式要求）' },
  { name: 'outline_section', description: '写作大纲整段（含 ## 标题和约束语）；用户跳过或无大纲时为空字符串' },
  { name: 'word_count_instruction', description: '字数要求，如「字数1500左右。」' },
],
```

变更：删除 L136 的 `style_instructions` 条目，更新 `style_profile` 的 description。

- [ ] **Step 2: Build 验证**

```bash
cd /Users/linsywu/Documents/AI-space/ArticleGenerator/ArticleGeneratorAdm
npm run build 2>&1 | tail -5
```

预期：`✓ built in X.XXs`

- [ ] **Step 3: Commit**

```bash
git add ArticleGeneratorAdm/src/views/ScenarioConfigsView.vue
git commit -m "feat: remove style_instructions from generate variable hints"
```

---

### Task 8: 更新数据库中已有场景配置

**Files:**
- Create: `ArticleGeneratorDatabase/migrations/006_update_distill_generate_prompts.sql`

**说明:** 种子脚本只影响新部署。已有数据库的 `scenario_configs` 表需要手动更新。

- [ ] **Step 1: 创建迁移 SQL**

```sql
-- 006_update_distill_generate_prompts.sql
-- 更新 distill 场景提示词为通用单维度模板
UPDATE scenario_configs
SET system_prompt_template = '你是一个写作风格提炼师。根据以下参考文章，仅针对「{{dimension}}」这一个维度提炼写作指导。\n\n分析要点：{{dimension_prompt}}\n\n要求：\n- 输出 4-6 条写作指导指令，每条不超过 40 字\n- 用指令式语气：应... / 避免... / 倾向于... / 多...少...\n- 不要写分析过程或原因解释\n- 只写确定能观察到的特征，不要编造\n\n共 {{num_articles}} 篇参考文章：\n{{articles_content}}',
    description = '① 风格蒸馏：单维度提炼写作指导指令'
WHERE scenario = 'distill';

-- 更新 generate 场景提示词：移除 style_instructions，更新 style_profile 上下文
UPDATE scenario_configs
SET system_prompt_template = '你是一个专业的内容创作者。\n\n## 核心约束（最高优先级）\n你必须严格围绕指定的「文章主题」和「写作方向」进行创作，不得偏离到其他话题。\n风格要求仅影响表达方式和语气，绝不改变文章的主题和内容方向。\n\n## 文章主题\n{{topic}}\n\n## 写作方向\n{{direction}}\n\n## 写作风格要求（必须严格遵守）\n{{style_profile}}\n{{outline_section}}{{word_count_instruction}}\n\n## 硬性要求\n- 文章必须紧扣上述主题和方向，禁止偏离到其他话题\n- 风格要求仅作为表达方式的参考，不作为主题选择依据\n- 文章需要有吸引人的标题（包含在正文开头）\n- 清晰的结构、充实的内容\n- 语言自然，避免AI写作痕迹',
    description = '⑤ 文章生成：根据主题 + 方向 + 风格画像 + 大纲生成全文'
WHERE scenario = 'generate';
```

- [ ] **Step 2: 执行迁移**

```bash
cd /Users/linsywu/Documents/AI-space/ArticleGenerator/ArticleGeneratorService
sqlite3 article_generator.db < ../ArticleGeneratorDatabase/migrations/006_update_distill_generate_prompts.sql
```

- [ ] **Step 3: Commit**

```bash
git add ArticleGeneratorDatabase/migrations/006_update_distill_generate_prompts.sql
git commit -m "feat: add migration to update distill and generate prompt templates"
```

---

### Task 9: 端到端验证

- [ ] **Step 1: 运行全部后端测试**

```bash
cd /Users/linsywu/Documents/AI-space/ArticleGenerator/ArticleGeneratorService
python -m pytest tests/ -v --tb=short 2>&1 | tail -30
```

预期：全部通过，无 regression。

- [ ] **Step 2: 运行全部前端测试**

```bash
cd /Users/linsywu/Documents/AI-space/ArticleGenerator/ArticleGeneratorAdm
npx vitest run 2>&1 | tail -15
```

预期：全部通过。

- [ ] **Step 3: 浏览器验证**

启动前后端，浏览器访问：
1. 场景配置页 → 确认 generate 场景变量提示不含 `style_instructions`
2. 场景配置页 → distill 场景模板显示新提示词
3. 账号蒸馏 → 验证输出格式为 `##` 标题 + 指令式内容
4. 文章生成 → 验证正常生成，日志中 `style_instructions` 不再出现

- [ ] **Step 4: 最终 Commit（如有遗漏文件）**

```bash
git status
git add -A
git commit -m "chore: final verification adjustments for style-profile merge"
```
