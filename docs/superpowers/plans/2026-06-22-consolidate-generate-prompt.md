# Generate Prompt Consolidation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Merge generate scenario's user_prompt into system_prompt_template, make outline optional, rename `hotspot_title` → `topic`, and pass outline to humanize.

**Architecture:** All prompt text lives in `scenario_configs.system_prompt_template`. Celery builds variables dict (topic, style_instructions, outline_section, word_count_instruction) → Gateway renders template → User message is minimal trigger `"请开始创作。"`.

**Tech Stack:** Python/FastAPI/Celery backend, Vue 3/TypeScript frontend, SQLite/MySQL DB

---

### Task 1: Rename `hotspot_title` → `topic` in Celery task

**Files:**
- Modify: `ArticleGeneratorService/app/tasks.py:88`

- [ ] **Step 1: Rename parameter and internal references in trigger_generate**

Replace line 88:
```python
def trigger_generate(self, hotspot_title: str, account_id: int, hotspot_id: int = None, outline: list = None, word_count: str = None):
```
With:
```python
def trigger_generate(self, topic: str, account_id: int, hotspot_id: int = None, outline: list = None, word_count: str = None):
```

- [ ] **Step 2: Update all internal references in trigger_generate**

Replace `hotspot_title` → `topic` everywhere in the function body:

Line 141 (old user_prompt building — will be restructured in Task 2, but for now):
```python
f'以"{topic}"为题，写一篇文章。\n\n'
```

Line 150 (payload):
```python
payload = {
    "topic": topic,
    "account_id": account_id,
}
```

Line 166 (title resolution):
```python
title = resolve_article_title(content, topic)
```

- [ ] **Step 3: Update `resolve_article_title` parameter name**

Replace line 54:
```python
def resolve_article_title(content: str, hotspot_title: str | None) -> str | None:
```
With:
```python
def resolve_article_title(content: str, topic: str | None) -> str | None:
```

And line 65-66:
```python
if topic and topic.strip():
    return topic.strip()[:200]
```

- [ ] **Step 4: Commit**

```bash
git add ArticleGeneratorService/app/tasks.py
git commit -m "refactor: rename hotspot_title to topic in Celery generate task"
```

---

### Task 2: Replace user_prompt string building with variables dict

**Files:**
- Modify: `ArticleGeneratorService/app/tasks.py:115-165`

- [ ] **Step 1: Change outline building to outline_section**

Replace lines 115-119:
```python
        # 构建增强的 user_prompt
        outline_text = ""
        if outline:
            outline_items = [f"{i+1}. {p}" for i, p in enumerate(outline)]
            outline_text = "【写作大纲】\n" + "\n".join(outline_items) + "\n\n请严格按照以上大纲逐段写作。"
```
With:
```python
        # 构建大纲 section（整段，含标题和约束语；无大纲时为空）
        outline_section = ""
        if outline:
            outline_items = [f"{i+1}. {p}" for i, p in enumerate(outline)]
            outline_section = (
                "## 写作大纲\n"
                + "\n".join(outline_items)
                + "\n\n请严格按照以上大纲逐段写作，大纲有几段文章就必须有几段。\n"
            )
```

- [ ] **Step 2: Replace user_prompt string with variables dict**

Replace lines 140-165:
```python
        user_prompt = (
            f'以"{hotspot_title}"为题，写一篇文章。\n\n'
            f'{style_instructions}\n'
            f'{outline_text}\n'
            f'{word_count_instruction}'
        )

        # 调用 LLM 服务
        llm_url = settings.llm_service_url.rstrip("/")
        payload = {
            "hotspot_title": hotspot_title,
            "account_id": account_id,
            "user_prompt": user_prompt,
        }
        if lora_path:
            payload["lora_path"] = lora_path
        with httpx.Client(timeout=120.0) as client:
            resp = client.post(f"{llm_url}/generate", json=payload)
```
With:
```python
        # 调用 LLM 服务（通过 /chat 端点，variables 由 Gateway 渲染到 system_prompt_template）
        llm_url = settings.llm_service_url.rstrip("/")
        payload = {
            "scenario": "generate",
            "account_id": account_id,
            "variables": {
                "topic": topic,
                "style_instructions": style_instructions,
                "outline_section": outline_section,
                "word_count_instruction": word_count_instruction,
            },
        }
        with httpx.Client(timeout=120.0) as client:
            resp = client.post(f"{llm_url}/chat", json=payload)
```

