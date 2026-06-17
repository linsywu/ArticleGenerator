# P1 架构与性能修正 — 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 后端分层解耦（Service 层 + 异步化 + Celery 模块化）和前端组件化（共享组件 + hooks + Pinia store）

**Architecture:** T08 新建 Service 层 → T07 移除同步阻塞 → T09 拆分 Celery → T11 前端组件抽取 → T12 Pinia store → T13 输入校验

**Tech Stack:** FastAPI + SQLAlchemy + Celery (后端), Vue 3 + Pinia + Element Plus (前端)

**Specs:** `openspec/changes/p1-architecture-refactor/specs/` (6 specs)
**Design:** `openspec/changes/p1-architecture-refactor/design.md`

---

## Task 1: T08 — 抽取 Service 层

**Files:**
- Create: `ArticleGeneratorService/app/services/__init__.py`
- Create: `ArticleGeneratorService/app/services/generate_service.py`
- Create: `ArticleGeneratorService/app/services/article_service.py`
- Modify: `ArticleGeneratorService/app/api/generate.py`
- Modify: `ArticleGeneratorService/app/api/articles.py`

### Spec: `openspec/changes/p1-architecture-refactor/specs/service-layer/spec.md`

**Architecture Rule:** `api/（路由） → services/（业务） → models/ + database`。Router 函数 ≤30 行。

- [ ] **Step 1: Create `app/services/__init__.py`**

```python
"""业务服务层"""
```

- [ ] **Step 2: Create `app/services/generate_service.py` — generation trigger logic**

Extract hotspot validation + task creation from `api/generate.py:27-64`:

```python
"""生成触发编排服务"""
from typing import List, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException
from ..models import Hotspot, Account, GenerationTask
from ..tasks import trigger_generate


def trigger_generation(
    db: Session,
    hotspot_ids: List[int],
    account_id: int,
    custom_topic: Optional[str] = None,
    outline: Optional[List[str]] = None,
    word_count: Optional[str] = None,
) -> dict:
    """触发生成任务，返回 {message, tasks}"""
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="账号不存在")

    if not hotspot_ids and not custom_topic:
        raise HTTPException(status_code=400, detail="请选择至少一个热点或输入自定义主题")

    task_ids = []

    if custom_topic:
        task = trigger_generate.delay(custom_topic, account_id, hotspot_id=None, outline=outline, word_count=word_count)
        task_ids.append({"topic": custom_topic, "task_id": task.id})
        gt = GenerationTask(task_id=task.id, account_id=account_id, status="pending")
        db.add(gt)
    else:
        for hid in hotspot_ids:
            hotspot = db.query(Hotspot).filter(Hotspot.id == hid).first()
            if not hotspot:
                continue
            task = trigger_generate.delay(hotspot.title, account_id, hid, outline=outline, word_count=word_count)
            task_ids.append({"hotspot_id": hid, "task_id": task.id})
            gt = GenerationTask(task_id=task.id, hotspot_id=hid, account_id=account_id, status="pending")
            db.add(gt)

    db.commit()
    return {"message": "任务已提交", "tasks": task_ids}
```

- [ ] **Step 3: Create `app/services/article_service.py` — article status machine**

```python
"""文章状态管理服务"""
from sqlalchemy.orm import Session
from fastapi import HTTPException
from ..models import Article


VALID_STATUSES = {"pending_review", "approved", "rejected", "published"}
ALLOWED_TRANSITIONS = {
    "pending_review": {"approved", "rejected"},
    "approved": {"published"},
    "rejected": set(),
    "published": set(),
}


def update_article_status(db: Session, article_id: int, new_status: str) -> Article:
    """更新文章状态，校验状态转换合法性"""
    if new_status not in VALID_STATUSES:
        raise HTTPException(status_code=400, detail=f"无效状态: {new_status}")

    article = db.query(Article).filter(Article.id == article_id).first()
    if not article:
        raise HTTPException(status_code=404, detail="文章不存在")

    allowed = ALLOWED_TRANSITIONS.get(article.status, set())
    if new_status not in allowed and article.status != new_status:
        raise HTTPException(
            status_code=400,
            detail=f"不允许从 {article.status} 转换到 {new_status}",
        )

    article.status = new_status
    db.commit()
    db.refresh(article)
    return article
```

