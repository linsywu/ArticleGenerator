# 方向卡片展示增强 + 下游链路修复 — 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 方向卡片展示 LLM 输出的 7 个字段，且 `core_viewpoint` 替代 `title` 传入下游生成步骤

**Architecture:** 3 文件修改：后端 Pydantic schema → 前端 TypeScript 类型 → 前端 Vue 模板 + 下游传递。新字段均为 Optional，向后兼容。关键变更：4 处 `selectedDirection.value.title` → `core_viewpoint`（带 `|| title` fallback）

**Tech Stack:** Python Pydantic + TypeScript + Vue 3 SFC + Element Plus

## Global Constraints

- 新字段必须 Optional（向后兼容旧方向数据）
- 前端用 `v-if` 条件渲染（缺字段不显示空白行）
- 下游传递用 `core_viewpoint || title` fallback（旧数据无 core_viewpoint 时回退）
- 不修改 tasks.py 解析逻辑（已透传所有 JSON 字段）
- 不修改 direction 提示词本身
- 前端变更需浏览器验证

---

## File Structure

| 文件 | 操作 | 职责 |
|------|------|------|
| `ArticleGeneratorService/app/schemas.py:369-371` | 修改 | `DirectionItem` 新增 5 个 Optional 字段 |
| `ArticleGeneratorAdm/src/api/types.ts:112-115` | 修改 | `DirectionItem` 接口同步 |
| `ArticleGeneratorAdm/src/views/CreateView.vue` | 修改 | 卡片模板重设计 + CSS + 下游传递修复 |

---

### Task 1: 后端 Schema — DirectionItem 新增 5 个可选字段

**Files:**
- Modify: `ArticleGeneratorService/app/schemas.py:369-371`

**Interfaces:**
- Produces: `DirectionItem(id, title, angle?, core_viewpoint?, reader_gain?, article_type?, check?)`

- [ ] **Step 1: 修改 DirectionItem schema**

将 `ArticleGeneratorService/app/schemas.py` 第 369-371 行：

```python
class DirectionItem(BaseModel):
    id: str
    title: str
```

替换为：

```python
class DirectionItem(BaseModel):
    id: str
    title: str
    angle: Optional[str] = None
    core_viewpoint: Optional[str] = None
    reader_gain: Optional[str] = None
    article_type: Optional[str] = None
    check: Optional[str] = None
```

确认文件顶部已有 `from typing import Optional`。

- [ ] **Step 2: 验证**

```bash
cd ArticleGeneratorService && python -c "
from app.schemas import DirectionItem
# 全字段
d = DirectionItem(id='A', title='测试', angle='反常识', core_viewpoint='核心论点...', reader_gain='收获', article_type='现象解读型', check='好奇:xx')
print('full:', d.model_dump())
# 只有 id+title
d2 = DirectionItem(id='B', title='旧格式')
print('legacy:', d2.model_dump())
"
```

预期：全字段 serialization 保留所有字段，旧格式 angle/core_viewpoint 等为 `None`。

- [ ] **Step 3: Commit**

```bash
git add ArticleGeneratorService/app/schemas.py
git commit -m "feat: DirectionItem schema 新增 angle/core_viewpoint/reader_gain/article_type/check 可选字段"
```

---

### Task 2: 前端类型 — DirectionItem 接口同步

**Files:**
- Modify: `ArticleGeneratorAdm/src/api/types.ts:112-115`

**Interfaces:**
- Produces: `DirectionItem` 含 7 个字段（5 个 optional）

- [ ] **Step 1: 修改 TypeScript 接口**

将 `ArticleGeneratorAdm/src/api/types.ts` 第 112-115 行：

```typescript
export interface DirectionItem {
  id: string;
  title: string;
}
```

替换为：

```typescript
export interface DirectionItem {
  id: string;
  title: string;
  angle?: string;
  core_viewpoint?: string;
  reader_gain?: string;
  article_type?: string;
  check?: string;
}
```