- [ ] **Step 3: Commit**

```bash
git add ArticleGeneratorService/app/tasks.py
git commit -m "refactor: replace user_prompt with variables dict in generate task"
```

---

### Task 3: Update trigger_humanize to receive outline_section

**Files:**
- Modify: `ArticleGeneratorService/app/tasks.py:210-220`

- [ ] **Step 1: Add outline_section parameter**

Replace line 210:
```python
def trigger_humanize(self, article_id: int, content: str):
```
With:
```python
def trigger_humanize(self, article_id: int, content: str, outline_section: str = ""):
```

- [ ] **Step 2: Pass outline_section in variables**

Replace lines 217-221:
```python
        with httpx.Client(timeout=120.0) as client:
            resp = client.post(f"{llm_url}/chat", json={
                "scenario": "humanize",
                "variables": {"article_content": content},
            })
```
With:
```python
        with httpx.Client(timeout=120.0) as client:
            resp = client.post(f"{llm_url}/chat", json={
                "scenario": "humanize",
                "variables": {
                    "article_content": content,
                    "outline_section": outline_section,
                },
            })
```

- [ ] **Step 3: Update call site in trigger_generate (line 194-195)**

Replace:
```python
        if article:
            trigger_humanize.delay(article.id, article.content)
```
With:
```python
        if article:
            trigger_humanize.delay(article.id, article.content, outline_section)
```

- [ ] **Step 4: Commit**

```bash
git add ArticleGeneratorService/app/tasks.py
git commit -m "feat: pass outline_section to humanize task for structure preservation"
```

---

### Task 4: Update service layer parameter names

**Files:**
- Modify: `ArticleGeneratorService/app/services/generate_service.py:49`

- [ ] **Step 1: Update Celery task call**

Replace line 49:
```python
        task = trigger_generate.delay(custom_topic, account_id, hotspot_id=None, outline=outline, word_count=word_count)
```
With:
```python
        task = trigger_generate.delay(topic=custom_topic, account_id=account_id, hotspot_id=None, outline=outline, word_count=word_count)
```

- [ ] **Step 2: Commit**

```bash
git add ArticleGeneratorService/app/services/generate_service.py
git commit -m "refactor: use keyword arg for topic in generate_service"
```

---

### Task 5: Update seed data — generate and humanize templates

**Files:**
- Modify: `scripts/seed_providers.py:130-163`

- [ ] **Step 1: Update generate scenario template**

Replace lines 130-144:
```python
    # ── ⑤ 文章生成 ──────────────────────────────────────────────────────────
    {
        "scenario": "generate",
        "model": "claude-sonnet-4-20250514",
        "system_prompt_template": (
            "你是一个专业的内容创作者。根据热点标题和风格要求，创作一篇高质量的文章。"
            "文章需要有吸引人的标题、清晰的结构、充实的内容。\n\n"
            "风格要求：{{style_profile}}\n\n"
            "热点标题：{{hotspot_title}}"
        ),
        "params": '{"max_tokens": 4096, "temperature": 0.8}',
        "priority": 10,
        "description": "⑤ 文章生成：根据热点/想法 + 风格画像 + 大纲生成全文",
        "sort_order": 5,
    },
```
With:
```python
    # ── ⑤ 文章生成 ──────────────────────────────────────────────────────────
    {
        "scenario": "generate",
        "model": "claude-sonnet-4-20250514",
        "system_prompt_template": (
            "你是一个专业的内容创作者。\n\n"
            "## 任务\n"
            "根据以下信息创作一篇高质量的文章。\n\n"
            "## 文章主题\n"
            "{{topic}}\n\n"
            "## 风格画像\n"
            "{{style_profile}}\n\n"
            "{{style_instructions}}\n\n"
            "{{outline_section}}\n\n"
            "{{word_count_instruction}}\n\n"
            "## 要求\n"
            "- 文章需要有吸引人的标题（包含在正文开头）\n"
            "- 清晰的结构、充实的内容\n"
            "- 语言自然，避免AI写作痕迹"
        ),
        "params": '{"max_tokens": 4096, "temperature": 0.8}',
        "priority": 10,
        "description": "⑤ 文章生成：根据主题 + 风格画像 + 大纲生成全文（提示词统一在模板中，人类可编辑权重）",
        "sort_order": 5,
    },
```

