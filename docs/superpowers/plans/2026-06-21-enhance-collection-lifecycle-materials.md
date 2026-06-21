# Enhance Collection Task Lifecycle & Materials — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development

**Goal:** 5 UX improvements: execute auto-refresh+polling, task lifecycle drawer, materials pagination enhancement, is_original/published_at display, collect log detail drawer.

**Tech Stack:** Vue 3 + Element Plus + TypeScript, Python FastAPI + SQLAlchemy

---

## Verified Current State (2026-06-21)

| # | Requirement | Current State |
|---|-------------|---------------|
| 1 | Execute → refresh | `handleExecute` (line 441-448) calls `executeTask` + `fetchCollectTasks` once. No polling. |
| 2 | Task log drawer | `viewLogs` (line 471) navigates to `/collect-logs?task_id=X`. No drawer. |
| 3 | Materials pagination | `el-pagination` (line 34) layout=`"prev, pager, next"`. No total/sizes. |
| 4 | is_original + published_at | Table (line 14) has no `is_original` column. `published_at` shown but mostly `null` — worker uses `meta["published_at"]` (from HTML meta), not `art["create_time"]` (API timestamp). |
| 5 | Log detail drawer | `CollectLogsView.vue` has no row click, no drawer. No `GET /collect-logs/{id}` endpoint. |

---

## Task 1: Fix published_at — use API create_time instead of HTML meta

**File**: `app/collector/worker.py:143-156`

**Root cause**: `extract_metadata()` reads `<meta property="og:article:publish_time">` from WeChat article HTML, which is often missing. But `fetch_article_list()` already returns `create_time` from the API (Unix timestamp).

**Fix**: Convert `art["create_time"]` to datetime and use it:

```python
from datetime import datetime, timezone

# After line 141 (word_count), add:
published_at = None
if art.get("create_time"):
    try:
        published_at = datetime.fromtimestamp(art["create_time"], tz=timezone.utc)
    except (ValueError, TypeError, OSError):
        pass

# In MpMaterial(...), change:
published_at=meta["published_at"],
# To:
published_at=published_at or meta["published_at"],
```

Priority: API timestamp first, HTML meta fallback.

---

## Task 2: Execute button → auto-refresh + polling

**File**: `ArticleGeneratorAdm/src/views/CollectTasksView.vue:441-448`

**Change**: After `executeTask`, start polling until task completes:

```typescript
async function handleExecute(id: number) {
  try {
    await collectTasksApi.executeTask(id);
    ElMessage.success("采集任务已提交执行");
    await fetchCollectTasks();
    // Poll until done
    pollTask(id);
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || "操作失败");
  }
}

const pollingTimers = new Map<number, ReturnType<typeof setInterval>>();

async function pollTask(taskId: number) {
  // Clear any existing poll for this task
  if (pollingTimers.has(taskId)) clearInterval(pollingTimers.get(taskId));
  
  const timer = setInterval(async () => {
    try {
      const { data } = await collectTasksApi.getCollectTask(taskId);
      // Update the task in the list
      const idx = collectTasks.value.findIndex(t => t.id === taskId);
      if (idx !== -1) collectTasks.value[idx] = data;
      
      if (data.status !== "running") {
        clearInterval(timer);
        pollingTimers.delete(taskId);
        await fetchCollectTasks(); // Full refresh on completion
      }
    } catch { /* polling error — ignore */ }
  }, 2000);
  pollingTimers.set(taskId, timer);
}
```

Also add `onUnmounted` cleanup:
```typescript
import { onUnmounted } from "vue";
onUnmounted(() => {
  pollingTimers.forEach(t => clearInterval(t));
});
```

---

## Task 3: Task lifecycle drawer (log button → el-drawer)

**File**: `ArticleGeneratorAdm/src/views/CollectTasksView.vue`

**Change**: Replace `viewLogs` navigation with drawer component.

