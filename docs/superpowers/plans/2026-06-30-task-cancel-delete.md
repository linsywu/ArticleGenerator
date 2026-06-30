# Task Cancel/Delete Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add cancel button to TaskCenterView and delete button to both TaskCenterView and TasksView, with a new backend DELETE endpoint.

**Architecture:** New `DELETE /api/generate/tasks/{task_id}` endpoint validates task state, cleans up generation_logs, and removes the GenerationTask record. Frontend buttons call this endpoint with confirmation dialogs.

**Tech Stack:** FastAPI + SQLAlchemy (backend), Vue 3 + Element Plus (frontend)

## Global Constraints

- 删除前二次确认（`ElMessageBox.confirm`）
- RefineTask 暂不支持取消/删除
- 删除只移除任务记录，保留关联文章
- pending/running 状态不可删除，需先取消

---

### Task 1: Backend DELETE endpoint

**Files:**
- Modify: `ArticleGeneratorService/app/api/generate.py`
- Create test: `ArticleGeneratorService/tests/test_task_delete.py`

**Interfaces:**
- Produces: `DELETE /api/generate/tasks/{task_id}` → `{"message": "已删除"}`

- [ ] **Step 1: Write the failing test**

Create `tests/test_task_delete.py`:

```python
"""测试 DELETE /api/generate/tasks/{task_id}"""
import json
from app.models import GenerationTask, GenerationLog


class TestDeleteTask:
    def test_delete_success_task(self, auth_client, db_session):
        """删除已成功的任务"""
        gt = GenerationTask(task_id="del-test-1", account_id=1, status="success")
        db_session.add(gt)
        # 添加关联日志
        db_session.add(GenerationLog(scenario="generate", task_id="del-test-1", status="success", prompt_tokens=10, completion_tokens=20, latency_ms=100))
        db_session.commit()

        resp = auth_client.delete(f"/api/generate/tasks/del-test-1")
        assert resp.status_code == 200
        assert resp.json()["message"] == "已删除"

        # 验证任务已删除
        assert db_session.query(GenerationTask).filter(GenerationTask.task_id == "del-test-1").first() is None
        # 验证关联日志已清理
        assert db_session.query(GenerationLog).filter(GenerationLog.task_id == "del-test-1").first() is None

    def test_delete_running_task_fails(self, auth_client, db_session):
        """运行中的任务不可删除"""
        gt = GenerationTask(task_id="del-test-2", account_id=1, status="running")
        db_session.add(gt)
        db_session.commit()

        resp = auth_client.delete(f"/api/generate/tasks/del-test-2")
        assert resp.status_code == 400
        assert "请先取消" in resp.json()["detail"]

    def test_delete_not_found(self, auth_client):
        resp = auth_client.delete("/api/generate/tasks/nonexistent")
        assert resp.status_code == 404
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd ArticleGeneratorService && python -m pytest tests/test_task_delete.py -v
```
Expected: FAIL — "Method Not Allowed" (DELETE route not registered)

- [ ] **Step 3: Implement the DELETE endpoint**

In `app/api/generate.py`, add after the cancel endpoint:

```python
@router.delete("/tasks/{task_id}")
def delete_generation_task(task_id: str, db: Session = Depends(get_db)):
    """删除生成任务（仅 success/failed/cancelled 状态可删）"""
    task = db.query(GenerationTask).filter(GenerationTask.task_id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    if task.status in ("pending", "running"):
        raise HTTPException(status_code=400, detail="请先取消任务后再删除")

    # 清理关联的生成日志
    db.query(GenerationLog).filter(GenerationLog.task_id == task_id).delete()

    db.delete(task)
    db.commit()
    return {"message": "已删除"}
```

Add missing import at top of file:
```python
from ..models import Article, Account, GenerationTask, RefineTask, GenerationLog
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd ArticleGeneratorService && python -m pytest tests/test_task_delete.py -v
```
Expected: 3 passed

- [ ] **Step 5: Run full test suite**

```bash
cd ArticleGeneratorService && python -m pytest tests/ -q --ignore=tests/test_account_word_count.py
```
Expected: all pass (except pre-existing `test_update_word_count`)

- [ ] **Step 6: Commit**

```bash
git add ArticleGeneratorService/app/api/generate.py ArticleGeneratorService/tests/test_task_delete.py
git commit -m "feat: add DELETE /api/generate/tasks/{task_id} endpoint"
```

---

### Task 2: TasksView — Add delete button

**Files:**
- Modify: `ArticleGeneratorAdm/src/views/TasksView.vue`

**Interfaces:**
- Consumes: `DELETE /api/generate/tasks/{task_id}` (Task 1)
- Produces: "删除" button in operation column for terminal-state tasks

- [ ] **Step 1: Update operation column width**

In the template, change operation column width from `260` to `320`:

```vue
<el-table-column label="操作" width="320" fixed="right">
```

- [ ] **Step 2: Add delete button in the operations column**

After the existing cancel button block (inside the `v-if="row.status === 'pending' || row.status === 'running'"`), add:

```vue
<el-button
  v-if="row.status === 'success' || row.status === 'failed' || row.status === 'cancelled'"
  size="small"
  type="danger"
  @click="deleteTask(row)"
>
  删除
</el-button>
```

- [ ] **Step 3: Add the `deleteTask` function**

In the `<script setup>` section, after `cancelTask`:

```typescript
async function deleteTask(row: TaskItem) {
  try {
    await ElMessageBox.confirm(
      `确定删除此任务？任务记录将被移除，但已生成的文章不受影响。`,
      "确认删除",
      { confirmButtonText: "删除", cancelButtonText: "取消", type: "warning" }
    );
    await api.delete(`/generate/tasks/${row.task_id}`);
    ElMessage.success("已删除");
    await load();
  } catch (e: any) {
    if (e !== "cancel" && e?.response?.status !== 400) {
      ElMessage.error(e?.response?.data?.detail || "删除失败");
    }
  }
}
```