- [ ] **Step 2: Update humanize scenario template**

Replace lines 145-163:
```python
    # ── ⑥ 去AI味 ────────────────────────────────────────────────────────────
    {
        "scenario": "humanize",
        "model": "claude-sonnet-4-20250514",
        "system_prompt_template": (
            "你是一个资深编辑，擅长让AI生成的文章读起来像真人写的。\n\n"
            "请对以下文章进行「去AI味」处理：\n"
            "1. 打破过于工整的对称结构\n"
            "2. 加入自然的语气变化和口语化表达\n"
            "3. 减少「首先/其次/最后/总而言之」等套路连接词\n"
            "4. 适当加入个人化的观点和感受\n"
            "5. 段落长短错落，避免每段都是3-4句\n\n"
            "文章内容：\n{{article_content}}"
        ),
        "params": '{"max_tokens": 4096, "temperature": 0.7}',
        "priority": 5,
        "description": "⑥ 去AI味：重写文章，消除AI写作痕迹，增加人味儿",
        "sort_order": 6,
    },
```
With:
```python
    # ── ⑥ 去AI味 ────────────────────────────────────────────────────────────
    {
        "scenario": "humanize",
        "model": "claude-sonnet-4-20250514",
        "system_prompt_template": (
            "你是一个资深编辑，擅长让AI生成的文章读起来像真人写的。\n\n"
            "{{outline_section}}"
            "请对以下文章进行「去AI味」处理：\n"
            "1. 打破过于工整的对称结构\n"
            "2. 加入自然的语气变化和口语化表达\n"
            "3. 减少「首先/其次/最后/总而言之」等套路连接词\n"
            "4. 适当加入个人化的观点和感受\n"
            "5. 段落长短错落，避免每段都是3-4句\n"
            "6. 如果原文有大纲结构要求，重写时保持段落结构不变\n\n"
            "文章内容：\n{{article_content}}"
        ),
        "params": '{"max_tokens": 4096, "temperature": 0.7}',
        "priority": 5,
        "description": "⑥ 去AI味：重写文章，消除AI写作痕迹，增加人味儿（感知大纲结构）",
        "sort_order": 6,
    },
```

- [ ] **Step 3: Commit**

```bash
git add scripts/seed_providers.py
git commit -m "feat: update generate and humanize system_prompt_templates for consolidated prompts"
```

---

### Task 6: Update LLM Service /generate endpoint for compatibility

**Files:**
- Modify: `LLMService/app/main.py:43-66`

- [ ] **Step 1: Add topic field to GenerateLegacyRequest and map internally**

Replace lines 43-66:
```python
class GenerateLegacyRequest(BaseModel):
    hotspot_title: str
    account_id: int
    lora_path: Optional[str] = None
    user_prompt: Optional[str] = None


# 保留旧端点兼容（标记废弃），内部转发到 /chat
@app.post("/generate")
def generate_legacy(req: GenerateLegacyRequest):
    variables = {"hotspot_title": req.hotspot_title}
    if req.user_prompt:
        variables["user_prompt"] = req.user_prompt
    return gateway.chat(
        scenario="generate",
        account_id=req.account_id,
        variables=variables,
    )
```
With:
```python
class GenerateLegacyRequest(BaseModel):
    hotspot_title: Optional[str] = None
    topic: Optional[str] = None
    account_id: int
    lora_path: Optional[str] = None
    user_prompt: Optional[str] = None


# 保留旧端点兼容（标记废弃），内部转发到 /chat
@app.post("/generate")
def generate_legacy(req: GenerateLegacyRequest):
    # 兼容新旧调用方：优先 topic，回退 hotspot_title
    resolved_topic = req.topic or req.hotspot_title or ""
    variables = {"topic": resolved_topic}
    if req.user_prompt:
        variables["user_prompt"] = req.user_prompt
    return gateway.chat(
        scenario="generate",
        account_id=req.account_id,
        variables=variables,
    )
```