- [ ] **Step 4: Slim down `api/generate.py` — replace trigger body with service call**

Replace the body of `trigger_article_generation` (lines 30-63) with:

```python
from ..services.generate_service import trigger_generation

@router.post("/trigger")
def trigger_article_generation(data: GenerateRequest, db: Session = Depends(get_db)):
    """触发生成：热点 ID 列表 或 自定义主题 + 账号 ID"""
    return trigger_generation(
        db, data.hotspot_ids, data.account_id,
        data.custom_topic, data.outline, data.word_count,
    )
```

Also extract `list_generation_tasks` (lines 129-171) into `generate_service.py` as `list_tasks()` and thin the router to ≤10 lines.

- [ ] **Step 5: Slim down `api/articles.py` — use article_service for status update**

Replace the status update body with:

```python
from ..services.article_service import update_article_status

@router.patch("/{article_id}/status")
def patch_article_status(article_id: int, data: ArticleStatusUpdate, db: Session = Depends(get_db)):
    article = update_article_status(db, article_id, data.status)
    return {"id": article.id, "status": article.status}
```

- [ ] **Step 6: Run tests and verify**

```bash
cd ArticleGeneratorService && pytest tests/ -v --tb=short
# Expected: all 45 tests pass
```

- [ ] **Step 7: Commit**

```bash
git add app/services/ app/api/generate.py app/api/articles.py
git commit -m "feat(T08): 抽取 Service 层 — generate_service + article_service"
```

---

## Task 2: T07 — 移除 Celery 同步阻塞

**Files:**
- Modify: `ArticleGeneratorService/app/api/generate.py`
- (Frontend already supports polling via TaskCenterView)

### Spec: `openspec/changes/p1-architecture-refactor/specs/async-generate-api/spec.md`

**Rule:** 长任务返回 task_id，由前端轮询；禁止 `task.get(timeout=...)` 同步阻塞。

- [ ] **Step 1: Replace `task.get(timeout=120)` with `delay()` in directions endpoint**

In `generate.py` line 200-201, replace:

```python
task = trigger_direction_generation.delay(data.account_id, data.idea.strip(), data.word_count)
result = task.get(timeout=120)

directions = result.get("directions", [])
if not directions:
    raise HTTPException(status_code=500, detail="方向生成失败，请重试")

return DirectionsResponse(directions=[{"id": d.get("id", str(i)), "title": d.get("title", d)} for i, d in enumerate(directions)])
```

With:

```python
task = trigger_direction_generation.delay(data.account_id, data.idea.strip(), data.word_count)
return {"task_id": task.id, "status": "pending", "message": "方向生成已提交"}
```

- [ ] **Step 2: Same for outline endpoint (line 221-222)**

```python
task = trigger_outline_generation.delay(data.account_id, data.idea.strip(), data.direction.strip())
return {"task_id": task.id, "status": "pending", "message": "大纲生成已提交"}
```

- [ ] **Step 3: Same for titles endpoint (line 241-242)**

```python
outline_points = [p for p in data.outline if p.strip()]
task = trigger_title_generation.delay(data.account_id, data.idea.strip(), data.direction.strip(), outline_points)
return {"task_id": task.id, "status": "pending", "message": "标题生成已提交"}
```

- [ ] **Step 4: Update tests — assert 200 with task_id, not result content**

```bash
cd ArticleGeneratorService && pytest tests/test_api_generate.py -v --tb=short
# Fix any tests that assert on task.get() results
# Expected: 10 tests pass
```

- [ ] **Step 5: Verify no sync blocking remains**

```bash
grep -n "task\.get" app/api/generate.py
# Expected: no output
```

- [ ] **Step 6: Commit**

---

## Task 3: T09 — 拆分 Celery tasks

**Files:**
- Create: `ArticleGeneratorService/app/celery_app.py`
- Create: `ArticleGeneratorService/app/tasks/__init__.py`
- Create: `ArticleGeneratorService/app/tasks/generate.py`
- Create: `ArticleGeneratorService/app/tasks/review.py`
- Create: `ArticleGeneratorService/app/tasks/distill.py`
- Create: `ArticleGeneratorService/app/utils/json_parse.py`
- Modify: `ArticleGeneratorService/app/api/generate.py` (update imports)
- Delete: `ArticleGeneratorService/app/tasks.py` (after migration)