Template additions (before closing `</div>` / `</template>`):
```html
<!-- Lifecycle Drawer -->
<el-drawer v-model="logDrawerVisible" title="任务执行日志" size="50%">
  <template v-if="logTaskId">
    <div v-loading="logLoading">
      <h4 style="margin-bottom:12px;">{{ logTaskName }}</h4>
      <el-table :data="logEntries" size="small">
        <el-table-column label="公众号" width="120">
          <template #default="{ row }">{{ row.account?.name || '-' }}</template>
        </el-table-column>
        <el-table-column label="开始时间" width="160">
          <template #default="{ row }">{{ formatTimeStr(row.start_time) }}</template>
        </el-table-column>
        <el-table-column label="状态" width="100" align="center">
          <template #default="{ row }">
            <el-tag v-if="!row.end_time" type="warning" size="small">进行中</el-tag>
            <el-tag v-else-if="row.fail_count > 0" type="danger" size="small">部分失败</el-tag>
            <el-tag v-else type="success" size="small">完成</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="success_count" label="成功" width="70" align="center" />
        <el-table-column prop="fail_count" label="失败" width="70" align="center" />
        <el-table-column prop="total_count" label="总计" width="70" align="center" />
        <el-table-column label="错误信息" min-width="150">
          <template #default="{ row }">{{ row.error_message || '-' }}</template>
        </el-table-column>
      </el-table>
      <div v-if="logEntries.length === 0 && !logLoading" style="text-align:center;padding:40px;color:#999;">
        暂无执行记录
      </div>
    </div>
  </template>
</el-drawer>
```

Script additions:
```typescript
const logDrawerVisible = ref(false);
const logTaskId = ref<number | null>(null);
const logTaskName = ref("");
const logEntries = ref<CollectLog[]>([]);
const logLoading = ref(false);
let logPollTimer: ReturnType<typeof setInterval> | null = null;

function viewLogs(row: CollectTask) {
  logTaskId.value = row.id;
  logTaskName.value = row.name;
  logDrawerVisible.value = true;
  fetchLogEntries();
  startLogPolling();
}

async function fetchLogEntries() {
  if (!logTaskId.value) return;
  logLoading.value = true;
  try {
    const { data } = await collectLogsApi.fetchCollectLogs({ task_id: logTaskId.value, page_size: 50 });
    logEntries.value = data.data;
  } finally {
    logLoading.value = false;
  }
}

function startLogPolling() {
  if (logPollTimer) clearInterval(logPollTimer);
  logPollTimer = setInterval(async () => {
    if (!logDrawerVisible.value) { stopLogPolling(); return; }
    await fetchLogEntries();
    // Stop when all entries have end_time
    if (logEntries.value.length > 0 && logEntries.value.every(l => l.end_time)) {
      stopLogPolling();
    }
  }, 2000);
}

function stopLogPolling() {
  if (logPollTimer) { clearInterval(logPollTimer); logPollTimer = null; }
}

function formatTimeStr(iso?: string) {
  if (!iso) return '-';
  return iso.replace('T',' ').slice(0,19);
}
```

Close drawer → stop polling:
```html
<el-drawer v-model="logDrawerVisible" ... @close="stopLogPolling">
```

Need to import `collectLogsApi` and `CollectLog` type.

---

## Task 4: Materials pagination enhancement

**File**: `ArticleGeneratorAdm/src/views/MaterialsView.vue:34-41`

Replace:
```html
<el-pagination
  v-model:current-page="page"
  :page-size="pageSize"
  :total="total"
  layout="prev, pager, next"
  style="margin-top: 16px; justify-content: center;"
  @current-change="fetchMaterials"
/>
```

With:
```html
<el-pagination
  v-model:current-page="page"
  v-model:page-size="pageSize"
  :page-sizes="[10, 20, 50]"
  :total="total"
  layout="total, sizes, prev, pager, next"
  style="margin-top: 16px; justify-content: center;"
  @current-change="fetchMaterials"
  @size-change="fetchMaterials"
/>
```

---

## Task 5: Materials is_original + published_at columns + published_at fix

### 5a. Backend fix (same as Task 1, listed here for completeness)

**File**: `app/collector/worker.py`

See Task 1 — use `art["create_time"]` for `published_at`.

### 5b. Frontend table columns

**File**: `ArticleGeneratorAdm/src/views/MaterialsView.vue` — add between 字数 and 发布时间 columns:

```html
<el-table-column label="原创" width="70" align="center">
  <template #default="{ row }">
    <el-tag v-if="row.is_original" type="success" size="small">原创</el-tag>
    <el-tag v-else size="small" type="info">转载</el-tag>
  </template>
</el-table-column>
```

Update existing `published_at` column to handle null gracefully (line 20-22 already does `slice(0,10) || '-'` — keep as is, but with the backend fix it will now show real dates).

---

## Task 6: Collect Log detail drawer

### 6a. Backend: Add GET single log endpoint

**File**: `app/api/collect_logs.py` — add after `list_collect_logs`:

```python
@router.get("/{log_id}", response_model=CollectLogResponse)
def get_collect_log(log_id: int, db: Session = Depends(get_db)):
    """获取单条采集日志详情"""
    log = db.query(CollectLog).filter(CollectLog.id == log_id).first()
    if not log:
        raise HTTPException(status_code=404, detail="日志不存在")
    
    task = db.query(CollectTask).filter(CollectTask.id == log.task_id).first()
    account = db.query(MpAccount).filter(MpAccount.id == log.account_id).first() if log.account_id else None
    
    # Also get sibling logs from the same batch (same task, similar start_time)
    siblings = []
    if log.start_time and task:
        from datetime import timedelta
        window_start = log.start_time - timedelta(seconds=10)
        window_end = log.start_time + timedelta(seconds=10)
        siblings = db.query(CollectLog).filter(
            CollectLog.task_id == log.task_id,
            CollectLog.id != log.id,
            CollectLog.start_time >= window_start,
            CollectLog.start_time <= window_end
        ).all()
    
    return {
        "id": log.id,
        "task_id": log.task_id,
        "task_name": task.name if task else None,
        "account_id": log.account_id,
        "account": {"id": account.id, "name": account.name} if account else None,
        "start_time": _local_iso(log.start_time),
        "end_time": _local_iso(log.end_time),
        "total_count": log.total_count,
        "success_count": log.success_count,
        "fail_count": log.fail_count,
        "error_message": log.error_message,
        "created_at": _local_iso(log.created_at),
        "siblings": [{"id": s.id, "account": None, "success_count": s.success_count, "fail_count": s.fail_count} for s in siblings],
    }
```

Note: `siblings` field needs to be added to `CollectLogResponse` in schemas.py:
```python
siblings: Optional[list] = None
```

### 6b. Frontend API module

**File**: `src/api/modules/collectLogs.ts` — add:
```typescript
getCollectLog: (id: number) => get<CollectLog>(`/collect-logs/${id}`),
```

### 6c. Frontend view drawer

**File**: `ArticleGeneratorAdm/src/views/CollectLogsView.vue` — add drawer + row click:

Template (after `</el-pagination>`, before `</div>`):
```html
<el-drawer v-model="drawerVisible" title="日志详情" size="45%">
  <template v-if="currentLog">
    <el-descriptions :column="2" border>
      <el-descriptions-item label="任务">{{ currentLog.task_name }}</el-descriptions-item>
      <el-descriptions-item label="公众号">{{ currentLog.account?.name || '-' }}</el-descriptions-item>
      <el-descriptions-item label="开始时间">{{ currentLog.start_time?.replace('T',' ').slice(0,19) || '-' }}</el-descriptions-item>
      <el-descriptions-item label="结束时间">{{ currentLog.end_time?.replace('T',' ').slice(0,19) || '-' }}</el-descriptions-item>
      <el-descriptions-item label="成功">{{ currentLog.success_count }}</el-descriptions-item>
      <el-descriptions-item label="失败">{{ currentLog.fail_count }}</el-descriptions-item>
      <el-descriptions-item label="总计">{{ currentLog.total_count }}</el-descriptions-item>
      <el-descriptions-item label="错误信息" :span="2">{{ currentLog.error_message || '无' }}</el-descriptions-item>
    </el-descriptions>
    
    <div v-if="currentLog.siblings?.length" style="margin-top:20px;">
      <h4>同批次日志</h4>
      <el-table :data="currentLog.siblings" size="small" style="margin-top:8px;">
        <el-table-column prop="id" label="ID" width="60" />
        <el-table-column prop="success_count" label="成功" width="80" />
        <el-table-column prop="fail_count" label="失败" width="80" />
      </el-table>
    </div>
  </template>
</el-drawer>
```

Script:
```typescript
const drawerVisible = ref(false);
const currentLog = ref<CollectLog | null>(null);

async function openLogDetail(row: CollectLog) {
  try {
    const { data } = await collectLogsApi.getCollectLog(row.id);
    currentLog.value = data;
    drawerVisible.value = true;
  } catch (e) {
    console.error("Failed to load log detail", e);
  }
}
```

Table: add `@row-click="openLogDetail"` and `cursor: pointer` style.

---

## Task 7: End-to-end verification

- [ ] Start backend + frontend
- [ ] Execute a task → verify polling updates status in real-time
- [ ] Click "日志" → drawer opens with real-time log entries
- [ ] Materials list → new is_original column shows, pagination shows total/sizes
- [ ] published_at shows real dates for new collections
- [ ] Collect logs → click row → drawer with detail + siblings
- [ ] Run verifier-unit + verifier-e2e
