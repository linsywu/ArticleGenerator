# Materials Direction → Summary → CreateView Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 素材中心"创作方向"改为：AI 生成摘要 → 人工确认 → 选账号 → 跳转 `/create`。

**Architecture:** 新增 `material-summary` 场景配置 → 新增 Celery 任务 + API 端点 → 前端弹窗三态（加载/生成中/就绪）。MpMaterial 已有 summary 字段无需迁移。

**Tech Stack:** Python/Celery/httpx（后端）、Vue 3/Element Plus/Pinia（前端）

---

## 文件结构

| 操作 | 文件 | 职责 |
|------|------|------|
| 修改 | `scripts/seed_providers.py` | 加 material-summary 场景种子 |
| 修改 | `ArticleGeneratorService/app/tasks.py` | 新增 `trigger_material_summary` Celery 任务 |
| 修改 | `ArticleGeneratorService/app/api/materials.py` | 新增 `POST /{id}/generate-summary` 端点 |
| 重写 | `ArticleGeneratorAdm/src/components/MaterialsDirectionDialog.vue` | 摘要生成 + 账号选择 + 跳转 |
| 修改 | `ArticleGeneratorAdm/src/views/CreateView.vue` | 加自动跳步 |
| 新建 | `ArticleGeneratorService/tests/test_material_summary.py` | 单元测试 |

---

### Task 1: 新增 material-summary 场景种子

**Files:**
- Modify: `scripts/seed_providers.py`

- [ ] **Step 1: 在种子数据中添加 material-summary 配置**

在 direction 场景和 outline 场景之间插入：

```python
    # ── ⓪ 素材摘要 ──────────────────────────────────────────────────────────
    {
        "scenario": "material-summary",
        "model": "claude-sonnet-4-20250514",
        "system_prompt_template": (
            "你是一个专业的内容编辑。请将以下文章内容总结为简洁的摘要，"
            "保留核心观点和关键信息，150-300字。\n\n"
            "标题：{{title}}\n\n"
            "文章内容：\n{{content}}"
        ),
        "params": '{"max_tokens": 1024, "temperature": 0.5}',
        "priority": 10,
        "description": "⓪ 素材摘要：根据素材内容生成简洁摘要",
        "sort_order": 0,
    },
```

- [ ] **Step 2: Commit**

```bash
git add scripts/seed_providers.py
git commit -m "feat: add material-summary scenario seed config"
```

---

### Task 2: 新增 Celery 任务 + API 端点

**Files:**
- Modify: `ArticleGeneratorService/app/tasks.py`
- Modify: `ArticleGeneratorService/app/api/materials.py`

- [ ] **Step 1: 在 tasks.py 中新增 trigger_material_summary 任务**

在 `trigger_direction_generation` 任务之前添加：

```python
@celery_app.task(bind=True)
def trigger_material_summary(self, material_id: int, title: str, content: str):
    """生成素材摘要：标题+内容 → 150-300字摘要，落库"""
    db = SessionLocal()
    try:
        material = db.query(MpMaterial).filter(MpMaterial.id == material_id).first()
        if not material:
            raise ValueError(f"素材不存在: {material_id}")

        llm_url = settings.llm_service_url.rstrip("/")
        with httpx.Client(timeout=120.0) as client:
            resp = client.post(f"{llm_url}/chat", json={
                "scenario": "material-summary",
                "account_id": 0,
                "variables": {
                    "title": title or "",
                    "content": content or "",
                },
            })
            resp.raise_for_status()
            data = resp.json()

        summary = (data.get("content") or "").strip()
        if not summary:
            raise ValueError("摘要生成返回内容为空")

        # 保存到数据库
        material.summary = summary
        db.commit()

        return {"material_id": material_id, "summary": summary}
    finally:
        db.close()
```

- [ ] **Step 2: 在 materials.py 中新增 generate-summary 端点**

在现有路由中添加：