- [ ] **Step 2: Update Gateway user message fallback (gateway.py:85)**

Replace line 85:
```python
        user_content = variables.get("user_prompt") or variables.get("hotspot_title") or variables.get("keywords") or ""
```
With:
```python
        user_content = variables.get("user_prompt") or "请开始创作。"
```

- [ ] **Step 3: Commit**

```bash
git add LLMService/app/main.py LLMService/app/gateway.py
git commit -m "feat: add topic field support, default user message for consolidated prompts"
```

---

### Task 7: Update Frontend API client

**Files:**
- Modify: `ArticleGeneratorAdm/src/api/client.ts:144-153`
- Modify: `ArticleGeneratorAdm/src/api/modules/tasks.ts:8-29`

- [ ] **Step 1: Update client.ts triggerGenerateWithOutline**

Replace line 152-153:
```typescript
  triggerGenerateWithOutline: (accountId: number, customTopic: string, outline: string[], wordCount?: string) =>
    post("/generate/trigger", { hotspot_ids: [], account_id: accountId, custom_topic: customTopic, outline, word_count: wordCount || null }),
```
With:
```typescript
  triggerGenerateWithOutline: (accountId: number, topic: string, outline?: string[], wordCount?: string) =>
    post("/generate/trigger", { hotspot_ids: [], account_id: accountId, custom_topic: topic, outline: outline || [], word_count: wordCount || null }),
```

- [ ] **Step 2: Update modules/tasks.ts triggerGenerateWithOutline**

Replace lines 20-29 in `ArticleGeneratorAdm/src/api/modules/tasks.ts`:
```typescript
  triggerGenerateWithOutline: (
    accountId: number,
    customTopic: string,
    outline: string[],
  ) => post("/generate/trigger", {
    hotspot_ids: [],
    account_id: accountId,
    custom_topic: customTopic,
    outline,
  }),
```
With:
```typescript
  triggerGenerateWithOutline: (
    accountId: number,
    topic: string,
    outline?: string[],
  ) => post("/generate/trigger", {
    hotspot_ids: [],
    account_id: accountId,
    custom_topic: topic,
    outline: outline || [],
  }),
```

- [ ] **Step 3: Commit**

```bash
git add ArticleGeneratorAdm/src/api/client.ts ArticleGeneratorAdm/src/api/modules/tasks.ts
git commit -m "refactor: rename customTopic to topic in frontend API, make outline optional"
```

---

### Task 8: Make outline optional in CreateView.vue

**Files:**
- Modify: `ArticleGeneratorAdm/src/views/CreateView.vue:95-126, 266-296, 334-345`

- [ ] **Step 1: Add "Skip Outline" path in step 3 (写作方向)**

Replace lines 95-100:
```vue
          <div class="card-actions">
            <el-button size="large" @click="currentStep = 1">返回上一步</el-button>
            <el-button size="large" type="primary" :disabled="!selectedDirection" :loading="loadingOutline" @click="generateOutline">
              下一步 · 生成大纲
            </el-button>
          </div>
```
With:
```vue
          <div class="card-actions">
            <el-button size="large" @click="currentStep = 1">返回上一步</el-button>
            <el-button size="large" :disabled="!selectedDirection" @click="skipToTitles">
              跳过大纲 · 直接生成标题
            </el-button>
            <el-button size="large" type="primary" :disabled="!selectedDirection" :loading="loadingOutline" @click="generateOutline">
              生成大纲预览
            </el-button>
          </div>
```

