# Fix Collection Pagination, Content Viewing & Dedup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix full collection pagination (only 10 articles instead of all), material content viewing (raw HTML unreadable in drawer), and confirm deduplication works.

**Architecture:** Three changes: (1) add `"full": 999999` sentinel to `_mode_count()` so the pagination loop continues until API exhausts; (2) add `extract_article_content()` static method to `MpClient`, call it during collection in worker.py, store in new `content_html` DB column; (3) dedup is read-only verification — already working. New DB column via manual SQL migration matching project pattern. Historical data: content_html stays NULL, frontend shows "暂无原文内容" fallback.

**Tech Stack:** Python 3 (FastAPI/SQLAlchemy), Vue 3 + TypeScript + Element Plus, SQLite

**Design decisions from grill-with-docs:**
- full mode: sentinel 999999 (Plan A), consistent with existing history_* modes
- content_html: extracted at collection time, stored in DB (Plan B)
- extraction function: static method on MpClient (alongside content_hash, estimate_word_count)
- regex reliability: test against real WeChat articles during implementation
- historical data: no backfill, empty content_html → fallback message in UI
- migration: manual SQL `015_add_content_html_to_mp_materials.sql`

---

## File Structure

| File | Action | Responsibility |
|------|--------|----------------|
| `app/collector/mp_client.py:133-136` | Modify | Add `"full": 999999` to `_mode_count()` |
| `app/collector/mp_client.py` | Modify | Add `extract_article_content()` static method |
| `app/models.py:276-294` | Modify | Add `content_html` Column to `MpMaterial` |
| `ArticleGeneratorDatabase/migrations/015_add_content_html_to_mp_materials.sql` | Create | `ALTER TABLE mp_materials ADD COLUMN content_html TEXT` |
| `app/collector/worker.py:107-149` | Modify | Call `extract_article_content()` during collect |
| `app/api/materials.py:44-62` | Modify | Return `content_html` from DB field in `get_material` |
| `app/schemas.py` | Modify | Add `content_html` to `MpMaterialResponse` |
| `ArticleGeneratorAdm/src/api/types.ts` | Modify | Add `raw_html`, `content_html`, `content_markdown` to `MpMaterial` |
| `ArticleGeneratorAdm/src/views/MaterialsView.vue` | Modify | Render `content_html` in HTML tab |

---

### Task 1: Fix full collection pagination

**Files:**
- Modify: `ArticleGeneratorService/app/collector/mp_client.py:133-136`

- [ ] **Step 1: Add "full" mode to `_mode_count()`**

Open `ArticleGeneratorService/app/collector/mp_client.py`, replace lines 133-136:

```python
    @staticmethod
    def _mode_count(mode: str) -> int:
        mode_map = {"full": 999999, "history_50": 50, "history_100": 100, "history_200": 200, "incremental": 10}
        return mode_map.get(mode, 10)
```

**Why 999999**: The `while begin < count` loop in `fetch_article_list()` already has a proper break when `len(app_msg_list) < 10`. 999999 is a safe sentinel — the loop will always terminate via the break condition before reaching this count. An account with 999999+ articles is impossible.

- [ ] **Step 2: Verify existing modes unchanged**

Run: `cd ArticleGeneratorService && python3 -c "
from app.collector.mp_client import MpClient
assert MpClient._mode_count('incremental') == 10
assert MpClient._mode_count('history_50') == 50
assert MpClient._mode_count('history_100') == 100
assert MpClient._mode_count('history_200') == 200
assert MpClient._mode_count('full') == 999999
assert MpClient._mode_count('unknown') == 10  # default fallback
print('All assertions passed')
"`

Expected: `All assertions passed`

- [ ] **Step 3: Commit**

```bash
git add ArticleGeneratorService/app/collector/mp_client.py
git commit -m "fix: add full collection mode pagination support"
```

---

### Task 2: Add content_html column to model and database

**Files:**
- Modify: `ArticleGeneratorService/app/models.py` (MpMaterial class, around line 288)
- Create: `ArticleGeneratorDatabase/migrations/015_add_content_html_to_mp_materials.sql`