```python
from ..tasks import trigger_material_summary


@router.post("/{material_id}/generate-summary")
def generate_material_summary(material_id: int, db: Session = Depends(get_db)):
    """为素材生成 AI 摘要"""
    material = db.query(MpMaterial).filter(MpMaterial.id == material_id).first()
    if not material:
        raise HTTPException(status_code=404, detail="素材不存在")

    # 取内容：优先 markdown，其次 HTML
    content = material.content_markdown or ""
    if not content and material.content_html:
        # 简单 strip HTML tags
        content = re.sub(r'<[^>]+>', '', material.content_html)
    content = content[:3000]  # 限长

    task = trigger_material_summary.delay(
        material_id, material.title or "", content
    )
    return {"task_id": task.id, "status": "pending", "message": "摘要生成已提交"}
```

注意：需在文件顶部 import `re`（已存在）和导入 `trigger_material_summary`。

- [ ] **Step 3: Commit**

```bash
git add ArticleGeneratorService/app/tasks.py ArticleGeneratorService/app/api/materials.py
git commit -m "feat: add material summary generation endpoint and Celery task"
```

---

### Task 3: 前端 MaterialsDirectionDialog 重写

**Files:**
- Rewrite: `ArticleGeneratorAdm/src/components/MaterialsDirectionDialog.vue`
- Modify: `ArticleGeneratorAdm/src/api/client.ts`（如果 generateSummary 不存在）
- Modify: `ArticleGeneratorAdm/src/api/modules/materials.ts`（如果 generateSummary 不存在）

- [ ] **Step 1: 检查前端 API 接口**

检查 `ArticleGeneratorAdm/src/api/modules/materials.ts` 是否已有 `generateSummary` 方法。若不存在则添加：

```typescript
generateSummary: (materialId: number, title: string, content: string) =>
    post<{ task_id: string; status: string; message: string }>(
      `/materials/${materialId}/generate-summary`,
      { title, content }
    ),
```

- [ ] **Step 2: 重写 MaterialsDirectionDialog.vue**

完整替换为三态弹窗：