### Spec: `openspec/changes/p1-architecture-refactor/specs/celery-module-split/spec.md`

**Rule:** Celery 任务文件命名：`app/celery_app.py` + `app/tasks/*.py`；禁止与 `app/api/tasks.py` 混名。

- [ ] **Step 1: Extract Celery app to `app/celery_app.py`**

```python
"""Celery 应用实例"""
from celery import Celery
from ..config import settings

celery_app = Celery(
    "ArticleGenerator",
    broker=settings.redis_url,
    backend=settings.redis_url,
)
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)
```

- [ ] **Step 2: Extract JSON parsing utility to `app/utils/json_parse.py`**

```python
"""LLM 响应 JSON 解析工具"""
import json
import re
from typing import Any, Optional


def extract_json(text: str) -> Optional[dict]:
    """从 LLM 输出中提取 JSON 对象"""
    # 尝试直接解析
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # 尝试提取 ```json ... ``` 块
    match = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass
    # 尝试提取 { ... } 块
    match = re.search(r'\{.*\}', text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass
    return None
```

- [ ] **Step 3: Move generate tasks to `app/tasks/generate.py`**

Move `trigger_generate`, `trigger_direction_generation`, `trigger_outline_generation`, `trigger_title_generation` and their helpers from `tasks.py`. Import from `celery_app` and `utils/json_parse`.

- [ ] **Step 4: Move review tasks to `app/tasks/review.py`**

Move `trigger_review` and related functions.

- [ ] **Step 5: Move distill tasks to `app/tasks/distill.py`**

Move distillation-related tasks.

- [ ] **Step 6: Update all imports in `api/generate.py`**

```python
# Replace:
# from ..tasks import trigger_generate, celery_app, ...
# With:
from ..celery_app import celery_app
from ..tasks.generate import trigger_generate, trigger_direction_generation, trigger_outline_generation, trigger_title_generation
from ..tasks.review import trigger_review  # if needed
```

- [ ] **Step 7: Delete old `tasks.py` and verify**

```bash
rm app/tasks.py
celery -A app.celery_app worker -l info &
# Verify worker starts and registers all tasks
pytest tests/ -v --tb=short
# Expected: all 45 tests pass
```

- [ ] **Step 8: Commit**

---

## Task 4: T11 — 抽取核心前端组件与 hooks

**Files:**
- Create: `ArticleGeneratorAdm/src/components/ArticleEditorDialog.vue`
- Create: `ArticleGeneratorAdm/src/components/PageHeader.vue`
- Create: `ArticleGeneratorAdm/src/hooks/usePaginatedList.ts`
- Create: `ArticleGeneratorAdm/src/hooks/useActiveTasks.ts`
- Modify: `ArticleGeneratorAdm/src/views/ReviewView.vue`
- Modify: `ArticleGeneratorAdm/src/views/PublishView.vue`
- Modify: `ArticleGeneratorAdm/src/views/CreateView.vue`

### Spec: `openspec/changes/p1-architecture-refactor/specs/shared-frontend-components/spec.md`

- [ ] **Step 1: Create `ArticleEditorDialog.vue`**

Props: `modelValue` (boolean, dialog visible), `article` (article object). Emits: `update:modelValue`, `saved`.
Content: el-dialog with article content editor, review notes, and save/cancel buttons.

- [ ] **Step 2: Create `PageHeader.vue`**

Props: `title` (string), `subtitle` (string, optional).
Content: Consistent page title with optional subtitle, using ink theme.

- [ ] **Step 3: Create `hooks/usePaginatedList.ts`**

```typescript
import { ref, computed } from "vue";

export function usePaginatedList<T>(fetchFn: (page: number, pageSize: number) => Promise<{ data: T[]; total: number }>) {
  const data = ref<T[]>([]);
  const total = ref(0);
  const page = ref(1);
  const pageSize = ref(20);
  const loading = ref(false);

  async function load() {
    loading.value = true;
    try {
      const result = await fetchFn(page.value, pageSize.value);
      data.value = result.data;
      total.value = result.total;
    } finally {
      loading.value = false;
    }
  }

  return { data, total, page, pageSize, loading, load };
}
```

- [ ] **Step 4: Create `hooks/useActiveTasks.ts`**

Global singleton polling for active tasks (replace duplicate logic in LayoutView + TaskCenterView).