- [ ] **Step 1: Add `content_html` Column to MpMaterial model**

In `ArticleGeneratorService/app/models.py`, find the `MpMaterial` class (line 276). After the `raw_html` line (line 287), add:

```python
    content_html = Column(Text)
```

The relevant section should look like:

```python
class MpMaterial(Base):
    """素材文章"""
    __tablename__ = "mp_materials"

    id = Column(Integer, primary_key=True, autoincrement=True)
    account_id = Column(Integer, ForeignKey("mp_accounts.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(500))
    author = Column(String(100))
    original_url = Column(String(1000), nullable=False)
    cover_url = Column(String(500))
    summary = Column(Text)
    raw_html = Column(Text)
    content_html = Column(Text)
    content_markdown = Column(Text)
    content_hash = Column(String(64))
    word_count = Column(Integer, default=0)
    is_original = Column(Integer, default=0)
    published_at = Column(DateTime)
    collected_at = Column(DateTime(timezone=True), default=_utcnow)
    created_at = Column(DateTime(timezone=True), default=_utcnow)
```

- [ ] **Step 2: Create migration file**

Create `ArticleGeneratorDatabase/migrations/015_add_content_html_to_mp_materials.sql`:

```sql
-- 015: Add content_html to mp_materials
ALTER TABLE mp_materials ADD COLUMN content_html TEXT;
```

- [ ] **Step 3: Apply migration**

```bash
cd ArticleGeneratorDatabase && sqlite3 data/article_generator.db < migrations/015_add_content_html_to_mp_materials.sql 2>&1
```

Expected: No errors.

- [ ] **Step 4: Verify model imports correctly**

Run: `cd ArticleGeneratorService && python3 -c "
from app.models import MpMaterial
from sqlalchemy import inspect
cols = [c.name for c in inspect(MpMaterial).columns]
assert 'content_html' in cols, f'content_html not in {cols}'
print('content_html column exists in MpMaterial model')
"`

Expected: `content_html column exists in MpMaterial model`

- [ ] **Step 5: Commit**

```bash
git add ArticleGeneratorService/app/models.py ArticleGeneratorDatabase/migrations/015_add_content_html_to_mp_materials.sql
git commit -m "feat: add content_html column to MpMaterial for extracted article content"
```

---

### Task 3: Add extract_article_content to MpClient, call in worker

**Files:**
- Modify: `ArticleGeneratorService/app/collector/mp_client.py` (add static method)
- Modify: `ArticleGeneratorService/app/collector/worker.py` (call it during collection)

- [ ] **Step 1: Add `extract_article_content()` static method to MpClient**

In `ArticleGeneratorService/app/collector/mp_client.py`, add after `content_hash()` (line 124-125):

```python
    @staticmethod
    def extract_article_content(html: str) -> str:
        """Extract article body from WeChat MP page HTML"""
        if not html:
            return ""
        # Try to extract js_content div (primary WeChat article container)
        match = re.search(r'<div[^>]*id="js_content"[^>]*>(.*?)</div>', html, re.DOTALL)
        if match:
            content = match.group(1)
            # Remove inline scripts
            content = re.sub(r'<script[^>]*>.*?</script>', '', content, flags=re.DOTALL | re.IGNORECASE)
            return content.strip()
        # Fallback: strip scripts and styles, return cleaned HTML
        cleaned = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
        cleaned = re.sub(r'<style[^>]*>.*?</style>', '', cleaned, flags=re.DOTALL | re.IGNORECASE)
        return cleaned
```

- [ ] **Step 2: Call `extract_article_content()` in worker's `_collect_from_account()`**

In `ArticleGeneratorService/app/collector/worker.py`, in `_collect_from_account()`, after the line `meta = client.extract_metadata(html)` (around line 118), add:

```python
            content_html = MpClient.extract_article_content(html)
```

And in the `MpMaterial(...)` constructor (around line 125-136), add the `content_html` field:

```python
            material = MpMaterial(
                account_id=account.id,
                title=art["title"] or meta["title"],
                author=meta["author"],
                original_url=art["link"],
                cover_url=art["cover"],
                summary=art.get("digest", ""),
                raw_html=html,
                content_html=content_html,
                content_hash=content_hash,
                word_count=word_count,
                published_at=meta["published_at"],
                collected_at=_utcnow(),
            )
```

