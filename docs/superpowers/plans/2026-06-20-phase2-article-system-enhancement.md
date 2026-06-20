# Phase 2 Article System Enhancement Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix the humanize chain failure (P0), add article title field support across the stack (P1), extend unified task center for all task types (P1), add title generation step to creation wizard (P2), and add description/sort_order to scenario config schemas + seed data (P2).

**Architecture:** Multi-service changes across ArticleGeneratorService (FastAPI backend), ArticleGeneratorAdm (Vue 3 frontend), and SQLite DB. All changes are additive — no breaking changes. Backend schema changes follow the existing Pydantic pattern; frontend changes follow the existing Vue 3 + Element Plus + API modules pattern.

**Tech Stack:** Python 3 + FastAPI + SQLAlchemy + Pydantic + Celery | Vue 3 + TypeScript + Element Plus + Vite | SQLite

---

## File Structure

| File | Action | Purpose |
|------|--------|---------|
| `ArticleGeneratorService/app/schemas.py` | Modify | Add `title` to ArticleBase, `description`/`sort_order` to ScenarioConfigBase |
| `ArticleGeneratorService/app/api/tasks.py` | Modify | Extend unified endpoint with Celery fallback for non-DB task types |
| `scripts/seed_providers.py` | Modify | Add humanize/direction/outline/title scenarios, idempotent updates with descriptions |
| `ArticleGeneratorDatabase/migrations/` | Create + Run | Migration 014 for scenario_configs.description/sort_order |
| `ArticleGeneratorAdm/src/api/types.ts` | Modify | Add `title` to Article, `description`/`sort_order` to ScenarioConfig, `task_type`/`target`/`account_name`/`extra_info` to UnifiedTaskItem |
| `ArticleGeneratorAdm/src/api/client.ts` | Modify | Fix `generateTitles` return type (was `{titles:[]}`, is `{task_id,status,message}`) |
| `ArticleGeneratorAdm/src/views/CreateView.vue` | Modify | Insert title generation step between outline and generation (5→6 steps) |

---

### Task 1: Backup Database + Apply Migrations

**Files:**
- Create: `ArticleGeneratorDatabase/migrations/014_add_scenario_config_meta.sql`
- Modify: SQLite DB at `article_generator.db` (run ALTER TABLE)

