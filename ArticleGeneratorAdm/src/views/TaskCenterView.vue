<template>
  <div class="task-center">
    <header class="page-header">
      <div class="page-header-text">
        <h1 class="page-title">任务中心</h1>
        <p class="page-subtitle">实时跟踪生成、微调等任务的执行状态</p>
      </div>
      <div class="page-header-counts">
        <span class="count-badge running" v-if="activeRunningCount > 0">
          <span class="count-dot"></span>
          {{ activeRunningCount }} 进行中
        </span>
        <span class="count-badge pending" v-if="activePendingCount > 0">
          {{ activePendingCount }} 排队中
        </span>
      </div>
    </header>

    <!-- 进行中 -->
    <section class="task-section" v-if="runningTasks.length > 0">
      <h2 class="section-title">
        <span class="section-icon">▶</span>
        进行中
        <span class="section-count">{{ runningTasks.length }}</span>
      </h2>
      <div class="task-cards">
        <div v-for="t in runningTasks" :key="t.task_id" class="task-card running">
          <div class="card-left">
            <span class="task-icon">{{ typeIcon(t.task_type) }}</span>
          </div>
          <div class="card-body">
            <div class="card-header-row">
              <span class="task-type-label">{{ typeLabel(t.task_type) }}</span>
              <span class="status-badge running">
                <span class="status-dot"></span>
                运行中
                <span class="elapsed-timer">{{ elapsedTime(t) }}</span>
              </span>
            </div>
            <div class="target-text">{{ t.target }}</div>
            <div class="card-meta">
              <span v-if="t.account_name" class="meta-item">
                <span class="meta-icon">☺</span>
                {{ t.account_name }}
              </span>
              <span v-if="t.extra_info" class="meta-item">
                <span class="meta-icon">◈</span>
                {{ t.extra_info }}
              </span>
              <span class="meta-item meta-time">{{ formatTime(t.created_at) }}</span>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- 等待中 -->
    <section class="task-section" v-if="pendingTasks.length > 0">
      <h2 class="section-title">
        <span class="section-icon">▷</span>
        等待中
        <span class="section-count">{{ pendingTasks.length }}</span>
      </h2>
      <div class="task-cards">
        <div v-for="t in pendingTasks" :key="t.task_id" class="task-card pending">
          <div class="card-left">
            <span class="task-icon">{{ typeIcon(t.task_type) }}</span>
          </div>
          <div class="card-body">
            <div class="card-header-row">
              <span class="task-type-label">{{ typeLabel(t.task_type) }}</span>
              <span class="status-badge pending">排队中</span>
            </div>
            <div class="target-text">{{ t.target }}</div>
            <div class="card-meta">
              <span v-if="t.account_name" class="meta-item">
                <span class="meta-icon">☺</span>
                {{ t.account_name }}
              </span>
              <span v-if="t.extra_info" class="meta-item">
                <span class="meta-icon">◈</span>
                {{ t.extra_info }}
              </span>
              <span class="meta-item meta-time">{{ formatTime(t.created_at) }}</span>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- 已完成 -->
    <section class="task-section" v-if="completedTasks.length > 0">
      <h2 class="section-title collapsible" @click="showCompleted = !showCompleted">
        <span class="section-icon" :class="{ rotated: showCompleted }">▸</span>
        已完成
        <span class="section-count">{{ completedTasks.length }}</span>
      </h2>
      <div v-show="showCompleted" class="task-cards">
        <div v-for="t in completedTasks" :key="t.task_id" class="task-card completed">
          <div class="card-left">
            <span class="task-icon">{{ typeIcon(t.task_type) }}</span>
          </div>
          <div class="card-body">
            <div class="card-header-row">
              <span class="task-type-label">{{ typeLabel(t.task_type) }}</span>
              <span
                class="status-badge"
                :class="t.status"
              >{{ statusText(t.status) }}</span>
            </div>
            <div class="target-text">{{ t.target }}</div>
            <div class="card-meta">
              <span v-if="t.account_name" class="meta-item">
                <span class="meta-icon">☺</span>
                {{ t.account_name }}
              </span>
              <span v-if="t.extra_info" class="meta-item">
                <span class="meta-icon">◈</span>
                {{ t.extra_info }}
              </span>
              <span class="meta-item meta-time">{{ formatTime(t.created_at) }}</span>
            </div>
            <div v-if="t.error_message" class="error-msg">{{ t.error_message }}</div>
          </div>
        </div>
      </div>
    </section>

    <!-- 空状态 -->
    <div v-if="loading && tasks.length === 0" class="empty-state">
      <div class="empty-spinner"></div>
      <p>加载中...</p>
    </div>
    <div v-else-if="tasks.length === 0" class="empty-state">
      <p class="empty-icon">⌛</p>
      <p class="empty-text">暂无任务</p>
      <p class="empty-hint">在创作页面选择热点并生成文章后，任务将在此展示</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from "vue";