- [ ] **Step 3: Verify the extraction function**

Run: `cd ArticleGeneratorService && python3 -c "
from app.collector.mp_client import MpClient

# Test js_content extraction
html_with_js = '<html><body><div id=\"js_content\"><p>Hello World</p><script>alert(1)</script></div><script>foo</script></body></html>'
result = MpClient.extract_article_content(html_with_js)
assert '<p>Hello World</p>' in result
assert '<script>' not in result
print('js_content extraction: PASS')

# Test fallback
html_fallback = '<html><body><p>No js_content</p><script>bar</script><style>.a{}</style></body></html>'
result = MpClient.extract_article_content(html_fallback)
assert 'No js_content' in result
assert '<script>' not in result
assert '<style>' not in result
print('fallback extraction: PASS')

# Test empty
assert MpClient.extract_article_content('') == ''
print('empty input: PASS')
print('All tests passed')
"`

Expected: All tests pass

- [ ] **Step 4: Commit**

```bash
git add ArticleGeneratorService/app/collector/mp_client.py ArticleGeneratorService/app/collector/worker.py
git commit -m "feat: extract article content from WeChat MP HTML at collection time"
```

---

### Task 4: Update API and schema to serve content_html from DB

**Files:**
- Modify: `ArticleGeneratorService/app/schemas.py` (MpMaterialResponse)
- Modify: `ArticleGeneratorService/app/api/materials.py` (get_material)

- [ ] **Step 1: Add `content_html` to `MpMaterialResponse`**

In `ArticleGeneratorService/app/schemas.py`, find `class MpMaterialResponse` and add `content_html` after `raw_html`:

```python
class MpMaterialResponse(BaseModel):
    id: int
    account_id: int
    title: Optional[str] = None
    author: Optional[str] = None
    original_url: str
    cover_url: Optional[str] = None
    summary: Optional[str] = None
    raw_html: Optional[str] = None
    content_html: Optional[str] = None
    content_markdown: Optional[str] = None
    content_hash: Optional[str] = None
    word_count: int = 0
    is_original: int = 0
    published_at: Optional[datetime] = None
    collected_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    account: Optional[dict] = None

    class Config: from_attributes = True
```

- [ ] **Step 2: Add `content_html` to `get_material` response**

In `ArticleGeneratorService/app/api/materials.py`, in the `get_material()` return dict, add `content_html` after `raw_html`:

```python
        "raw_html": material.raw_html,
        "content_html": material.content_html,
        "content_markdown": material.content_markdown,
```

- [ ] **Step 3: Verify schema + API consistency**

Run: `cd ArticleGeneratorService && python3 -c "
from app.schemas import MpMaterialResponse
fields = list(MpMaterialResponse.model_fields.keys())
assert 'content_html' in fields, f'content_html not in {fields}'
print('Schema OK')
# Verify API module imports cleanly
from app.api.materials import router
print('API module imports OK')
"`

Expected:
```
Schema OK
API module imports OK
```

- [ ] **Step 4: Commit**

```bash
git add ArticleGeneratorService/app/schemas.py ArticleGeneratorService/app/api/materials.py
git commit -m "feat: serve content_html from DB in material detail API"
```

---

### Task 5: Update frontend to render extracted article content

**Files:**
- Modify: `ArticleGeneratorAdm/src/api/types.ts` (MpMaterial interface)
- Modify: `ArticleGeneratorAdm/src/views/MaterialsView.vue` (HTML tab)

- [ ] **Step 1: Add missing fields to frontend `MpMaterial` type**

In `ArticleGeneratorAdm/src/api/types.ts`, find `export interface MpMaterial` and add `raw_html`, `content_html`, `content_markdown`:

```typescript
export interface MpMaterial {
  id: number;
  account_id: number;
  title?: string;
  author?: string;
  original_url: string;
  cover_url?: string;
  summary?: string;
  raw_html?: string;
  content_html?: string;
  content_markdown?: string;
  word_count: number;
  is_original: number;
  published_at?: string;
  collected_at?: string;
  created_at: string;
  account?: { id: number; name: string };
}
```