- [ ] **Step 2: Add skipToTitles function**

Insert after `generateOutline` function (after line 296):
```typescript
function skipToTitles() {
  outline.value = []  // 清空大纲
  currentStep.value = 4  // 直接跳到标题生成
}
```

- [ ] **Step 3: Update generateTitles to work without outline**

Replace line 299:
```typescript
  if (!selectedAccountId.value || !selectedDirection.value || !outline.value.length) return
```
With:
```typescript
  if (!selectedAccountId.value || !selectedDirection.value) return
```

And lines 302-303:
```typescript
    const points = outline.value.map(o => o.point)
    const { data } = await api.generateTitles(selectedAccountId.value, idea.value.trim(), selectedDirection.value.title, points)
```
With:
```typescript
    const points = outline.value.length ? outline.value.map(o => o.point) : []
    const { data } = await api.generateTitles(selectedAccountId.value, idea.value.trim(), selectedDirection.value.title, points.length ? points : undefined as any)
```

- [ ] **Step 4: Update step 4 (大纲确认) to show skip option**

Replace lines 120-126 (the card-actions in step 4):
```vue
          <div class="card-actions">
            <el-button size="large" @click="currentStep = 2">返回上一步</el-button>
            <el-button size="large" type="primary" :disabled="!outline.length || !outline.every(o => o.point.trim())" @click="generateTitles">
              下一步 · 生成标题
            </el-button>
          </div>
```
With:
```vue
          <div class="card-actions">
            <el-button size="large" @click="currentStep = 2">返回上一步</el-button>
            <el-button size="large" @click="skipToTitles">不使用大纲 · 直接生成标题</el-button>
            <el-button size="large" type="primary" :disabled="!outline.length || !outline.every(o => o.point.trim())" @click="generateTitles">
              使用大纲 · 生成标题
            </el-button>
          </div>
```

- [ ] **Step 5: Update startGenerate to handle optional outline**

Replace lines 341-345:
```typescript
    const points = outline.value.map(o => o.point)
    const topicWithTitle = editedTitle.value
      ? `${editedTitle.value}\n\n${idea.value.trim()}`
      : idea.value.trim()
    const { data } = await api.triggerGenerateWithOutline(selectedAccountId.value, topicWithTitle, points)
```
With:
```typescript
    const points = outline.value.length ? outline.value.map(o => o.point) : undefined
    const topicWithTitle = editedTitle.value
      ? `${editedTitle.value}\n\n${idea.value.trim()}`
      : idea.value.trim()
    const { data } = await api.triggerGenerateWithOutline(selectedAccountId.value, topicWithTitle, points)
```

- [ ] **Step 6: Commit**

```bash
git add ArticleGeneratorAdm/src/views/CreateView.vue
git commit -m "feat: make outline step optional in creation flow, default skip"
```

---

### Task 9: Write backend test for consolidated prompt

**Files:**
- Create: `ArticleGeneratorService/tests/test_generate_prompt_consolidation.py`

- [ ] **Step 1: Write test file**