Note: `api.delete` uses `del` from `@/api/client`. Since `del` is exported but not on the `api` object, use `axios` directly or add a helper. Actually the `api` object has `cancelTask` which uses `post`. We need to import the `del` helper from client or use `api` with a raw path.

Simplest fix — add a `del` method to the import:

```typescript
import { api, del as apiDel, type Article } from "@/api/client";
```

Then use:
```typescript
await apiDel(`/generate/tasks/${row.task_id}`);
```

- [ ] **Step 4: Verify frontend build**

```bash
cd ArticleGeneratorAdm && npx vite build
```
Expected: build success, no errors

- [ ] **Step 5: Commit**

```bash
git add ArticleGeneratorAdm/src/views/TasksView.vue
git commit -m "feat: add delete button to TasksView"
```

---

### Task 3: TaskCenterView — Add cancel and delete buttons

**Files:**
- Modify: `ArticleGeneratorAdm/src/views/TaskCenterView.vue`

**Interfaces:**
- Consumes: `POST /api/generate/tasks/{task_id}/cancel` (existing), `DELETE /api/generate/tasks/{task_id}` (Task 1)
- Produces: "取消" button on pending/running cards, "删除" button on terminal-state cards (generate only)

- [ ] **Step 1: Add action buttons to pending/running task cards**

After the card-meta div in the running tasks section, add:

```vue
<div class="card-actions-row" v-if="t.task_type === 'generate'">
  <el-button size="small" type="danger" text @click="cancelUnifiedTask(t)">取消任务</el-button>
</div>
```

- [ ] **Step 2: Add action buttons to completed task cards**

In the completed tasks section, after the existing `card-actions-row` (查看日志 button), add:

```vue
<el-button
  v-if="t.task_type === 'generate'"
  size="small"
  type="danger"
  text
  @click="deleteUnifiedTask(t)"
>删除</el-button>
```

- [ ] **Step 3: Add the cancel and delete functions**

In the `<script setup>` section:

```typescript
import { ElMessage, ElMessageBox } from "element-plus";
```

Add functions after `showLogsByTaskId`:

```typescript
async function cancelUnifiedTask(t: UnifiedTaskItem) {
  try {
    await ElMessageBox.confirm(`确定取消任务「${t.target}」？`, "确认取消");
    await api.cancelTask(t.task_id);
    ElMessage.success("已取消");
    await loadTasks();
  } catch (e: any) {
    if (e !== "cancel") ElMessage.error("取消失败");
  }
}

async function deleteUnifiedTask(t: UnifiedTaskItem) {
  try {
    await ElMessageBox.confirm(
      `确定删除「${t.target}」？任务记录将被移除。`,
      "确认删除",
      { confirmButtonText: "删除", cancelButtonText: "取消", type: "warning" }
    );
    await api.delete(`/generate/tasks/${t.task_id}`);
    ElMessage.success("已删除");
    tasks.value = tasks.value.filter(task => task.task_id !== t.task_id);
  } catch (e: any) {
    if (e !== "cancel" && e?.response?.status !== 400) {
      ElMessage.error(e?.response?.data?.detail || "删除失败");
    }
  }
}
```

Note: For the delete API call, since the `api` object doesn't have a `delete` method, add the import from client:

```typescript
import { api, del as apiDel, type UnifiedTaskItem } from "@/api/client";
```

Then use:
```typescript
await apiDel(`/generate/tasks/${task_id}`);
// or import axios directly
```

Actually, simplest approach: add a `deleteTask` helper to the `api` object in client.ts or use a direct fetch:

Better: just add a simple del method on `api`:

In `ArticleGeneratorAdm/src/api/client.ts`, add to the `api` object:
```typescript
// 生成 — 删除
deleteGenerationTask: (taskId: string) => del(`/generate/tasks/${taskId}`),
```

Then in TaskCenterView:
```typescript
await api.deleteGenerationTask(t.task_id);
```

- [ ] **Step 4: Add del method to api object**

In `client.ts`, add this line inside the `api` object definition:

```typescript
deleteGenerationTask: (taskId: string) => del(`/generate/tasks/${taskId}`),
```

- [ ] **Step 5: Verify frontend build**

```bash
cd ArticleGeneratorAdm && npx vite build
```
Expected: build success, no errors

- [ ] **Step 6: Commit**

```bash
git add ArticleGeneratorAdm/src/views/TaskCenterView.vue ArticleGeneratorAdm/src/api/client.ts
git commit -m "feat: add cancel and delete buttons to TaskCenterView"
```

---

### Task 4: Integration verification

- [ ] **Step 1: Verify backend tests pass**

```bash
cd ArticleGeneratorService && python -m pytest tests/test_task_delete.py tests/test_generation_logs.py -v
```
Expected: all pass

- [ ] **Step 2: Verify all tests pass**

```bash
cd ArticleGeneratorService && python -m pytest tests/ -q --ignore=tests/test_account_word_count.py
```

- [ ] **Step 3: Verify frontend build**

```bash
cd ArticleGeneratorAdm && npx vite build
```
Expected: build success

- [ ] **Step 4: Restart backend and test in browser**

1. Restart backend: `kill <pid> && uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload`
2. Browser: visit `/tasks` → verify "删除" button on completed tasks → click → confirm → task removed
3. Browser: visit `/task-center` → verify "取消任务" on running cards → verify "删除" on completed cards
4. Check browser console: 0 errors

- [ ] **Step 5: Commit**

```bash
git add -A && git commit -m "test: add integration verification for task cancel/delete"
```