- [ ] **Step 5: Refactor ReviewView, PublishView, CreateView to use ArticleEditorDialog**

Replace inline el-dialog blocks with `<ArticleEditorDialog>`.

- [ ] **Step 6: Refactor all list views to use PageHeader + usePaginatedList**

- [ ] **Step 7: Verify**

```bash
cd ArticleGeneratorAdm && npm run test && npm run build
# Expected: 11 tests pass, build succeeds
```

- [ ] **Step 8: Commit**

---

## Task 5: T12 — 启用 Pinia Store

**Files:**
- Create: `ArticleGeneratorAdm/src/store/accounts.ts`
- Create: `ArticleGeneratorAdm/src/store/tasks.ts`
- Modify: `ArticleGeneratorAdm/src/views/AccountsView.vue` (and other views fetching accounts)
- Modify: `ArticleGeneratorAdm/src/views/LayoutView.vue` (use tasks store)

### Spec: `openspec/changes/p1-architecture-refactor/specs/pinia-state-management/spec.md`

- [ ] **Step 1: Create `store/accounts.ts`**

```typescript
import { defineStore } from "pinia";
import { api, type Account } from "@/api";

export const useAccountsStore = defineStore("accounts", {
  state: () => ({
    accounts: [] as Account[],
    loading: false,
    loaded: false,
  }),
  actions: {
    async fetch() {
      if (this.loaded) return;
      this.loading = true;
      try {
        const { data } = await api.getAccounts();
        this.accounts = data;
      } finally {
        this.loading = false;
        this.loaded = true;
      }
    },
    invalidate() {
      this.loaded = false;
    },
  },
});
```

- [ ] **Step 2: Create `store/tasks.ts`** with active task polling singleton.

- [ ] **Step 3: Replace per-view account fetching with store**

In each view that fetches accounts: `const { data: accounts } = await api.getAccounts()` → `const store = useAccountsStore(); await store.fetch(); store.accounts`.

- [ ] **Step 4: Verify**

```bash
cd ArticleGeneratorAdm && npm run build
# Expected: build succeeds, switching pages doesn't re-fetch accounts
```

---

## Task 6: T13 — 无效 hotspot_id 显式错误

**Files:**
- Modify: `ArticleGeneratorService/app/services/generate_service.py` (or `api/generate.py` if service not yet extracted)
- Create/Modify: `ArticleGeneratorService/tests/test_api_generate.py`

### Spec: `openspec/changes/p1-architecture-refactor/specs/input-validation/spec.md`

- [ ] **Step 1: Add validation at start of trigger function**

In `trigger_generation()`, before the loop, validate all hotspot_ids:

```python
if hotspot_ids:
    existing = db.query(Hotspot).filter(Hotspot.id.in_(hotspot_ids)).all()
    existing_ids = {h.id for h in existing}
    invalid_ids = [hid for hid in hotspot_ids if hid not in existing_ids]
    if invalid_ids:
        raise HTTPException(status_code=400, detail={"message": "无效的热点ID", "invalid_ids": invalid_ids})
```

- [ ] **Step 2: Add test case**

In `tests/test_api_generate.py`:

```python
def test_trigger_generate_invalid_hotspot_id(auth_client):
    """无效 hotspot_id 应返回 400"""
    resp = auth_client.post("/api/generate/trigger", json={
        "hotspot_ids": [99999],
        "account_id": 1,
    })
    assert resp.status_code == 400
    data = resp.json()
    assert "invalid_ids" in str(data)
```

- [ ] **Step 3: Run tests**

```bash
cd ArticleGeneratorService && pytest tests/test_api_generate.py -v --tb=short
# Expected: all tests pass, including new invalid_id test
```

- [ ] **Step 4: Commit**

---

## 执行顺序

```
T08 (service layer) → T07 (async) → T09 (celery split)
                                          ↓
T11 (frontend components) → T12 (pinia)
T13 (validation, independent)
```

后端和前端可并行执行（不同代码库），但后端内部有依赖顺序。

## 自检清单

- [x] 每个 spec requirement 有对应任务
- [x] 无 TBD/TODO
- [x] 文件路径精确
- [x] 遵循 backend-development.mdc 分层规则
- [x] 遵循 frontend-development.mdc 组件抽取规则
- [x] P0 经验教训已融入（数据库安全、浏览器验证）