- [ ] **Step 2: Commit**

```bash
git add ArticleGeneratorAdm/src/api/types.ts
git commit -m "feat: DirectionItem 前端类型同步新增 5 个字段"
```

---

### Task 3: 下游链路修复 — title → core_viewpoint

**Files:**
- Modify: `ArticleGeneratorAdm/src/views/CreateView.vue`

**Interfaces:**
- Consumes: `DirectionItem`（含 `core_viewpoint`）
- Produces: 下游 API 调用传入 `core_viewpoint` 而非 `title`

- [ ] **Step 1: 修改 generateOutline() — Line 290**

```typescript
// 修改前：
const { data } = await api.generateOutline(selectedAccountId.value, idea.value.trim(), selectedDirection.value.title)
// 修改后：
const { data } = await api.generateOutline(selectedAccountId.value, idea.value.trim(), selectedDirection.value.core_viewpoint || selectedDirection.value.title)
```

- [ ] **Step 2: 修改 generateTitles() — Line 321**

```typescript
// 修改前：
const { data } = await api.generateTitles(selectedAccountId.value, idea.value.trim(), selectedDirection.value.title, points)
// 修改后：
const { data } = await api.generateTitles(selectedAccountId.value, idea.value.trim(), selectedDirection.value.core_viewpoint || selectedDirection.value.title, points)
```

- [ ] **Step 3: 修改 startGenerate() — Line 363**

```typescript
// 修改前：...selectedDirection.value?.title, ...
// 修改后：...selectedDirection.value?.core_viewpoint || selectedDirection.value?.title, ...
```

完整行变为：
```typescript
const { data } = await api.triggerGenerateWithOutline(selectedAccountId.value, topicWithTitle, points, wordCount.value || undefined, selectedDirection.value?.core_viewpoint || selectedDirection.value?.title, directionTaskId.value || undefined, outlineTaskId.value || undefined, titleTaskId.value || undefined)
```

- [ ] **Step 4: 修改步骤 4 模板展示 — Line 117**

```html
<!-- 修改前： -->
<p class="card-desc">方向：{{ selectedDirection?.title }}。编辑、排序或增删要点。</p>
<!-- 修改后： -->
<p class="card-desc">方向：{{ selectedDirection?.core_viewpoint || selectedDirection?.title }}。编辑、排序或增删要点。</p>
```

- [ ] **Step 5: Commit**

```bash
git add ArticleGeneratorAdm/src/views/CreateView.vue
git commit -m "fix: 方向下游传递 title → core_viewpoint（fallback 兼容旧数据）"
```

---

### Task 4: 前端方向卡片重设计

**Files:**
- Modify: `ArticleGeneratorAdm/src/views/CreateView.vue:93-97`（模板）
- Modify: `ArticleGeneratorAdm/src/views/CreateView.vue:465-472`（CSS 样式）

- [ ] **Step 1: 新增 angleTagType 辅助函数**

在 `CreateView.vue` `<script setup>` 中函数定义区域（约第 178 行，`scenarioLabel` 函数下方）添加：

```typescript
function angleTagType(angle: string): string {
  const t: Record<string, string> = {
    "反常识": "danger",
    "情感共鸣": "warning",
    "利益驱动": "success",
    "实用干货": "",
    "故事切入": "info",
    "社会观察": "warning",
    "心理机制": "info",
  };
  return t[angle] || "";
}
```

- [ ] **Step 2: 修改方向卡片模板**

将第 93-97 行：

```html
<div v-for="d in directions" :key="d.id" class="direction-card" :class="{ selected: selectedDirection?.id === d.id }" @click="selectedDirection = d">
  <span class="direction-id">{{ d.id }}</span>
  <span class="direction-title">{{ d.title }}</span>
  <span v-if="selectedDirection?.id === d.id" class="direction-check">✓</span>
</div>
```

替换为：