import { api, type UnifiedTaskItem } from "@/api/client";
import { formatDateTime, relativeTime } from "@/utils/format";
import { storeToRefs } from "pinia";
import { useTasksStore } from "@/store/tasks";

const tasks = ref<UnifiedTaskItem[]>([]);
const loading = ref(true);
const showCompleted = ref(false);
const now = ref(Date.now());

// 活跃任务信息（来自 Pinia store，用于头部徽章）
const tasksStore = useTasksStore();
const { runningCount: activeRunningCount, pendingCount: activePendingCount } = storeToRefs(tasksStore);

// 全量任务列表的轮询
let listPollTimer: ReturnType<typeof setInterval> | null = null;
let clockTimer: ReturnType<typeof setInterval> | null = null;

const runningTasks = computed(() => tasks.value.filter(t => t.status === "running"));
const pendingTasks = computed(() => tasks.value.filter(t => t.status === "pending"));
const completedTasks = computed(() =>
  tasks.value.filter(t => ["success", "failed", "cancelled"].includes(t.status))
);
const hasActive = computed(() => runningTasks.value.length > 0 || pendingTasks.value.length > 0);

const TASK_TYPE_ICONS: Record<string, string> = {
  generate: "✏️",
  refine: "🔧",
  humanize: "📝",
  distill: "🧪",
  direction: "💡",
  outline: "📋",
  quality_review: "✅",
  compliance_review: "🛡️",
  title: "🎯",
};

const TASK_TYPE_LABELS: Record<string, string> = {
  generate: "文章生成",
  refine: "文章微调",
  humanize: "内容拟人化",
  distill: "风格蒸馏",
  direction: "方向生成",
  outline: "大纲生成",
  title: "标题生成",
  quality_review: "质量评审",
  compliance_review: "合规审查",
};

function typeIcon(type: string): string {
  return TASK_TYPE_ICONS[type] || "⚙";
}

function typeLabel(type: string): string {
  return TASK_TYPE_LABELS[type] || type;
}

function statusText(status: string): string {
  const map: Record<string, string> = {
    success: "已完成",
    failed: "失败",
    cancelled: "已取消",
    running: "运行中",
    pending: "排队中",
  };
  return map[status] || status;
}

function formatTime(iso: string): string {
  return relativeTime(iso);
}

function elapsedTime(task: UnifiedTaskItem): string {
  if (!task.created_at) return "";
  const start = new Date(task.created_at).getTime();
  const elapsed = Math.floor((now.value - start) / 1000);
  if (elapsed < 60) return `${elapsed}秒`;
  const min = Math.floor(elapsed / 60);
  const sec = elapsed % 60;
  return `${min}分${sec}秒`;
}

async function loadTasks() {
  try {
    const params: { status?: string; limit?: number } = {};
    const { data } = await api.getUnifiedTasks({ status: "running,pending,success,failed", limit: 50 });
    tasks.value = data.tasks;
    if (hasActive.value && completedTasks.value.length > 0) {
      showCompleted.value = false;
    } else if (completedTasks.value.length > 0) {
      showCompleted.value = true;
    }
  } catch (e) {
    console.error("加载任务失败", e);
  } finally {
    loading.value = false;
  }
}

function startListPolling() {
  if (listPollTimer) clearInterval(listPollTimer);
  listPollTimer = setInterval(loadTasks, 3000);
}

onMounted(() => {
  loadTasks();
  if (hasActive.value) {
    startListPolling();
  }
  clockTimer = setInterval(() => {
    now.value = Date.now();
  }, 1000);
});

onUnmounted(() => {
  if (listPollTimer) clearInterval(listPollTimer);
  if (clockTimer) clearInterval(clockTimer);
});
</script>

<style scoped>
.task-center {
  max-width: 800px;
  margin: 0 auto;
  padding-bottom: var(--space-2xl);
}

/* Page header */
.page-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: var(--space-xl);
  gap: var(--space-md);
}
.page-title {
  font-family: var(--font-serif);
  font-size: 28px;
  font-weight: 900;
  color: var(--text-on-dark);
  letter-spacing: 1px;
  margin-bottom: 4px;
}
.page-subtitle {
  font-size: 14px;
  color: var(--text-muted);
}
.page-header-counts {
  display: flex;
  gap: 8px;
  flex-shrink: 0;
}
.count-badge {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 14px;
  border-radius: 20px;
  font-size: 12px;
  font-weight: 600;
}
.count-badge.running {
  background: rgba(200, 132, 60, 0.12);
  color: var(--amber-light);
  border: 1px solid rgba(200, 132, 60, 0.25);
}
.count-badge.pending {
  background: rgba(90, 125, 154, 0.12);
  color: var(--blue-muted);
  border: 1px solid rgba(90, 125, 154, 0.25);
}
.count-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--amber-light);
  animation: pulse-dot 1.5s ease-in-out infinite;
}
@keyframes pulse-dot {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.3; }
}

