# Phase 1 Remaining Issues Fix — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix 5 categories of Phase 1 remaining issues: CredentialsView crash bug, CollectTasksView misleading feedback and selector state sync, missing Pydantic schemas, and hardcoded credential_id.

**Architecture:** All changes are surgical fixes to existing files — no new files, no new dependencies, no schema migrations. Backend schemas follow existing Pydantic v2 `Config.from_attributes` pattern. Frontend fixes follow existing Vue 3 Composition API patterns.

**Tech Stack:** Python/FastAPI/Pydantic v2 (backend), Vue 3/Element Plus/TypeScript (frontend)

---

### Task 1: Fix CredentialsView.vue handleCheck crash

**Files:**
- Modify: `ArticleGeneratorAdm/src/views/CredentialsView.vue:167-180`

**Background:** The `handleCheck` function has a broken nested try-catch. The outer try calls `checkCredential(id)`, but an inner try-catch block (lines 170-176) references an undefined `row` variable and duplicates the API call. This causes a runtime error when the "检测" button is clicked.

- [ ] **Step 1: Replace the broken handleCheck function**

Replace lines 167-180 in `ArticleGeneratorAdm/src/views/CredentialsView.vue`:

```typescript
async function handleCheck(id: number) {
  try {
    await credentialsApi.checkCredential(id);
    await fetchCredentials();
    ElMessage.success("检测完成");
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || "检测失败");
  }
}
```

The fix:
1. Removes the inner nested try-catch (lines 170-176)
2. Calls `checkCredential(id)` once with the correct `id` parameter
3. Calls `fetchCredentials()` after the check to refresh the list
4. Shows "检测完成" on success, "检测失败" on error

- [ ] **Step 2: Verify the fix compiles**

Run: `cd ArticleGeneratorAdm && npx vue-tsc --noEmit --pretty 2>&1 | head -20`

Expected: No new errors related to CredentialsView.vue.

- [ ] **Step 3: Commit**

```bash
git add ArticleGeneratorAdm/src/views/CredentialsView.vue
git commit -m "fix: repair CredentialsView handleCheck nested try-catch with undefined row variable"
```

---

### Task 2: Fix CollectTasksView.vue execute feedback

**Files:**
- Modify: `ArticleGeneratorAdm/src/views/CollectTasksView.vue:413-420`

**Background:** The execute handler calls the API successfully but then displays `ElMessage.info("功能开发中")` — a misleading message suggesting the feature is incomplete. The backend endpoint is fully functional.

- [ ] **Step 1: Replace execute feedback message**

Replace the `handleExecute` function (lines 413-420) in `ArticleGeneratorAdm/src/views/CollectTasksView.vue`:

```typescript
async function handleExecute(id: number) {
  try {
    await collectTasksApi.executeTask(id);
    ElMessage.success("采集任务已提交执行");
    await fetchCollectTasks();
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || "操作失败");
  }
}
```

Changes:
1. `ElMessage.info("功能开发中")` → `ElMessage.success("采集任务已提交执行")`
2. Added `await fetchCollectTasks()` to refresh the task list after execution

- [ ] **Step 2: Verify the fix compiles**

Run: `cd ArticleGeneratorAdm && npx vue-tsc --noEmit --pretty 2>&1 | head -20`

Expected: No new errors.

- [ ] **Step 3: Commit**

```bash
git add ArticleGeneratorAdm/src/views/CollectTasksView.vue
git commit -m "fix: replace misleading execution feedback with accurate success message"
```

---

### Task 3: Fix CollectTasksView.vue tree selector state sync

**Files:**
- Modify: `ArticleGeneratorAdm/src/views/CollectTasksView.vue:356-371` (openEditDialog)
- Modify: `ArticleGeneratorAdm/src/views/CollectTasksView.vue:383-395` (handleSave payload)

**Background:** The tree selector uses `selectedTrackIds` (number[]) and `selectedAccountIds` (number[]) for UI state, but the form stores `track_ids`/`account_ids` as JSON strings. When editing an existing task, the tree selector shows no selections because the edit dialog doesn't restore state from the form data. When saving, the tree selections are never serialized into the payload.

- [ ] **Step 1: Fix openEditDialog to restore tree selector state**

Replace `openEditDialog` (lines 356-371) in `ArticleGeneratorAdm/src/views/CollectTasksView.vue`:

```typescript
function openEditDialog(row: CollectTask) {
  editingTask.value = row;
  // Restore tree selector state from stored JSON strings
  selectedTrackIds.value = parseJsonArray(row.track_ids);
  selectedAccountIds.value = parseJsonArray(row.account_ids);
  form.value = {
    name: row.name,
    credential_id: row.credential_id,
    track_ids: row.track_ids || "",
    account_ids: row.account_ids || "",
    collect_mode: row.collect_mode,
    date_start: row.date_start || null,
    date_end: row.date_end || null,
    schedule_type: row.schedule_type,
    cron: row.cron || "",
    interval_hours: row.interval_hours || null,
  };
  dialogVisible.value = true;
}
```