```vue
<template>
  <el-dialog
    :model-value="modelValue"
    @update:model-value="$emit('update:modelValue', $event)"
    :title="dialogTitle"
    width="650px"
    :close-on-click-modal="false"
    @open="onOpen"
    @close="onClose"
  >
    <!-- 状态 1: 加载素材内容 -->
    <div v-if="loadingContent" class="state-box">
      <div class="spinner"></div>
      <p>加载素材内容...</p>
    </div>

    <!-- 状态 2: 正在生成摘要 -->
    <div v-else-if="generatingSummary" class="state-box">
      <div class="spinner"></div>
      <p>正在生成摘要...</p>
    </div>

    <!-- 状态 3: 就绪 — 摘要 + 账号选择 -->
    <div v-else class="ready-layout">
      <!-- 摘要区域 -->
      <div class="section">
        <div class="section-header">
          <label class="section-label">AI 摘要</label>
          <el-button
            size="small"
            text
            :loading="generatingSummary"
            @click="startSummaryGeneration"
          >
            🔄 重新生成
          </el-button>
        </div>
        <el-input
          v-model="summary"
          type="textarea"
          :rows="4"
          placeholder="摘要内容..."
        />
        <p v-if="summaryError" class="error-text">{{ summaryError }}</p>
      </div>

      <!-- 账号选择区域 -->
      <div class="section">
        <label class="section-label">选择写作账号</label>
        <div
          v-for="acc in accounts"
          :key="acc.id"
          class="account-option"
          :class="{ selected: selectedAccountId === acc.id }"
          @click="selectedAccountId = acc.id"
        >
          <div class="account-avatar">{{ acc.account_name.charAt(0) }}</div>
          <div class="account-info">
            <span class="account-name">{{ acc.account_name }}</span>
            <span class="account-platform">{{ acc.platform }}</span>
          </div>
          <span class="account-badge" :class="{ ready: acc.style_profile_status === 'ready' }">
            {{ acc.style_profile_status === 'ready' ? '画像就绪' : '待蒸馏' }}
          </span>
          <span v-if="selectedAccountId === acc.id" class="account-check">✓</span>
        </div>
        <p v-if="!accounts.length" class="no-data">暂无可用账号</p>
      </div>
    </div>

    <template #footer>
      <el-button @click="$emit('update:modelValue', false)">取消</el-button>
      <el-button
        type="primary"
        :disabled="!selectedAccountId || !summary.trim()"
        @click="goCreate"
      >
        确认 · 去创作
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, computed } from "vue";
import { useRouter } from "vue-router";
import materialsApi from "@/api/modules/materials";
import { api } from "@/api/client";
import { useAccountsStore } from "@/store/accounts";
import type { MpMaterial } from "@/api/types";

const props = defineProps<{
  modelValue: boolean;
  material: MpMaterial | null;
}>();

const emit = defineEmits<{
  "update:modelValue": [value: boolean];
}>();

const router = useRouter();
const accountsStore = useAccountsStore();

const accounts = computed(() => accountsStore.accounts);
const selectedAccountId = ref<number | null>(null);
const summary = ref("");
const summaryError = ref("");
const loadingContent = ref(false);
const generatingSummary = ref(false);
let generationCancelled = false;

function stripHtml(html: string): string {
  if (!html) return "";
  return html.replace(/<[^>]+>/g, "").replace(/&[a-z]+;/g, " ").trim();
}

const dialogTitle = computed(() => {
  return props.material?.title
    ? `创作方向 - ${props.material.title.slice(0, 30)}${props.material.title.length > 30 ? "..." : ""}`
    : "创作方向";
});

async function onOpen() {
  if (!props.material) return;

  loadingContent.value = true;
  summary.value = "";
  summaryError.value = "";
  selectedAccountId.value = null;

  try {
    await accountsStore.fetch();

    // 获取素材详情
    const { data: detail } = await materialsApi.getMaterial(props.material.id);

    // 如果已有摘要，直接展示
    if (detail.summary && detail.summary !== "———" && detail.summary.trim().length > 5) {
      summary.value = detail.summary;
    } else {
      // 没有摘要，自动生成
      await startSummaryGeneration(detail);
    }
  } catch (e: any) {
    summaryError.value = "加载素材详情失败";
  } finally {
    loadingContent.value = false;
  }
}

function onClose() {
  generationCancelled = true;
  summary.value = "";
  summaryError.value = "";
  selectedAccountId.value = null;
  loadingContent.value = false;
  generatingSummary.value = false;
}

async function startSummaryGeneration(detail?: any) {
  if (!props.material) return;

  const materialDetail = detail || (await materialsApi.getMaterial(props.material.id)).data;
  const title = materialDetail.title || props.material.title || "";
  const markdown = materialDetail.content_markdown || "";
  const html = materialDetail.content_html || "";
  const content = markdown || stripHtml(html) || "";

  if (!content && !title) {
    summaryError.value = "素材内容为空，无法生成摘要";
    return;
  }

  generationCancelled = false;
  generatingSummary.value = true;
  summaryError.value = "";

  try {
    const { data } = await materialsApi.generateSummary(
      props.material.id, title, content
    );
    const taskId = (data as any).task_id;
    if (!taskId) throw new Error("未获取到任务 ID");

    // 轮询
    let attempts = 0;
    while (attempts < 30) {
      await new Promise((r) => setTimeout(r, 2000));
      if (generationCancelled) return;
      const { data: taskData } = await api.getTaskResult(taskId);
      if (generationCancelled) return;
      if (taskData.status === "success") {
        summary.value = (taskData as any).result?.summary || "";
        return;
      }
      if (taskData.status === "failed") {
        throw new Error((taskData as any).error_message || "摘要生成失败");
      }
      attempts++;
    }
    throw new Error("摘要生成超时，请重试");
  } catch (e: any) {
    summaryError.value = e?.response?.data?.detail || e?.message || "摘要生成失败";
  } finally {
    generatingSummary.value = false;
  }
}

function goCreate() {
  if (!selectedAccountId.value || !summary.value.trim()) return;

  emit("update:modelValue", false);
  router.push({
    path: "/create",
    query: {
      idea: summary.value.trim(),
      account_id: String(selectedAccountId.value),
    },
  });
}
</script>

<style scoped>
.state-box {
  text-align: center;
  padding: 40px;
  color: var(--text-muted);
}
.state-box p { margin-top: 16px; font-size: 14px; }

.spinner {
  width: 40px;
  height: 40px;
  border: 3px solid var(--ink-border, #e0e0e0);
  border-top-color: var(--amber, #c8843c);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  margin: 0 auto;
}
@keyframes spin { to { transform: rotate(360deg); } }

.ready-layout {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.section {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.section-label {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-on-dark, #333);
}

.error-text {
  color: #e53935;
  font-size: 13px;
}

.account-option {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 12px 16px;
  background: var(--ink-surface, #f5f5f5);
  border: 1px solid var(--ink-border, #e0e0e0);
  border-radius: 8px;
  cursor: pointer;
  transition: border-color 0.2s, background-color 0.2s;
  position: relative;
}
.account-option:hover { border-color: var(--text-dim, #999); }
.account-option.selected {
  border-color: var(--amber, #c8843c);
  background: rgba(200, 132, 60, 0.06);
}

.account-avatar {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: var(--amber, #c8843c);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  font-weight: 700;
  flex-shrink: 0;
}
.account-info { flex: 1; display: flex; flex-direction: column; gap: 2px; }
.account-name { font-size: 15px; font-weight: 600; color: var(--text-on-dark, #333); }
.account-platform { font-size: 12px; color: var(--text-muted, #999); }

.account-badge {
  font-size: 12px;
  padding: 2px 8px;
  border-radius: 4px;
  background: var(--ink-border, #e0e0e0);
  color: var(--text-muted, #999);
}
.account-badge.ready { background: rgba(76, 175, 80, 0.12); color: #388e3c; }

.account-check {
  position: absolute;
  top: 8px;
  right: 12px;
  color: var(--amber, #c8843c);
  font-weight: 700;
  font-size: 18px;
}

.no-data { text-align: center; color: var(--text-muted); padding: 20px; }
</style>
```

