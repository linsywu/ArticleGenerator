# MaterialsView 创作方向弹窗 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the placeholder "💡 创作方向" button in MaterialsView with a functional dialog that generates creative directions from material titles and navigates to the article creation wizard.

**Architecture:** New standalone `MaterialsDirectionDialog.vue` component reuses the existing `POST /generate/directions` + polling pattern from CreateView. MaterialsView opens the dialog via `v-model`; on direction selection, the dialog closes and navigates to `/create?idea=...&account_id=...`. CreateView reads query params on mount to pre-fill the idea input and select the account.

**Decisions (from grill-with-docs):**
1. CreateView only pre-fills `idea` + `account_id`, does NOT auto-trigger direction generation
2. CSS spinner for loading state (same pattern as CreateView), no `@element-plus/icons-vue` dependency
3. Use legacy `{ api }` from `@/api/client` for direction API (supports Celery polling; modular API has wrong return type)
4. URL only passes `idea` + `account_id`, not `direction` (no consumer yet)

**Tech Stack:** Vue 3 Composition API, Element Plus (`el-dialog`), Axios (via `@/api/client`), Vue Router

---

## File Structure

| File | Action | Responsibility |
|------|--------|---------------|
| `src/components/MaterialsDirectionDialog.vue` | **Create** | Dialog: API call, polling, card display, navigation |
| `src/views/MaterialsView.vue` | **Modify** | Replace placeholder handler, import + wire dialog |
| `src/views/CreateView.vue` | **Modify** | Read `route.query` on mount, pre-fill idea + account |

---

### Task 1: Create MaterialsDirectionDialog component

**Files:**
- Create: `ArticleGeneratorAdm/src/components/MaterialsDirectionDialog.vue`

- [ ] **Step 1: Scaffold the component file with template, script, and style blocks**

Create `ArticleGeneratorAdm/src/components/MaterialsDirectionDialog.vue`:

```vue
<template>
  <el-dialog
    :model-value="modelValue"
    @update:model-value="$emit('update:modelValue', $event)"
    :title="dialogTitle"
    width="600px"
    :close-on-click-modal="false"
    @open="onOpen"
    @close="onClose"
  >
    <!-- Loading state -->
    <div v-if="loading" class="direction-loading">
      <div class="direction-spinner"></div>
      <p>正在生成创作方向...</p>
    </div>

    <!-- Error state -->
    <div v-else-if="errorMsg" class="direction-error">
      <p>{{ errorMsg }}</p>
      <el-button type="primary" @click="startGeneration">重试</el-button>
    </div>

    <!-- Directions grid -->
    <div v-else-if="directions.length" class="directions-grid">
      <div
        v-for="d in directions"
        :key="d.id"
        class="direction-card"
        :class="{ selected: selectedDirection?.id === d.id }"
        @click="selectedDirection = d"
      >
        <span class="direction-id">{{ d.id }}</span>
        <span class="direction-title">{{ d.title }}</span>
        <span v-if="selectedDirection?.id === d.id" class="direction-check">✓</span>
      </div>
    </div>

    <template #footer>
      <el-button @click="$emit('update:modelValue', false)">取消</el-button>
      <el-button
        type="primary"
        :disabled="!selectedDirection"
        @click="goCreate"
      >
        去创作
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, computed } from "vue";
import { useRouter } from "vue-router";
import { api } from "@/api/client";
import type { DirectionItem, MpMaterial } from "@/api/types";

const props = defineProps<{
  modelValue: boolean;
  material: MpMaterial | null;
}>();

const emit = defineEmits<{
  "update:modelValue": [value: boolean];
}>();

const router = useRouter();

const directions = ref<DirectionItem[]>([]);
const selectedDirection = ref<DirectionItem | null>(null);
const loading = ref(false);
const errorMsg = ref("");

const dialogTitle = computed(() => {
  return props.material?.title
    ? `创作方向 - ${props.material.title.slice(0, 30)}${props.material.title.length > 30 ? "..." : ""}`
    : "创作方向";
});

function onOpen() {
  if (props.material?.title && props.material?.account_id) {
    startGeneration();
  }
}

function onClose() {
  directions.value = [];
  selectedDirection.value = null;
  errorMsg.value = "";
  loading.value = false;
}

async function startGeneration() {
  if (!props.material?.title || !props.material?.account_id) {
    errorMsg.value = "素材信息不完整";
    return;
  }

  loading.value = true;
  errorMsg.value = "";
  directions.value = [];
  selectedDirection.value = null;

  try {
    const { data } = await api.generateDirections(
      props.material.account_id,
      props.material.title
    );
    const taskId = (data as any).task_id;
    if (!taskId) throw new Error("未获取到任务 ID");

    // Poll for result (same pattern as CreateView)
    let attempts = 0;
    const maxAttempts = 30;
    while (attempts < maxAttempts) {
      await new Promise((r) => setTimeout(r, 2000));
      const { data: taskData } = await api.getTaskResult(taskId);
      if (taskData.status === "success") {
        const result = (taskData as any).result;
        directions.value = result?.directions || [];
        if (directions.value.length) {
          selectedDirection.value = directions.value[0];
        }
        return;
      }
      if (taskData.status === "failed") {
        throw new Error(
          (taskData as any).error_message || "方向生成失败"
        );
      }
      attempts++;
    }
    throw new Error("方向生成超时，请重试");
  } catch (e: any) {
    errorMsg.value =
      e?.response?.data?.detail || e?.message || "方向生成失败";
  } finally {
    loading.value = false;
  }
}

function goCreate() {
  if (!selectedDirection.value || !props.material) return;

  const query: Record<string, string> = {
    idea: props.material.title || "",
  };
  if (props.material.account_id) {
    query.account_id = String(props.material.account_id);
  }

  emit("update:modelValue", false);
  router.push({ path: "/create", query });
}
</script>

<style scoped>
.direction-loading {
  text-align: center;
  padding: 40px;
  color: var(--text-muted);
}
.direction-loading p {
  margin-top: 16px;
  font-size: 14px;
}

.direction-spinner {
  width: 40px;
  height: 40px;
  border: 3px solid var(--ink-border, #e0e0e0);
  border-top-color: var(--amber, #c8843c);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  margin: 0 auto;
}
@keyframes spin {
  to { transform: rotate(360deg); }
}

.direction-error {
  text-align: center;
  padding: 40px;
}
.direction-error p {
  color: var(--text-muted);
  margin-bottom: 16px;
}

.directions-grid {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.direction-card {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 14px 18px;
  background: var(--ink-surface, #f5f5f5);
  border: 1px solid var(--ink-border, #e0e0e0);
  border-radius: 8px;
  cursor: pointer;
  transition: border-color 0.2s, background-color 0.2s;
}
.direction-card:hover {
  border-color: var(--text-dim, #999);
}
.direction-card.selected {
  border-color: var(--amber, #c8843c);
  background: rgba(200, 132, 60, 0.06);
}

.direction-id {
  font-size: 20px;
  font-weight: 700;
  color: var(--amber, #c8843c);
  width: 32px;
  flex-shrink: 0;
}

.direction-title {
  flex: 1;
  font-size: 15px;
  color: var(--text-on-dark, #333);
}

.direction-check {
  color: var(--amber, #c8843c);
  font-weight: 700;
}
</style>
```

