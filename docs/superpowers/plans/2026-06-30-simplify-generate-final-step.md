# Simplify Generate Final Step — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace article content display in creation flow step 6 with task submission confirmation + task center link.

**Architecture:** Modify `CreateView.vue` only — remove polling and content display logic, add confirmation UI. Backend `tasks.py` already has humanize-sync fix from prior work.

**Tech Stack:** Vue 3 + Element Plus + TypeScript

## Global Constraints

- 前端变更必须浏览器验证，禁止仅依赖 build+test
- 注释/回复语言：中文
- 提交格式：语义化 `feat:` 前缀

---

## File Map

| File | Action | Responsibility |
|------|--------|----------------|
| `ArticleGeneratorAdm/src/views/CreateView.vue` | Modify | Step 6 template + `startGenerate()` + watcher cleanup |

---

### Task 1: Modify CreateView.vue — replace content display with task confirmation

**Files:**
- Modify: `ArticleGeneratorAdm/src/views/CreateView.vue`

**Changes:**

#### 1.1 Remove unused refs (lines 229-231)

Remove:
```ts
const generatingStatusText = ref('')  // line 230
const generatedArticle = ref('')      // line 231
```

#### 1.2 Import `ElMessageBox` 

Modify line 205 — change:
```ts
import { ElMessage } from 'element-plus'
```
to:
```ts
import { ElMessage, ElMessageBox } from 'element-plus'
```

#### 1.3 Add `taskSubmitted` ref for confirmation state

After line 230 (`const generatingStatusText = ref('')`), add:
```ts
const taskSubmitted = ref(false)
```

#### 1.3 Simplify `startGenerate()` — remove polling, add confirmation

Replace lines 360-398 (entire `startGenerate` function) with:

```ts
async function startGenerate() {
  if (!selectedAccountId.value || !idea.value.trim()) return
  generating.value = true
  currentStep.value = 5

  try {
    const points = outline.value.length ? outline.value.map(o => o.point) : undefined
    const topicWithTitle = editedTitle.value
      ? `${editedTitle.value}\n\n${idea.value.trim()}`
      : idea.value.trim()
    const { data } = await api.triggerGenerateWithOutline(selectedAccountId.value, topicWithTitle, points, undefined, selectedDirection.value?.title)
    const taskId = data.tasks?.[0]?.task_id
    if (!taskId) throw new Error('未获取到任务 ID')

    generating.value = false
    taskSubmitted.value = true
  } catch (e: any) {
    generating.value = false
    const errMsg = e?.response?.data?.detail || e?.message || '生成失败'
    try {
      await ElMessageBox.confirm(
        `文章生成失败：${errMsg}\n\n是否返回上一步重新尝试？`,
        '生成失败',
        { confirmButtonText: '返回上一步', cancelButtonText: '关闭', type: 'error' }
      )
      currentStep.value = outline.value.length ? 3 : 2
    } catch {
      // 用户点击关闭，留在当前页面
    }
  }
}
```

#### 1.4 Update step 5→6 watcher to use `taskSubmitted` guard

Replace lines 400-405 with:

```ts
// 进入步骤 6 时自动触发文章生成（仅首次进入）
watch(currentStep, (step) => {
  if (step === 5 && !generating.value && !taskSubmitted.value) {
    startGenerate()
  }
})
```

#### 1.5 Replace step 6 template (lines 172-196)

Replace the entire step 6 block with:

```vue
<!-- 步骤 6: 生成全文 -->
<div v-else key="step6" class="step-card">
  <div class="card-header">
    <span class="card-number">06</span>
    <h2 class="card-title">生成全文</h2>
  </div>
  <div v-if="generating" class="generating-state">
    <div class="generating-spinner"></div>
    <p class="generating-text">正在提交生成任务...</p>
  </div>
  <div v-else-if="taskSubmitted" class="task-submitted-state">
    <div class="submit-success-icon">✅</div>
    <p class="submit-title">文章生产中，请前往任务中心查看</p>
    <p class="submit-desc">文章生成需要一定时间，您可以在任务中心查看实时进度和结果。</p>
    <div class="card-actions">
      <el-button size="large" @click="goBack()">返回上一步</el-button>
      <el-button size="large" type="primary" @click="$router.push('/task-center')">前往任务中心</el-button>
    </div>
  </div>
  <div v-else class="card-actions">
    <el-button size="large" @click="goBack()">返回上一步</el-button>
  </div>
</div>
```

#### 1.6 Add styles for the new confirmation UI

Add after the existing `.generating-*` styles (around line 530-550 area):

```css
.task-submitted-state {
  text-align: center;
  padding: 40px 20px;
}
.submit-success-icon {
  font-size: 48px;
  margin-bottom: 16px;
}
.submit-title {
  font-size: 18px;
  font-weight: 600;
  color: var(--el-text-color-primary);
  margin: 0 0 8px 0;
}
.submit-desc {
  font-size: 14px;
  color: var(--el-text-color-secondary);
  margin: 0 0 24px 0;
}
```

---

- [ ] **Step 1:** Read current `CreateView.vue` to confirm line numbers
- [ ] **Step 2:** Apply edits 1.1–1.6 above
- [ ] **Step 3:** Run `npm run build` — verify no errors
- [ ] **Step 4:** Commit with `feat: replace creation flow final step with task center redirect`