- [ ] **Step 3: 确认前端 API 模块**

检查 `ArticleGeneratorAdm/src/api/modules/materials.ts`，确保 `generateSummary` 方法存在：

```typescript
generateSummary: (materialId: number, title: string, content: string) =>
    post<{ task_id: string; status: string; message: string }>(
      `/materials/${materialId}/generate-summary`,
      { title, content }
    ),
```

- [ ] **Step 4: 构建验证**

```bash
cd ArticleGeneratorAdm && npx vite build --mode production 2>&1 | tail -10
```

- [ ] **Step 5: Commit**

```bash
git add ArticleGeneratorAdm/src/components/MaterialsDirectionDialog.vue ArticleGeneratorAdm/src/api/modules/materials.ts
git commit -m "feat: rewrite materials direction dialog with AI summary + account selector"
```

---

### Task 4: CreateView 自动跳步 + 后端测试

**Files:**
- Modify: `ArticleGeneratorAdm/src/views/CreateView.vue:385-389`
- Create: `ArticleGeneratorService/tests/test_material_summary.py`

- [ ] **Step 1: CreateView 加自动跳步**

在 `onMounted` 中 `route.query.idea` 处理后添加：

```typescript
    // Auto-advance to step 1 when account is pre-filled from query
    if (route.query.account_id && selectedAccountId.value) {
      currentStep.value = 1
    }
```