```html
<div v-for="d in directions" :key="d.id" class="direction-card" :class="{ selected: selectedDirection?.id === d.id }" @click="selectedDirection = d">
  <span class="direction-id">{{ d.id }}</span>
  <div class="direction-body">
    <div class="direction-title-row">
      <span class="direction-title">{{ d.title }}</span>
      <span v-if="selectedDirection?.id === d.id" class="direction-check">✓</span>
    </div>
    <p v-if="d.core_viewpoint" class="direction-viewpoint">{{ d.core_viewpoint }}</p>
    <p v-if="d.reader_gain" class="direction-gain">📌 {{ d.reader_gain }}</p>
    <p v-if="d.check" class="direction-check-text">{{ d.check }}</p>
    <div v-if="d.angle || d.article_type" class="direction-meta">
      <el-tag v-if="d.angle" size="small" :type="angleTagType(d.angle)">{{ d.angle }}</el-tag>
      <el-tag v-if="d.article_type" size="small" type="info">{{ d.article_type }}</el-tag>
    </div>
  </div>
</div>
```

- [ ] **Step 3: 更新 CSS 样式**

替换第 465-472 行：

```css
/* 方向卡片 */
.directions-grid { display: flex; flex-direction: column; gap: 8px; margin-bottom: var(--space-xl); }
.direction-card { display: flex; align-items: flex-start; gap: 14px; padding: 14px 18px; background: var(--ink-surface); border: 1px solid var(--ink-border); border-radius: var(--radius-lg); cursor: pointer; transition: all var(--duration-fast) var(--ease-out); }
.direction-card:hover { border-color: var(--text-dim); }
.direction-card.selected { border-color: var(--amber); background: rgba(200,132,60,0.06); }
.direction-id { font-family: var(--font-serif); font-size: 20px; font-weight: 700; color: var(--amber); width: 32px; flex-shrink: 0; line-height: 1.4; }
.direction-body { flex: 1; min-width: 0; }
.direction-title-row { display: flex; align-items: center; gap: 8px; }
.direction-title { flex: 1; font-size: 15px; font-weight: 600; color: var(--text-on-dark); }
.direction-check { color: var(--amber); font-weight: 700; flex-shrink: 0; }
.direction-viewpoint { font-size: 13px; color: var(--text-muted); line-height: 1.6; margin: 6px 0 0; display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical; overflow: hidden; }
.direction-gain { font-size: 12px; color: var(--amber-light); margin: 4px 0 0; line-height: 1.5; }
.direction-check-text { font-size: 11px; color: var(--text-dim); margin: 4px 0 0; line-height: 1.5; }
.direction-meta { display: flex; gap: 6px; margin-top: 8px; }
```

- [ ] **Step 4: Commit**

```bash
git add ArticleGeneratorAdm/src/views/CreateView.vue
git commit -m "feat: 方向卡片重设计 — 展示全字段层次布局"
```

---

### Task 5: 浏览器验证

- [ ] **Step 1: 启动服务**

```bash
cd ArticleGeneratorService && uvicorn app.main:app --host 0.0.0.0 --port 8000 &
cd ArticleGeneratorService && celery -A app.tasks:celery_app worker -l info &
cd ArticleGeneratorAdm && npm run dev &
```

- [ ] **Step 2: 走通完整流程**

浏览器访问 `http://localhost:5173/create`：
1. 选择有 `style_profile` 的账号
2. 输入想法 → 生成写作方向
3. **检查方向卡片**：每个卡片显示 ID + title（bold）+ core_viewpoint（灰色简介，最多 3 行）+ reader_gain + check + 底部彩色标签
4. 选择一个方向 → 生成大纲 → **检查步骤 4 显示 core_viewpoint**
5. 生成标题 → 生成全文
6. 全流程无控制台报错

- [ ] **Step 3: 验证 fallback**

在浏览器控制台手动注入只有 `{id, title}` 的旧方向数据：
```js
// 临时测试：确认 v-if 条件渲染不报错
```

确认卡片不显示空白行。

- [ ] **Step 4: 验证通过，完成**