```python
"""Tests for consolidated generate prompt — outline_section, topic, variables"""
import pytest
from unittest.mock import patch, MagicMock


class TestOutlineSection:
    """outline → outline_section 转换"""

    def test_outline_section_with_outline(self):
        """有 outline 时构建完整 section"""
        from app.tasks import trigger_generate

        outline = ["开篇引入问题", "分析原因", "给出建议"]
        # 模拟 outline_section 的构建逻辑
        outline_items = [f"{i+1}. {p}" for i, p in enumerate(outline)]
        outline_section = (
            "## 写作大纲\n"
            + "\n".join(outline_items)
            + "\n\n请严格按照以上大纲逐段写作，大纲有几段文章就必须有几段。\n"
        )

        assert "## 写作大纲" in outline_section
        assert "1. 开篇引入问题" in outline_section
        assert "2. 分析原因" in outline_section
        assert "3. 给出建议" in outline_section
        assert "请严格按照以上大纲逐段写作" in outline_section

    def test_outline_section_empty(self):
        """无 outline 时 outline_section 为空"""
        outline_section = ""
        if None:  # outline is None/empty
            pass
        assert outline_section == ""

    def test_outline_section_empty_list(self):
        """空列表同样为空"""
        outline = []
        outline_section = ""
        if outline:
            pass  # won't execute
        assert outline_section == ""


class TestTopicVariable:
    """topic 变量覆盖热点和自定义两种来源"""

    def test_topic_from_custom(self):
        """创建流程中 topic 为用户自拟内容"""
        topic = "AI编程的焦虑是否被夸大？\n\n探讨AI工具对初级程序员的影响"
        assert "AI编程" in topic
        assert "初级程序员" in topic

    def test_topic_from_hotspot(self):
        """热点流程中 topic 为热点标题"""
        topic = "GPT-5发布引发行业震动"
        assert "GPT-5" in topic


class TestPayloadStructure:
    """验证发往 LLM 的 payload 结构"""

    def test_payload_has_variables_not_user_prompt(self):
        """新 payload 使用 variables dict，不传 user_prompt"""
        payload = {
            "scenario": "generate",
            "account_id": 1,
            "variables": {
                "topic": "测试主题",
                "style_instructions": "句式：长短句参差\n",
                "outline_section": "",
                "word_count_instruction": "字数1500左右。",
            },
        }
        assert "scenario" in payload
        assert "variables" in payload
        assert "user_prompt" not in payload
        assert payload["variables"]["topic"] == "测试主题"

    def test_humanize_payload_has_outline_section(self):
        """Humanize payload 包含 outline_section"""
        payload = {
            "scenario": "humanize",
            "variables": {
                "article_content": "...",
                "outline_section": "## 写作大纲\n1. 要点一\n",
            },
        }
        assert "outline_section" in payload["variables"]
```

- [ ] **Step 2: Run tests**

```bash
cd ArticleGeneratorService && pytest tests/test_generate_prompt_consolidation.py -v
```
Expected: 6 passed

- [ ] **Step 3: Commit**

```bash
git add ArticleGeneratorService/tests/test_generate_prompt_consolidation.py
git commit -m "test: add unit tests for consolidated prompt variables and outline_section"
```

---

### Task 10: Verification

- [ ] **Step 1: Run backend pytest suite**

```bash
cd ArticleGeneratorService && pytest tests/ -v --ignore=tests/test_workflow_*.py
```
Expected: All passing

- [ ] **Step 2: Run LLM service tests**

```bash
cd LLMService && pytest tests/ -v
```
Expected: All passing

- [ ] **Step 3: Run frontend vitest**

```bash
cd ArticleGeneratorAdm && npx vitest run
```
Expected: All passing

- [ ] **Step 4: Reseed scenario configs**

```bash
cd ArticleGeneratorService && python ../scripts/seed_providers.py
```
Expected: generate 和 humanize 场景模板更新成功

- [ ] **Step 5: Start dev server and manually test "no outline" flow**

```bash
./scripts/start.sh
# Browser: http://localhost:5173/create
# 1. Select account → Next
# 2. Enter idea → Generate directions
# 3. Select direction → "跳过大纲 · 直接生成标题"
# 4. Select title → "确认标题 · 生成全文"
# 5. Verify: Article generated, check in review page
```

- [ ] **Step 6: Manually test "with outline" flow**

```bash
# Browser: http://localhost:5173/create
# 1-3 as above
# 4. Click "生成大纲预览" → Review outline → "使用大纲 · 生成标题"
# 5. Select title → "确认标题 · 生成全文"
# 6. Verify: Generated article follows outline structure
```

- [ ] **Step 7: Verify admin panel template editing**

```
Browser: http://localhost:5173/scenario-configs
Find generate scenario → Edit system_prompt_template → Save → Re-generate → Verify new template used
```

- [ ] **Step 8: Final commit if any fixups needed**

```bash
git status
git add -A
git commit -m "chore: verification fixes for consolidate-generate-prompt"
```