- [ ] **Step 2: 后端单元测试**

创建 `ArticleGeneratorService/tests/test_material_summary.py`：

```python
"""Test material summary generation task"""
from unittest.mock import patch, MagicMock
import pytest
from app.tasks import trigger_material_summary
from app.models import MpMaterial, MpAccount
from app.database import SessionLocal


def _mock_chat_response(content: str):
    mock_resp = MagicMock()
    mock_resp.raise_for_status.return_value = None
    mock_resp.json.return_value = {"content": content}
    return mock_resp


def test_generate_summary_saves_to_db():
    """摘要生成后落库"""
    db = SessionLocal()
    acc = MpAccount(name="test_summary", platform="公众号", fakeid="test123")
    db.add(acc)
    db.commit()

    material = MpMaterial(
        account_id=acc.id,
        title="测试文章",
        original_url="https://example.com/test",
        content_markdown="这是一篇测试文章的内容。",
    )
    db.add(material)
    db.commit()
    mat_id = material.id
    acc_id = acc.id
    db.close()

    with patch("app.tasks.httpx.Client") as mock_client:
        mock_instance = MagicMock()
        mock_client.return_value.__enter__.return_value = mock_instance
        mock_instance.post.return_value = _mock_chat_response("AI 生成的摘要内容")

        result = trigger_material_summary(mat_id, "测试文章", "内容...")

    assert result["summary"] == "AI 生成的摘要内容"

    db = SessionLocal()
    mat = db.query(MpMaterial).filter(MpMaterial.id == mat_id).first()
    assert mat.summary == "AI 生成的摘要内容"
    db.close()


def test_empty_response_raises():
    """LLM 返回空内容时抛错"""
    db = SessionLocal()
    acc = MpAccount(name="test_empty", platform="公众号", fakeid="test456")
    db.add(acc)
    db.commit()
    material = MpMaterial(
        account_id=acc.id,
        title="空测试",
        original_url="https://example.com/empty",
        content_markdown="空内容测试",
    )
    db.add(material)
    db.commit()
    mat_id = material.id
    acc_id = acc.id
    db.close()

    with patch("app.tasks.httpx.Client") as mock_client:
        mock_instance = MagicMock()
        mock_client.return_value.__enter__.return_value = mock_instance
        mock_instance.post.return_value = _mock_chat_response("")

        with pytest.raises(ValueError, match="摘要生成返回内容为空"):
            trigger_material_summary(mat_id, "空测试", "空")
```

- [ ] **Step 3: 运行测试**

```bash
cd ArticleGeneratorService && python3 -m pytest tests/test_material_summary.py -v
```

- [ ] **Step 4: Commit**

```bash
git add ArticleGeneratorAdm/src/views/CreateView.vue ArticleGeneratorService/tests/test_material_summary.py
git commit -m "feat: auto-advance create step + material summary tests"
```

---

### Task 5: 验证

- [ ] **Step 1: 部署**

- 在 `/scenario-configs` 确认 `material-summary` 场景存在（或运行 seed）
- 重启 Celery worker 加载新任务代码

- [ ] **Step 2: 浏览器验证**

1. 素材中心 → 点击"创作方向"
2. 确认弹窗先显示"加载素材内容..."→ 然后"正在生成摘要..."
3. 确认摘要生成完成，textarea 可编辑
4. "🔄 重新生成"按钮可重新生成
5. 选择账号 → 点击"确认 · 去创作"
6. 确认跳转到 `/create?idea=<摘要>&account_id=<id>`
7. 确认直接显示步骤 1（输入想法），想法已预填为摘要
8. 点击"生成写作方向" → 正常走后续流程

- [ ] **Step 3: 直接访问 /create 不受影响**

1. 浏览器访问 `/create`（无 query 参数）
2. 确认从步骤 0 正常开始