/* Sections */
.task-section {
  margin-bottom: var(--space-xl);
}
.section-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-family: var(--font-serif);
  font-size: 18px;
  font-weight: 700;
  color: var(--text-on-dark);
  margin-bottom: var(--space-md);
  cursor: default;
}
.section-title.collapsible {
  cursor: pointer;
  user-select: none;
}
.section-icon {
  font-size: 14px;
  color: var(--text-dim);
  transition: transform var(--duration-fast) var(--ease-out);
}
.section-icon.rotated {
  transform: rotate(90deg);
}
.section-count {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-muted);
  background: var(--ink-surface);
  padding: 1px 8px;
  border-radius: 10px;
  margin-left: 4px;
}

/* Cards */
.task-cards {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.task-card {
  display: flex;
  gap: 14px;
  padding: 16px 18px;
  background: var(--ink-mid);
  border: 1px solid var(--ink-border);
  border-radius: var(--radius-lg);
  transition: all var(--duration-fast) var(--ease-out);
}
.task-card:hover {
  border-color: var(--text-dim);
}
.task-card.running {
  border-left: 3px solid var(--amber);
}
.task-card.pending {
  border-left: 3px solid var(--blue-muted);
}
.task-card.completed.success {
  border-left: 3px solid var(--green-muted);
  opacity: 0.85;
}
.task-card.completed.failed {
  border-left: 3px solid var(--red-muted);
}

.card-left {
  flex-shrink: 0;
  padding-top: 2px;
}
.task-icon {
  font-size: 20px;
  line-height: 1;
}
.card-body {
  flex: 1;
  min-width: 0;
}
.card-header-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 6px;
  gap: 8px;
}
.task-type-label {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-on-dark);
}
.target-text {
  font-size: 15px;
  color: var(--text-on-dark);
  font-weight: 500;
  margin-bottom: 8px;
  line-height: 1.4;
  word-break: break-word;
}
.card-meta {
  display: flex;
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;
}
.meta-item {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: var(--text-muted);
}
.meta-icon {
  font-size: 11px;
  opacity: 0.7;
}
.meta-time {
  font-size: 11px;
  color: var(--text-dim);
}

/* Status badges */
.status-badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 11px;
  font-weight: 600;
  padding: 2px 10px;
  border-radius: 20px;
  white-space: nowrap;
  flex-shrink: 0;
}
.status-badge.running {
  background: rgba(200, 132, 60, 0.1);
  color: var(--amber-light);
  border: 1px solid rgba(200, 132, 60, 0.2);
}
.status-badge.pending {
  background: rgba(90, 125, 154, 0.1);
  color: var(--blue-muted);
  border: 1px solid rgba(90, 125, 154, 0.2);
}
.status-badge.success {
  background: rgba(91, 140, 90, 0.1);
  color: var(--green-muted);
  border: 1px solid rgba(91, 140, 90, 0.2);
}
.status-badge.failed {
  background: rgba(184, 84, 80, 0.1);
  color: var(--red-muted);
  border: 1px solid rgba(184, 84, 80, 0.2);
}
.status-badge.cancelled {
  background: rgba(92, 88, 96, 0.15);
  color: var(--text-dim);
  border: 1px solid rgba(92, 88, 96, 0.2);
}
.status-dot {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: var(--amber-light);
  animation: pulse-dot 1.5s ease-in-out infinite;
}
.elapsed-timer {
  font-variant-numeric: tabular-nums;
  opacity: 0.8;
}

/* Error message */
.error-msg {
  margin-top: 8px;
  padding: 8px 12px;
  background: rgba(184, 84, 80, 0.08);
  border: 1px solid rgba(184, 84, 80, 0.15);
  border-radius: var(--radius-sm);
  font-size: 12px;
  color: var(--red-muted);
  word-break: break-word;
}

/* Empty state */
.empty-state {
  text-align: center;
  padding: var(--space-2xl);
  color: var(--text-muted);
}
.empty-icon {
  font-size: 48px;
  margin-bottom: 12px;
}
.empty-text {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-dim);
  margin-bottom: 6px;
}
.empty-hint {
  font-size: 13px;
  color: var(--text-dim);
}
.empty-spinner {
  width: 32px;
  height: 32px;
  border: 2px solid var(--ink-border);
  border-top-color: var(--amber);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  margin: 0 auto 12px;
}
@keyframes spin {
  to { transform: rotate(360deg); }
}
</style>