- [ ] **Step 2: Add parseJsonArray helper**

Add the helper function before `loadTrackTree` (before line 320) in `ArticleGeneratorAdm/src/views/CollectTasksView.vue`:

```typescript
function parseJsonArray(raw: string | undefined | null): number[] {
  if (!raw) return [];
  try {
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}
```

- [ ] **Step 3: Fix handleSave to serialize tree selections into payload**

Replace the payload construction in `handleSave` (lines 383-395) in `ArticleGeneratorAdm/src/views/CollectTasksView.vue`:

```typescript
    const payload: Record<string, any> = {
      name: form.value.name,
      credential_id: form.value.credential_id,
      collect_mode: form.value.collect_mode,
      schedule_type: form.value.schedule_type,
      track_ids: JSON.stringify(selectedTrackIds.value),
      account_ids: JSON.stringify(selectedAccountIds.value),
    };
    if (form.value.date_start) payload.date_start = form.value.date_start;
    if (form.value.date_end) payload.date_end = form.value.date_end;
    if (form.value.schedule_type === "cron") payload.cron = form.value.cron;
    if (form.value.schedule_type === "interval") payload.interval_hours = form.value.interval_hours;
```

Key changes:
- `track_ids: form.value.track_ids || undefined` → `track_ids: JSON.stringify(selectedTrackIds.value)`
- `account_ids: form.value.account_ids || undefined` → `account_ids: JSON.stringify(selectedAccountIds.value)`

- [ ] **Step 4: Verify the fix compiles**

Run: `cd ArticleGeneratorAdm && npx vue-tsc --noEmit --pretty 2>&1 | head -20`

Expected: No new errors.

- [ ] **Step 5: Commit**

```bash
git add ArticleGeneratorAdm/src/views/CollectTasksView.vue
git commit -m "fix: sync tree selector state with form on edit and save in CollectTasksView"
```

---

### Task 4: Add MpMaterial and CollectLog Pydantic schemas

**Files:**
- Modify: `ArticleGeneratorService/app/schemas.py` (append new classes at end)
- Modify: `ArticleGeneratorService/app/api/materials.py:16-52` (use response_model)
- Modify: `ArticleGeneratorService/app/api/collect_logs.py:15-46` (use response_model)

**Background:** The materials API and collect_logs API return raw Python dicts instead of Pydantic-validated response models. This is inconsistent with all other API endpoints and skips automatic serialization, validation, and OpenAPI doc generation.

- [ ] **Step 1: Add schemas to schemas.py**

Append the following at the end of `ArticleGeneratorService/app/schemas.py`:

```python
# ----- 素材中心 -----

class MpMaterialResponse(BaseModel):
    id: int
    account_id: int
    title: Optional[str] = None
    author: Optional[str] = None
    original_url: str
    cover_url: Optional[str] = None
    summary: Optional[str] = None
    raw_html: Optional[str] = None
    content_markdown: Optional[str] = None
    content_hash: Optional[str] = None
    word_count: int = 0
    is_original: int = 0
    published_at: Optional[datetime] = None
    collected_at: Optional[datetime] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class MpMaterialListItem(BaseModel):
    id: int
    account_id: int
    title: Optional[str] = None
    author: Optional[str] = None
    original_url: str
    cover_url: Optional[str] = None
    summary: Optional[str] = None
    word_count: int = 0
    is_original: int = 0
    published_at: Optional[datetime] = None
    collected_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    account: Optional[dict] = None

    class Config:
        from_attributes = True


class MpMaterialListResponse(BaseModel):
    data: list[MpMaterialListItem]
    total: int


# ----- 采集日志 -----

class CollectLogResponse(BaseModel):
    id: int
    task_id: int
    task_name: Optional[str] = None
    account_id: Optional[int] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    total_count: int = 0
    success_count: int = 0
    fail_count: int = 0
    error_message: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class CollectLogListResponse(BaseModel):
    data: list[CollectLogResponse]
    total: int
```

- [ ] **Step 2: Update materials API to use response models**

In `ArticleGeneratorService/app/api/materials.py`:

At the top (line 10), add the import:
```python
from ..schemas import MpMaterialResponse, MpMaterialListResponse
```

Replace the list endpoint decorator (line 16):
```python
@router.get("", response_model=MpMaterialListResponse)
```

Replace the detail endpoint decorator (line 55):
```python
@router.get("/{material_id}", response_model=MpMaterialResponse)
```

- [ ] **Step 3: Update collect_logs API to use response models**

In `ArticleGeneratorService/app/api/collect_logs.py`:

At the top (line 9), add the import:
```python
from ..schemas import CollectLogResponse, CollectLogListResponse
```

Replace the list endpoint decorator (line 15):
```python
@router.get("", response_model=CollectLogListResponse)
```

- [ ] **Step 4: Verify backend imports**