- [ ] **Step 2: Verify the file was created**

Run: `ls -la ArticleGeneratorAdm/src/components/MaterialsDirectionDialog.vue`
Expected: File exists, ~4KB

---

### Task 2: Integrate dialog into MaterialsView

**Files:**
- Modify: `ArticleGeneratorAdm/src/views/MaterialsView.vue:35,74-79,145-147`

- [ ] **Step 3: Add dialog component import and reactive state**

In `ArticleGeneratorAdm/src/views/MaterialsView.vue`, add the import after line 80 (`import PageHeader from ...`):

```typescript
import MaterialsDirectionDialog from "@/components/MaterialsDirectionDialog.vue";
```

Add two new refs after line 95 (`const markdownLoading = ref(false);`):

```typescript
const directionDialogVisible = ref(false);
const directionMaterial = ref<MpMaterial | null>(null);
```

- [ ] **Step 4: Replace the placeholder onCreateDirection handler**

Replace lines 145-147:

```typescript
function onCreateDirection(row: MpMaterial) {
  ElMessage.info("创作方向功能将在后续版本中开放");
}
```

With:

```typescript
function onCreateDirection(row: MpMaterial) {
  directionMaterial.value = row;
  directionDialogVisible.value = true;
}
```

- [ ] **Step 5: Add the dialog component to the template**

After line 70 (`</el-drawer>`), before line 71 (`</div>`), add:

```vue
    <MaterialsDirectionDialog
      v-model="directionDialogVisible"
      :material="directionMaterial"
    />
```

- [ ] **Step 6: Verify the modified file compiles**

Run: `cat -n ArticleGeneratorAdm/src/views/MaterialsView.vue | head -5`
Expected: File structure intact with new imports

---

### Task 3: Update CreateView to read query params for pre-fill

**Files:**
- Modify: `ArticleGeneratorAdm/src/views/CreateView.vue:198-210,368-373`

- [ ] **Step 7: Add useRoute import**

In `ArticleGeneratorAdm/src/views/CreateView.vue`, change line 199 from:

```typescript
import { ref, computed, onMounted } from 'vue'
```

To:

```typescript
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
```

- [ ] **Step 8: Pre-fill idea and account from query params in onMounted**

Replace the `onMounted` block at lines 368-373:

```typescript
onMounted(async () => {
  try {
    await accountsStore.fetch()
    if (accounts.value.length) selectedAccountId.value = accounts.value[0].id
  } catch (e) { console.error('加载账号失败', e) }
})
```

With:

```typescript
onMounted(async () => {
  const route = useRoute()

  try {
    await accountsStore.fetch()

    // Pre-fill account from query param (from MaterialsView direction dialog)
    if (route.query.account_id) {
      const qAccountId = Number(route.query.account_id)
      if (!isNaN(qAccountId) && accounts.value.find(a => a.id === qAccountId)) {
        selectedAccountId.value = qAccountId
      }
    }
    if (!selectedAccountId.value && accounts.value.length) {
      selectedAccountId.value = accounts.value[0].id
    }

    // Pre-fill idea from query param (does NOT auto-generate directions)
    if (route.query.idea) {
      idea.value = String(route.query.idea)
    }
  } catch (e) { console.error('加载账号失败', e) }
})
```

- [ ] **Step 9: Verify CreateView changes**

Run: `grep -n "useRoute\|route.query" ArticleGeneratorAdm/src/views/CreateView.vue`
Expected: Matches for `useRoute` import and `route.query` usages

---

### Task 4: Verify end-to-end

- [ ] **Step 10: Start dev servers and test the flow**

```bash
# Terminal 1: Backend (if not running)
cd ArticleGeneratorService && source venv/bin/activate && uvicorn app.main:app --reload --port 8000

# Terminal 2: Frontend
cd ArticleGeneratorAdm && npm run dev
```

- [ ] **Step 11: Test: MaterialsView → Direction Dialog → Generate → Select → Navigate**

1. Open browser to `http://localhost:5173/materials`
2. Click "💡 创作方向" on any material row
3. Verify dialog opens with title "创作方向 - {material title}"
4. Verify CSS spinner appears with "正在生成创作方向..."
5. Wait for generation to complete
6. Verify 3-5 direction cards appear with IDs (A/B/C/...) and titles
7. Click a direction card → verify visual highlight
8. Click "去创作" → verify navigation to `/create?idea=...&account_id=...`
9. Verify CreateView Step 1 has correct account pre-selected
10. Click "下一步" → verify Step 2 has idea pre-filled in textarea

Expected: All steps succeed without console errors.

- [ ] **Step 12: Test: Error handling**

1. Stop the Celery worker: `pkill -f "celery.*worker"`
2. Click "💡 创作方向" on a material
3. Verify after ~60 seconds: error message "方向生成超时，请重试" appears
4. Click "重试" → verify loading restarts
5. Restart Celery: `celery -A app.tasks:celery_app worker -l info`
6. Click "重试" again → verify successful generation

- [ ] **Step 13: Test: Dialog close and reopen**

1. Open direction dialog
2. Close it before generation completes
3. Reopen the same material
4. Verify generation restarts fresh (previous state cleared)

- [ ] **Step 14: Commit**

```bash
git add ArticleGeneratorAdm/src/components/MaterialsDirectionDialog.vue
git add ArticleGeneratorAdm/src/views/MaterialsView.vue
git add ArticleGeneratorAdm/src/views/CreateView.vue
git commit -m "feat: implement materials creative direction dialog

Replace placeholder button in MaterialsView with functional dialog.
- New MaterialsDirectionDialog.vue component with polling and card UI
- Reuses existing POST /generate/directions API
- Navigates to /create with query params (idea + account_id) for pre-fill
- CreateView reads query params on mount to pre-fill idea + account"
```

---

## Self-Review

**1. Spec coverage:**
- ✅ "Button opens direction dialog with material title" → Task 1 Step 1 (onOpen → startGeneration)
- ✅ "Loading state during generation" → Task 1 Step 1 (loading div)
- ✅ "Directions displayed as selectable cards" → Task 1 Step 1 (directions-grid)
- ✅ "Generation timeout or failure" → Task 1 Step 1 (error div + retry button)
- ✅ "User selects direction and navigates" → Task 1 Step 1 (goCreate)
- ✅ "Component props" → Task 1 Step 1 (defineProps)
- ✅ "Component manages its own generation state" → Task 1 Step 1 (all state internal)
- ✅ "Pre-fill idea from query parameter" → Task 3 Step 8 (route.query.idea)
- ✅ "Pre-fill account from query parameter" → Task 3 Step 8 (route.query.account_id)

**2. Placeholder scan:** No TBD/TODO/placeholder patterns found.

**3. Type consistency:**
- `DirectionItem` imported from `@/api/types` (defined at types.ts:116-119) ✅
- `MpMaterial` imported from `@/api/types` (defined at types.ts:237-254) ✅
- `api.generateDirections()` from `@/api/client` (returns `{ task_id, status, message }`) ✅
- `api.getTaskResult()` from `@/api/client` (returns task result with `status` + `result`) ✅
- Router path `/create` matches router definition at router/index.ts:15 ✅