- [ ] **Step 2: Change HTML tab to render `content_html` with fallback**

In `ArticleGeneratorAdm/src/views/MaterialsView.vue`, find the HTML tab pane:

```html
          <el-tab-pane label="原文 (HTML)" name="html">
            <div class="html-preview" v-html="currentMaterial.raw_html || '(无内容)'" />
          </el-tab-pane>
```

Replace with:

```html
          <el-tab-pane label="原文 (HTML)" name="html">
            <div v-if="currentMaterial.content_html" class="html-preview" v-html="currentMaterial.content_html" />
            <div v-else style="text-align:center; padding:40px; color:#888;">暂无原文内容</div>
          </el-tab-pane>
```

- [ ] **Step 3: Build frontend to verify no compilation errors**

Run: `cd ArticleGeneratorAdm && npx vite build 2>&1 | tail -20`

Expected: Build succeeds with no errors.

- [ ] **Step 4: Commit**

```bash
git add ArticleGeneratorAdm/src/api/types.ts ArticleGeneratorAdm/src/views/MaterialsView.vue
git commit -m "fix: render extracted article content in material detail drawer"
```

---

### Task 6: Verify deduplication (read-only audit)

**Files:**
- Read only: `ArticleGeneratorService/app/collector/worker.py`

- [ ] **Step 1: Confirm URL-based dedup exists**

In `_collect_from_account()`, verify:

```python
existing = db.query(MpMaterial).filter(MpMaterial.original_url == art["link"]).first()
if existing:
    continue
```

- [ ] **Step 2: Confirm content-hash-based dedup exists**

After HTML fetch, verify:

```python
hash_exists = db.query(MpMaterial).filter(MpMaterial.content_hash == content_hash).first()
if hash_exists:
    continue
```

- [ ] **Step 3: Report finding**

Both dedup layers confirmed. No code changes needed.

---

### Task 7: End-to-end verification

- [ ] **Step 1: Start backend dev server**

```bash
cd ArticleGeneratorService && source venv/bin/activate && uvicorn app.main:app --reload --port 8000 &
```

Wait for: `Uvicorn running on http://127.0.0.1:8000`

- [ ] **Step 2: Start frontend dev server**

```bash
cd ArticleGeneratorAdm && npx vite --port 5173 &
```

Wait for: `Local: http://localhost:5173/`

- [ ] **Step 3: Test full collection pagination**

1. Open `http://localhost:5173/`, navigate to 采集任务
2. Create a task with `collect_mode="full"` for a known account
3. Execute the task
4. After completion, check 素材中心 article count is >10 for that account

- [ ] **Step 4: Test material content viewing**

1. In 素材中心, click "查看" on a material
2. "原文 (HTML)" tab shows readable article content (not WeChat chrome)
3. "Markdown" tab still works (click to load → parsed content)
4. For old materials (collected before this fix), "暂无原文内容" is shown

- [ ] **Step 5: Test content extraction against a real WeChat article**

Run: `cd ArticleGeneratorService && python3 -c "
import requests
from app.collector.mp_client import MpClient
# Use a well-known WeChat article URL for testing
url = 'https://mp.weixin.qq.com/s?__biz=MjM5MzA4ODI5Nw==&mid=2651249879&idx=1&sn=test'
resp = requests.get(url, timeout=10)
html = resp.text
content = MpClient.extract_article_content(html)
print(f'Extracted {len(content)} chars')
print(content[:200])
assert len(content) > 100, 'Extracted content too short — regex may not match'
print('Real article extraction: PASS')
"`

If the test URL is inaccessible, skip with note: "Test article URL unreachable — verify with real collection task instead."

- [ ] **Step 6: Run unit tests**

```bash
cd ArticleGeneratorService && python3 -m pytest tests/ -v --tb=short 2>&1 | tail -30
```

Expected: All tests pass (or pre-existing failures only).

- [ ] **Step 7: Commit**

```bash
git add -A
git commit -m "docs: end-to-end verification for collection fixes"
```