Run: `cd ArticleGeneratorService && python -c "from app.schemas import MpMaterialResponse, MpMaterialListResponse, CollectLogResponse, CollectLogListResponse; print('Schemas OK')"`

Expected: `Schemas OK`

- [ ] **Step 5: Verify API loads correctly**

Run: `cd ArticleGeneratorService && timeout 5 python -c "from app.main import app; print('App OK')" 2>&1`

Expected: `App OK` (may see uvicorn start warning, that's fine)

- [ ] **Step 6: Commit**

```bash
git add ArticleGeneratorService/app/schemas.py ArticleGeneratorService/app/api/materials.py ArticleGeneratorService/app/api/collect_logs.py
git commit -m "feat: add MpMaterial and CollectLog Pydantic response schemas"
```

---

### Task 5: Fix hardcoded credential_id in MpAccountsView imports

**Files:**
- Modify: `ArticleGeneratorAdm/src/views/MpAccountsView.vue:212-415`

**Background:** Both `handleImportByName` and `handleImportByUrl` pass `credential_id: 1` hardcoded. This breaks if the credential with ID 1 is deleted or expires. Fix: dynamically fetch credentials and use the first one with `status === "normal"`.

- [ ] **Step 1: Add credentials import and state**

At the top of the `<script setup>` block (line 213), add the import:
```typescript
import credentialsApi from "@/api/modules/credentials";
```

After the `tracks` ref (line 221), add:
```typescript
const credentials = ref<any[]>([]);
```

- [ ] **Step 2: Add fetchCredentials function**

Add this before `onMounted` (before line 412):
```typescript
async function fetchCredentials() {
  try {
    const { data } = await credentialsApi.fetchCredentials();
    credentials.value = (data as any) || [];
  } catch {
    // credentials not required for basic operation
  }
}
```

- [ ] **Step 3: Add getActiveCredentialId helper**

Add this after `fetchCredentials`:
```typescript
function getActiveCredentialId(): number | null {
  const normal = credentials.value.find(c => c.status === "normal");
  return normal ? normal.id : null;
}
```

- [ ] **Step 4: Update handleImportByName**

Replace `credential_id: 1` with dynamic lookup. Modify lines 361:
```typescript
    const credId = getActiveCredentialId();
    if (!credId) { ElMessage.warning("请先添加有效的采集凭证"); return; }
    const names = importNames.value.split('\n').filter(n => n.trim());
    const { data } = await mpAccountsApi.importByName({ names, credential_id: credId });
```

- [ ] **Step 5: Update handleImportByUrl**

Same change for lines 373:
```typescript
    const credId = getActiveCredentialId();
    if (!credId) { ElMessage.warning("请先添加有效的采集凭证"); return; }
    const urls = importUrls.value.split('\n').filter(u => u.trim());
    const { data } = await mpAccountsApi.importByUrl({ urls, credential_id: credId });
```

- [ ] **Step 6: Add fetchCredentials to onMounted**

Replace `onMounted` (line 412):
```typescript
onMounted(() => {
  fetchMpAccounts();
  fetchTracks();
  fetchCredentials();
});
```

- [ ] **Step 7: Verify the fix compiles**

Run: `cd ArticleGeneratorAdm && npx vue-tsc --noEmit --pretty 2>&1 | head -20`

Expected: No new errors.

- [ ] **Step 8: Commit**

```bash
git add ArticleGeneratorAdm/src/views/MpAccountsView.vue
git commit -m "fix: replace hardcoded credential_id with dynamic selection in MpAccountsView imports"
```

---

### Task 6: End-to-End Verification

**Files:** None (verification only)

- [ ] **Step 1: Backend import check**

Run: `cd ArticleGeneratorService && python -c "from app.main import app; print('All imports OK')" 2>&1`

Expected: `All imports OK`

- [ ] **Step 2: Frontend type check**

Run: `cd ArticleGeneratorAdm && npx vue-tsc --noEmit 2>&1 | tail -5`

Expected: No new type errors.

- [ ] **Step 3: Start backend dev server and check /docs**

Run: `cd ArticleGeneratorService && python -m uvicorn app.main:app --reload --port 8000 &`

Open `/docs` and verify:
- Materials API shows `MpMaterialListResponse` and `MpMaterialResponse` as response models
- Collect Logs API shows `CollectLogListResponse` as response model

- [ ] **Step 4: Start frontend dev server and smoke test**

Run: `cd ArticleGeneratorAdm && npm run dev`

Manually verify:
1. **CredentialsView**: Click "检测" button → should show "检测完成" or proper error, no console crash
2. **CollectTasksView**: Click "执行" button → should show "采集任务已提交执行"
3. **CollectTasksView**: Edit an existing task → tree selector should show previously selected tracks/accounts
4. **MpAccountsView**: Click "导入公众号" → should work without hardcoded credential_id errors

- [ ] **Step 5: Commit verification notes**

```bash
git add -A
git commit -m "docs: add verification notes for phase1 remaining issues fix"
```
