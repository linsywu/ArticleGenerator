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
            @click="startSummaryGeneration()"
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
        <p v-if="!accounts.length && !loadingContent" class="no-data">暂无可用账号</p>
      </div>
    </div>

    <template #footer>
      <el-button @click="$emit('update:modelValue', false)">取消</el-button>
      <el-button
        type="primary"
        :disabled="!selectedAccountId || !summary.trim() || generatingSummary || loadingContent"
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

    // 如果已有摘要，直接展示；否则自动生成
    if (detail.summary && detail.summary !== "———" && detail.summary.trim().length > 5) {
      summary.value = detail.summary;
    } else {
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

  let materialDetail = detail;
  if (!materialDetail) {
    const { data } = await materialsApi.getMaterial(props.material.id);
    materialDetail = data;
  }

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