**Background:** Two migrations are missing from the actual DB: `articles.title` (migration 007 exists but wasn't applied) and `scenario_configs.(description|sort_order)` (no migration SQL file exists). The SQLAlchemy models already have these columns.

- [ ] **Step 1: Backup the SQLite database**

```bash
cp /Users/linsywu/Documents/AI-space/ArticleGenerator/article_generator.db /Users/linsywu/Documents/AI-space/ArticleGenerator/article_generator.db.bak
```

Expected: `ls -la article_generator.db.bak` shows file exists, same size as original

- [ ] **Step 2: Apply migration 007 (articles.title)**

```bash
sqlite3 /Users/linsywu/Documents/AI-space/ArticleGenerator/article_generator.db "ALTER TABLE articles ADD COLUMN title VARCHAR(200);"
```
Expected: no error output

Verify: `sqlite3 ... "PRAGMA table_info(articles);" | grep title` → shows `title|VARCHAR(200)|...`

- [ ] **Step 3: Create migration 014 for scenario_configs metadata**

Create file `ArticleGeneratorDatabase/migrations/014_add_scenario_config_meta.sql`:

```sql
-- 014: Add description and sort_order to scenario_configs
ALTER TABLE scenario_configs ADD COLUMN description TEXT;
ALTER TABLE scenario_configs ADD COLUMN sort_order INTEGER DEFAULT 0;
```

- [ ] **Step 4: Apply migration 014**

```bash
sqlite3 /Users/linsywu/Documents/AI-space/ArticleGenerator/article_generator.db < /Users/linsywu/Documents/AI-space/ArticleGenerator/ArticleGeneratorDatabase/migrations/014_add_scenario_config_meta.sql
```
Expected: no error output

Verify: `sqlite3 ... "PRAGMA table_info(scenario_configs);" | grep -E "description|sort_order"` → two rows

- [ ] **Step 5: Commit**

```bash
git add ArticleGeneratorDatabase/migrations/014_add_scenario_config_meta.sql
git commit -m "feat: apply article title + scenario config meta migrations"
```

---

### Task 2: Update Seed Script with Missing Scenarios + Descriptions

**Files:**
- Modify: `scripts/seed_providers.py` (full rewrite of seed logic)

**Background:** The seed script currently deletes all rows and inserts 5 scenarios (generate, refine, distill, quality_review, compliance_review). It's missing humanize, direction, outline, title. It also doesn't set description/sort_order. Not idempotent — deletes all data on each run.

- [ ] **Step 1: Rewrite seed_providers.py with idempotent upsert and all 9 scenarios**

Replace `scripts/seed_providers.py` with a version that:
1. Uses UPSERT pattern: check existence by scenario name, UPDATE if exists, INSERT if not
2. Preserves the existing Provider (update if exists, insert if not) instead of DELETE + INSERT
3. Adds 4 new scenarios: `humanize`, `direction`, `outline`, `title` with appropriate system prompts
4. Sets `description` and `sort_order` for all 9 scenarios according to the plan:
   - distill: sort_order=1, direction: sort_order=2, outline: sort_order=3, title: sort_order=4, generate: sort_order=5, humanize: sort_order=6, quality_review: sort_order=7, compliance_review: sort_order=8, refine: sort_order=9
5. Keeps existing Provider API key from env var or the existing DB value

The key structural change: replace `db.query(ScenarioConfig).delete()` + `db.query(Provider).delete()` with per-scenario existence checks using `db.query(ScenarioConfig).filter(ScenarioConfig.scenario == name).first()`. Update if found, insert if not.

**Humanize scenario system_prompt_template** (the critical P0 fix):
```
你是一个资深编辑，擅长让AI生成的文章读起来像真人写的。

请对以下文章进行「去AI味」处理：
1. 打破过于工整的对称结构
2. 加入自然的语气变化和口语化表达
3. 减少「首先/其次/最后/总而言之」等套路连接词
4. 适当加入个人化的观点和感受
5. 段落长短错落，避免每段都是3-4句

文章内容：
{{article_content}}
```

**Direction scenario system_prompt_template**:
```
你是一个专业的内容策划。根据给定的想法和账号写作风格，生成3-5个不同的写作方向。

每个方向应该是一个不同的切入角度，用一句话描述。

风格要求：{{style_profile}}
想法：{{idea}}
```

**Outline scenario system_prompt_template**:
```
你是一个专业的内容策划。根据想法、写作方向和账号风格，生成5-8个要点的文章大纲。

每个要点用一句话概括核心内容。

风格要求：{{style_profile}}
想法：{{idea}}
方向：{{direction}}
```

**Title scenario system_prompt_template**:
```
你是一个专业的内容编辑。根据想法、写作方向和大纲，生成3-5个吸引人的文章标题。

标题要求：
1. 简洁有力，15字以内为佳
2. 能准确传达文章核心观点
3. 符合账号的写作风格
4. 有一定吸引力但不标题党

风格要求：{{style_profile}}
想法：{{idea}}
方向：{{direction}}
大纲：{{outline}}
```

**For full seed_providers.py code with all 9 scenarios**, reference the existing patterns in the current file — each scenario follows the same dict structure with `scenario`, `model`, `system_prompt_template`, `params`, `priority`, `description`, `sort_order`.

- [ ] **Step 2: Run the updated seed script**

```bash
cd /Users/linsywu/Documents/AI-space/ArticleGenerator && python3 scripts/seed_providers.py
```
Expected: "Done: 1 provider + 9 scenario configs seeded/updated."

- [ ] **Step 3: Verify all 9 scenarios exist in DB**

```bash
sqlite3 /Users/linsywu/Documents/AI-space/ArticleGenerator/article_generator.db "SELECT scenario, description, sort_order FROM scenario_configs ORDER BY sort_order;"
```
Expected: 9 rows — distill(1), direction(2), outline(3), title(4), generate(5), humanize(6), quality_review(7), compliance_review(8), refine(9)

- [ ] **Step 4: Commit**

```bash
git add scripts/seed_providers.py
git commit -m "feat: seed all 9 scenario configs with descriptions and sort_order, idempotent upsert"
```

---

### Task 3: Add title to Article Pydantic Schemas

**Files:**
- Modify: `ArticleGeneratorService/app/schemas.py:155-157` (ArticleBase class)

- [ ] **Step 1: Add title to ArticleBase**

In `ArticleGeneratorService/app/schemas.py`, change `ArticleBase` from:

```python
class ArticleBase(BaseModel):
    content: str
    status: str = "pending_review"
```

To:

```python
class ArticleBase(BaseModel):
    content: str
    title: Optional[str] = None
    status: str = "pending_review"
```

- [ ] **Step 2: Verify backend imports**

```bash
cd ArticleGeneratorService && python -c "from app.schemas import ArticleBase; print('fields:', list(ArticleBase.model_fields.keys()))"
```
Expected: `fields: ['content', 'title', 'status']`

- [ ] **Step 3: Commit**

```bash
git add ArticleGeneratorService/app/schemas.py
git commit -m "feat: add title to ArticleBase Pydantic schema"
```

---

### Task 4: Add description/sort_order to ScenarioConfig Pydantic Schemas

**Files:**
- Modify: `ArticleGeneratorService/app/schemas.py:285-301` (ScenarioConfigBase + ScenarioConfigUpdate)

- [ ] **Step 1: Add description and sort_order to ScenarioConfigBase**

In `ScenarioConfigBase`, add two fields before `enabled`:

```python
    description: Optional[str] = None
    sort_order: Optional[int] = None
```

- [ ] **Step 2: Add description and sort_order to ScenarioConfigUpdate**

In `ScenarioConfigUpdate`, add:

```python
    description: Optional[str] = None
    sort_order: Optional[int] = None
```

- [ ] **Step 3: Verify backend imports**

```bash
cd ArticleGeneratorService && python -c "from app.schemas import ScenarioConfigBase; print('has description:', 'description' in ScenarioConfigBase.model_fields)"
```
Expected: `has description: True`

- [ ] **Step 4: Commit**

```bash
git add ArticleGeneratorService/app/schemas.py
git commit -m "feat: add description and sort_order to ScenarioConfig Pydantic schemas"
```

---

### Task 5: Extend Unified Task Endpoint with Celery Fallback

**Files:**
- Modify: `ArticleGeneratorService/app/api/tasks.py`

**Background:** Non-generate/refine task types (humanize, distill, direction, outline, title, quality_review, compliance_review) only exist in Celery's result backend. Add Celery inspection to surface these in the unified response.

- [ ] **Step 1: Add Celery inspection to the unified endpoint**

At the top of `app/api/tasks.py`, add imports:

```python
from celery.result import AsyncResult
from ..tasks import celery_app as _celery_app
```

Then, in the `query_unified_tasks` function, before the `return` statement (before line 137), add logic to:
1. Call `_celery_app.control.inspect()` to get active/reserved tasks
2. Filter for `app.tasks.trigger_*` task names
3. For each Celery task not already in the DB-tracked list, create a `task_item` dict with inferred `task_type`
4. Wrap in try/except — on Celery failure, log warning and continue with DB-only results
5. Helper function `_infer_task_type(task_id)` extracts task type from Celery task name (e.g., `app.tasks.trigger_humanize` → `humanize`)
6. Helper function `_celery_target(task_type)` returns a readable Chinese label for each type

**Key additions to the response loop:**

```python
# After the DB UNION query loop, add Celery fallback:
CELERY_TASK_TYPES = {"humanize", "distill", "direction", "outline", "title", "quality_review", "compliance_review"}

try:
    inspector = _celery_app.control.inspect()
    active_tasks = inspector.active() or {}
    reserved_tasks = inspector.reserved() or {}
    
    celery_task_ids = set()
    for worker_tasks in list(active_tasks.values()) + list(reserved_tasks.values()):
        for t in worker_tasks:
            if t.get("name", "").startswith("app.tasks.trigger_"):
                celery_task_ids.add(t["id"])
    
    for task_id in celery_task_ids:
        if any(t["task_id"] == task_id for t in tasks):
            continue
        async_result = AsyncResult(task_id, app=_celery_app)
        task_type = _infer_task_type(task_id)
        if task_type not in CELERY_TASK_TYPES:
            continue
        
        status = "running" if async_result.state in ("STARTED", "PENDING") else async_result.state.lower()
        if status_list and status not in status_list:
            continue
        
        task_item = {
            "task_id": task_id,
            "task_type": task_type,
            "status": status,
            "target": _celery_target(task_type) or "未知任务",
            "article_id": None,
            "account_name": None,
            "extra_info": None,
            "error_message": str(async_result.result) if async_result.state == "FAILURE" else None,
            "created_at": None,
            "updated_at": None,
        }
        tasks.append(task_item)
        if status == "running": running_count += 1
        elif status == "pending": pending_count += 1
except Exception as e:
    import logging
    logging.getLogger(__name__).warning(f"Celery inspection failed: {e}")
```

- [ ] **Step 2: Verify backend imports**

```bash
cd ArticleGeneratorService && python -c "from app.api.tasks import router; print('OK')"
```
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add ArticleGeneratorService/app/api/tasks.py
git commit -m "feat: extend unified task endpoint with Celery fallback for non-DB task types"
```

---

### Task 6: Fix Frontend TypeScript Interfaces

**Files:**
- Modify: `ArticleGeneratorAdm/src/api/types.ts`
- Modify: `ArticleGeneratorAdm/src/api/client.ts` (generateTitles return type fix)

- [ ] **Step 1: Add title to Article interface**

In `src/api/types.ts`, add `title?: string;` after `account_id: number;` and before `content: string;` in the `Article` interface.

- [ ] **Step 2: Add description and sort_order to ScenarioConfig interface**

In the `ScenarioConfig` interface, add after `priority: number;`:
```typescript
  description?: string;
  sort_order?: number;
```

- [ ] **Step 3: Fix UnifiedTaskItem to match actual backend response**

Replace the old `UnifiedTaskItem` interface (which has `id`, `hotspot_id`, `account_id`, `hotspot`, `account` fields that the backend doesn't return) with one that matches the actual API response:

```typescript
export interface UnifiedTaskItem {
  task_id: string;
  task_type: string;
  status: string;
  target: string;
  article_id: number | null;
  account_name?: string;
  extra_info?: string;
  error_message: string | null;
  created_at: string;
  updated_at?: string;
}
```

- [ ] **Step 4: Fix generateTitles return type in client.ts**

In `src/api/client.ts`, the `generateTitles` method currently returns `{ titles: string[] }` but the backend returns `{ task_id, status, message }`. Fix the return type:

```typescript
  generateTitles: (accountId: number, idea: string, direction: string, outline: string[]) =>
    post<{ task_id: string; status: string; message: string }>("/generate/titles", { account_id: accountId, idea, direction, outline }),
```

- [ ] **Step 5: Verify frontend builds**

```bash
cd ArticleGeneratorAdm && npm run build 2>&1 | tail -5
```
Expected: build succeeds, no type errors

- [ ] **Step 6: Commit**

```bash
git add ArticleGeneratorAdm/src/api/types.ts ArticleGeneratorAdm/src/api/client.ts
git commit -m "fix: add missing fields to Article, ScenarioConfig, UnifiedTaskItem types; fix generateTitles return type"
```

---

### Task 7: Add Title Generation Step to CreateView

**Files:**
- Modify: `ArticleGeneratorAdm/src/views/CreateView.vue`

**Background:** Backend `POST /generate/titles` + `trigger_title_generation` already exist. CreateView has 5 steps. Insert title generation as step 5 (6 steps total) between outline confirmation and full-text generation. Uses same task+result polling pattern as directions/outline.

- [ ] **Step 1: Update steps array**

```typescript
const steps = ['选择账号', '输入想法', '写作方向', '确认大纲', '生成标题', '生成全文']
```

- [ ] **Step 2: Add title state variables**

After `const generatedArticle = ref('')`:
```typescript
const titles = ref<string[]>([])
const selectedTitle = ref('')
const editedTitle = ref('')
const loadingTitles = ref(false)
```

- [ ] **Step 3: Add generateTitles function**

Add after `generateOutline()` and before `startGenerate()`. Pattern matches `generateDirections`/`generateOutline`:
1. Call `api.generateTitles(accountId, idea, direction, outlinePoints)` → get `task_id`
2. Poll `api.getTaskResult(taskId)` every 2s, max 30 attempts
3. On success: `titles.value = result.titles`, set `selectedTitle`/`editedTitle` to first title, advance to `currentStep.value = 4`
4. On failure: `ElMessage.error(...)`
5. `finally: loadingTitles.value = false`

- [ ] **Step 4: Update startGenerate to use selected title**

In `startGenerate()`, prepend the selected title to `custom_topic`:
```typescript
const topicWithTitle = editedTitle.value
  ? `${editedTitle.value}\n\n${idea.value.trim()}`
  : idea.value.trim()
```
And change `currentStep.value = 4` to `currentStep.value = 5`.

- [ ] **Step 5: Insert title step template**

Add between step 4 (`currentStep === 3`) and the final generation step. The template shows:
1. A card header: "05 选择文章标题"
2. A `titles-grid` of clickable title cards (radio-like selection)
3. An edit area (`el-input`) for modifying the selected title
4. Action buttons: "返回修改大纲" and "确认标题 · 生成全文"

- [ ] **Step 6: Fix step numbering in final generation step**

Change the old step 5 (now step 6):
- Key: `key="step5"` → `key="step6"`
- Card number: `05` → `06`
- Return button: `@click="currentStep = 3"` → `@click="currentStep = 4"` (back to title step)

- [ ] **Step 7: Fix step line count**

In the step indicator template, change `<span v-if="i < 4"` to `<span v-if="i < 5"` to show lines between all 6 steps.

- [ ] **Step 8: Add title card styles**

Add styles for `.titles-grid`, `.title-card`, `.title-card.selected`, `.title-index`, `.title-text`, `.title-check`, `.title-edit-area`, `.title-edit-label` — following existing style patterns (same color vars, same border/hover approach as `.direction-card`).

- [ ] **Step 9: Verify frontend builds**

```bash
cd ArticleGeneratorAdm && npm run build 2>&1 | tail -5
```
Expected: build succeeds

- [ ] **Step 10: Commit**

```bash
git add ArticleGeneratorAdm/src/views/CreateView.vue
git commit -m "feat: add title generation step to CreateView (5→6 steps)"
```

---

### Task 8: End-to-End Verification

- [ ] **Step 1: Start backend and verify API responses**

```bash
cd ArticleGeneratorService && uvicorn app.main:app --host 0.0.0.0 --port 8000 &
sleep 3
```

**Verify article title field:**
```bash
curl -s http://localhost:8000/api/articles?page=1\&page_size=1 | python3 -m json.tool | head -20
```
Expected: response data items include `"title"` field

**Verify scenario configs:**
```bash
curl -s http://localhost:8000/api/scenario-configs | python3 -c "import json,sys; d=json.load(sys.stdin); [print(f'{c[\"scenario\"]}: sort={c[\"sort_order\"]} desc={c.get(\"description\",\"N/A\")[:20]}') for c in d]"
```
Expected: 9 scenarios with sort_order 1-9 and descriptions

**Verify unified tasks:**
```bash
curl -s "http://localhost:8000/api/tasks/unified?status=running,pending&limit=10" | python3 -m json.tool | head -15
```
Expected: `tasks` array with `running_count`, `pending_count`, `completed_count`

- [ ] **Step 2: Start frontend and verify pages in browser**

```bash
cd ArticleGeneratorAdm && npm run dev &
sleep 5
```

Visit these pages and check console (F12 → Console) for errors:

| URL | Check |
|-----|-------|
| `/scenario-configs` | "顺序", "说明", "提示词预览" columns display |
| `/tasks-center` | Header badges, no missing-prop errors |
| `/create` | 6-step indicator, walk through all steps |
| `/review` | Article title column works |

- [ ] **Step 3: Cleanup**

```bash
kill %1 %2 2>/dev/null
```

- [ ] **Step 4: Success checklist**

- [x] DB has `articles.title` column
- [x] DB has `scenario_configs.description` and `sort_order` columns
- [x] DB has all 9 scenario configs with descriptions and sort_orders
- [x] API returns `description`/`sort_order` in scenario-configs response
- [x] API returns `title` in articles response
- [x] Frontend types match backend response fields
- [x] CreateView has 6 steps with title generation
- [x] No console errors on affected pages
