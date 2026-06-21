<template>
  <el-dialog
    v-model="visible"
    :title="`风格蒸馏 · ${account?.account_name || ''}`"
    width="960px"
    :close-on-click-modal="false"
    @close="stopPolling"
  >
    <div class="distill-layout">
      <!-- Left: Reference Articles -->
      <div class="distill-left">
        <div class="distill-left-header">
          <h4>参考文章</h4>
          <el-button v-if="!isRunning" size="small" @click="openArticleForm()">＋ 添加</el-button>
        </div>
        <div v-if="articles.length" class="distill-article-list" :class="{ readonly: isRunning }">
          <div v-for="a in articles" :key="a.id" class="distill-article-item">
            <div class="distill-article-item-content">
              <div class="distill-article-title">{{ a.title }}</div>
              <div class="distill-article-meta">
                {{ a.content ? a.content.length : 0 }} 字
                <span v-if="a.is_benchmark" class="tag-benchmark">代表篇</span>
              </div>
            </div>
            <div v-if="!isRunning" class="distill-article-actions">
              <el-button size="small" text @click="openArticleForm(a)">编辑</el-button>
              <el-button size="small" text type="danger" @click="deleteArticle(a)">删除</el-button>
            </div>
          </div>
        </div>
        <div v-else class="empty-hint">暂无参考文章，请先添加</div>
      </div>

      <!-- Right: Style Profile + Progress -->
      <div class="distill-right">
        <div class="distill-right-header">
          <h4>风格画像</h4>
          <span v-if="status === 'completed'" class="status-tag ready">画像就绪 v{{ account?.style_profile_version }}</span>
          <span v-else-if="status === 'running'" class="status-tag running">蒸馏中...</span>
          <span v-else-if="status === 'failed'" class="status-tag failed">失败</span>
        </div>

        <!-- Idle / Empty -->
        <div v-if="status === 'idle'" class="distill-center">
          <p v-if="!articles.length" class="empty-hint">请先在左侧添加参考文章</p>
          <div v-else-if="account?.style_profile_structured" class="profile-content-area">
            <div v-for="dim in styleDimensions" :key="dim.key" class="dim-content-card">
              <div class="dim-content-header">
                <span>{{ dim.icon }} {{ dim.label }}</span>
              </div>
              <p class="dim-content-text">{{ getDimContent(dim.key) || '未定义' }}</p>
            </div>
          </div>
          <p v-else class="empty-hint">点击下方按钮开始蒸馏</p>
        </div>

        <!-- Running progress -->
        <div v-else-if="status === 'running'" class="distill-center">
          <div style="text-align:center;width:100%;">
            <div style="font-size:32px;animation:pulse 1.5s infinite;">⏳</div>
            <h4 style="margin:12px 0;">正在蒸馏风格...</h4>
            <div class="progress-bar">
              <div class="progress-fill" :style="{ width: progressPercent + '%' }"></div>
            </div>
            <p class="progress-text">已完成 {{ progress.completed }}/{{ progress.total }} 维度</p>
            <p class="progress-dim">正在分析：{{ progress.current_dimension }}</p>
            <p class="progress-eta">预计还需 {{ etaSeconds }} 秒</p>
            <div class="dimension-status-grid">
              <div v-for="dim in dimensionStatusList" :key="dim.key" class="dim-status-item" :class="dim.state">
                <span>{{ dim.icon }} {{ dim.label }}</span>
                <span v-if="dim.state === 'done'">✓</span>
                <span v-else-if="dim.state === 'active'" class="active-dot">●</span>
                <span v-else>○</span>
              </div>
            </div>
          </div>
        </div>

        <!-- Completed -->
        <div v-else-if="status === 'completed'" class="distill-center">
          <div class="profile-content-area">
            <div v-for="dim in styleDimensions" :key="dim.key" class="dim-content-card">
              <div class="dim-content-header">
                <span>{{ dim.icon }} {{ dim.label }}</span>
              </div>
              <p class="dim-content-text">{{ getDimContent(dim.key) || '未定义' }}</p>
            </div>
          </div>
        </div>

        <!-- Failed -->
        <div v-else-if="status === 'failed'" class="distill-center">
          <div style="text-align:center;">
            <div style="font-size:32px;">❌</div>
            <h4 style="color:#cf1322;margin:8px 0;">蒸馏失败</h4>
            <p style="font-size:13px;color:var(--text-dim);margin-bottom:8px;">{{ errorMessage }}</p>
            <el-button size="small" text @click="showDetail = !showDetail">{{ showDetail ? '收起' : '查看详情' }}</el-button>
            <pre v-if="showDetail" class="error-detail">{{ errorMessage }}</pre>
          </div>
        </div>

        <!-- Timeout -->
        <div v-else-if="status === 'timeout'" class="distill-center">
          <div style="text-align:center;">
            <div style="font-size:32px;">⏰</div>
            <h4 style="margin:8px 0;">蒸馏超时</h4>
            <p style="font-size:13px;color:var(--text-dim);">5 分钟内未完成，请稍后重试</p>
          </div>
        </div>

        <!-- Action button -->
        <div class="distill-action-bar">
          <el-button
            v-if="status !== 'running'"
            type="primary"
            :disabled="!articles.length"
            :loading="distillLoading"
            @click="triggerDistill"
          >
            {{ account?.style_profile_structured ? '🔄 重新蒸馏' : '🔥 开始蒸馏' }}
          </el-button>
          <el-button v-if="status === 'failed' || status === 'timeout'" type="primary" :loading="distillLoading" @click="retryDistill">
            🔄 重试蒸馏
          </el-button>
        </div>
      </div>
    </div>

    <!-- Article sub-dialog -->
    <el-dialog v-model="articleFormVisible" :title="editingArticleId ? '编辑文章' : '添加文章'" width="720px" append-to-body>
      <ReferenceArticleForm ref="articleFormRef" :article="editingArticleData" />
      <template #footer>
        <el-button @click="articleFormVisible = false">取消</el-button>
        <el-button type="primary" :loading="savingArticle" @click="saveArticle">保存</el-button>
      </template>
    </el-dialog>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, computed, watch, onUnmounted } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { api } from "@/api/client";
import type { Account, ReferenceArticle } from "@/api/types";
import ReferenceArticleForm from "./ReferenceArticleForm.vue";

const props = defineProps<{ modelValue: boolean; account: Account | null }>();
const emit = defineEmits<{
  (e: "update:modelValue", v: boolean): void;
  (e: "profile-updated"): void;
}>();

const styleDimensions = [
  { key: "thinking_pattern", label: "思维特征", icon: "🧠" },
  { key: "structure_pattern", label: "结构模式", icon: "🏗️" },
  { key: "sentence_pattern", label: "句式特征", icon: "✍️" },
  { key: "vocabulary_pattern", label: "词汇偏好", icon: "📝" },
  { key: "evidence_type", label: "论据类型", icon: "📊" },
  { key: "taboos", label: "禁忌清单", icon: "🚫" },
  { key: "blank_leaving", label: "留白程度", icon: "💭" },
];

function getDimContent(key: string): string {
  const profile = props.account?.style_profile_structured;
  if (!profile || typeof profile !== "object") return "";
  return (profile as Record<string, string>)[key] || "";
}

const visible = ref(props.modelValue);
watch(() => props.modelValue, (v) => { visible.value = v; if (v) { dialogOpen = true; onOpen(); } });
watch(visible, (v) => { emit("update:modelValue", v); if (!v) { dialogOpen = false; stopPolling(); } });

const articles = ref<ReferenceArticle[]>([]);
const status = ref<"idle" | "running" | "completed" | "failed" | "timeout">("idle");
const progress = ref({ completed: 0, total: 7, current_dimension: "" });
const errorMessage = ref("");
const distillLoading = ref(false);
const showDetail = ref(false);

let pollTimer: ReturnType<typeof setInterval> | null = null;
let startTime = 0;
let pollErrorCount = 0;
let dialogOpen = false;  // guard against async onOpen race

const isRunning = computed(() => status.value === "running");
const progressPercent = computed(() => {
  if (progress.value.total === 0) return 0;
  return Math.round((progress.value.completed / progress.value.total) * 100);
});
const etaSeconds = computed(() => {
  if (progress.value.completed === 0) return 60;
  const elapsed = (Date.now() - startTime) / 1000;
  if (elapsed < 1) return 60;
  const rate = elapsed / progress.value.completed;
  return Math.max(1, Math.round(rate * (progress.value.total - progress.value.completed)));
});

const dimensionStatusList = computed(() => {
  return styleDimensions.map((dim, i) => ({
    ...dim,
    state: i < progress.value.completed ? "done" : i === progress.value.completed ? "active" : "pending",
  }));
});

// Article sub-form
const articleFormVisible = ref(false);
const editingArticleId = ref<number | null>(null);
const savingArticle = ref(false);
const articleFormRef = ref<InstanceType<typeof ReferenceArticleForm>>();
const editingArticleData = computed(() => {
  if (editingArticleId.value) {
    const a = articles.value.find(x => x.id === editingArticleId.value);
    if (a) return { title: a.title, content: a.content, source_url: a.source_url || "", is_benchmark: !!a.is_benchmark };
  }
  return null;
});

async function loadArticles() {
  if (!props.account?.id) return;
  try {
    const { data } = await api.getReferenceArticles(props.account.id);
    articles.value = data;
  } catch { articles.value = []; }
}

async function onOpen() {
  await loadArticles();
  if (!dialogOpen) return;  // dialog was closed during loadArticles
  await checkStatus();
  if (!dialogOpen) return;  // dialog was closed during checkStatus
  if (status.value === "running") startPolling();
}

async function checkStatus() {
  if (!props.account?.id) return;
  try {
    const { data } = await api.getDistillStatus(props.account.id);
    pollErrorCount = 0;  // reset error count on success
    if (data.status === "running") {
      status.value = "running";
      if (data.progress) progress.value = data.progress;
      if (startTime === 0) startTime = Date.now();
    } else if (data.status === "completed") {
      status.value = "completed";
      stopPolling();
    } else if (data.status === "failed") {
      status.value = "failed";
      errorMessage.value = data.error || "未知错误";
      stopPolling();
    } else {
      // Treat unknown status as idle (don't kill polling if already running)
      if (status.value !== "running") {
        status.value = "idle";
      }
    }
  } catch {
    pollErrorCount++;
    // Only kill polling after 3 consecutive network errors
    if (pollErrorCount >= 3) {
      status.value = "idle";
      stopPolling();
      ElMessage.error("无法获取蒸馏状态，请检查网络后重试");
    }
  }
}

function startPolling() {
  stopPolling();
  startTime = Date.now();
  pollTimer = setInterval(async () => {
    await checkStatus();
    if (status.value === "running" && (Date.now() - startTime) > 300_000) {
      status.value = "timeout";
      stopPolling();
    }
    if (status.value !== "running") {
      stopPolling();
      if (status.value === "completed") emit("profile-updated");
    }
  }, 2000);
}

function stopPolling() {
  if (pollTimer) { clearInterval(pollTimer); pollTimer = null; }
}

async function triggerDistill() {
  if (!props.account?.id || !articles.value.length) return;
  distillLoading.value = true;
  try {
    await api.triggerDistill(props.account.id);
    ElMessage.success("蒸馏任务已开始");
    status.value = "running";
    progress.value = { completed: 0, total: 7, current_dimension: "准备中" };
    startPolling();
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || "蒸馏失败");
  } finally {
    distillLoading.value = false;
  }
}

function retryDistill() {
  errorMessage.value = "";
  showDetail.value = false;
  status.value = "idle";
  triggerDistill();
}

function openArticleForm(article?: ReferenceArticle) {
  editingArticleId.value = article?.id ?? null;
  articleFormVisible.value = true;
}

async function saveArticle() {
  if (!props.account?.id) return;
  const data = articleFormRef.value?.getFormData();
  if (!data || !data.title || !data.content) {
    ElMessage.warning("标题和正文不能为空");
    return;
  }
  savingArticle.value = true;
  try {
    if (editingArticleId.value) {
      await api.updateReferenceArticle(props.account.id, editingArticleId.value, {
        ...data, account_id: props.account.id,
      } as any);
    } else {
      await api.createReferenceArticle(props.account.id, {
        ...data, account_id: props.account.id,
      } as any);
    }
    ElMessage.success(editingArticleId.value ? "已保存" : "已添加");
    articleFormVisible.value = false;
    articleFormRef.value?.reset();
    await loadArticles();
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || "操作失败");
  } finally {
    savingArticle.value = false;
  }
}

async function deleteArticle(article: ReferenceArticle) {
  if (!props.account?.id) return;
  try {
    await ElMessageBox.confirm("确定删除此参考文章？", "确认", { type: "warning" });
    await api.deleteReferenceArticle(props.account.id, article.id);
    ElMessage.success("已删除");
    await loadArticles();
  } catch { /* cancelled */ }
}

onUnmounted(() => stopPolling());
</script>

<style scoped>
.distill-layout { display: flex; min-height: 480px; }
.distill-left { flex: 1; border-right: 1px solid var(--ink-border); padding: 16px; max-width: 40%; overflow-y: auto; }
.distill-right { flex: 1.5; padding: 16px; display: flex; flex-direction: column; }
.distill-left-header, .distill-right-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
.distill-left-header h4, .distill-right-header h4 { margin: 0; font-size: 14px; }
.distill-article-list.readonly { opacity: 0.5; pointer-events: none; }
.distill-article-item {
  display: flex; justify-content: space-between; align-items: center;
  padding: 10px 12px; margin-bottom: 6px;
  background: var(--ink-surface); border-radius: 6px;
}
.distill-article-item>.distill-article-item-content{flex:1;}
.distill-article-item>.distill-article-actions{width: 120px;}
.distill-article-title { font-size: 13px; font-weight: 500; color: var(--text-on-dark); }
.distill-article-meta { font-size: 11px; color: var(--text-dim); }
.distill-center { flex: 1; display: flex; align-items: center; justify-content: center; }
.profile-content-area {
  width: 100%; max-height: 420px; overflow-y: auto;
  display: flex; flex-direction: column; gap: 10px;
}
.dim-content-card {
  background: var(--ink-surface); border-left: 2px solid var(--amber);
  border-radius: 0 var(--radius-md) var(--radius-md) 0;
  padding: 12px 14px;
}
.dim-content-header {
  font-size: 13px; font-weight: 600; color: var(--amber-light);
  margin-bottom: 6px;
}
.dim-content-text {
  font-size: 12px; line-height: 1.7; color: var(--text-dim);
  white-space: pre-wrap; margin: 0;
}
.distill-action-bar { text-align: center; padding-top: 16px; border-top: 1px solid var(--ink-border); }
.progress-bar { width: 100%; height: 8px; background: var(--ink-border); border-radius: 8px; overflow: hidden; margin: 16px 0; }
.progress-fill { height: 100%; background: #409eff; border-radius: 8px; transition: width 0.3s; }
.progress-text { font-size: 13px; margin-top: 8px; color: var(--text-dim); }
.progress-dim { font-size: 13px; color: var(--text-on-dark); font-weight: 500; }
.progress-eta { font-size: 11px; color: var(--text-muted); }
.dimension-status-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 4px; margin-top: 12px; text-align: left; font-size: 12px; }
.dim-status-item { padding: 4px 8px; border-radius: 4px; }
.dim-status-item.done { color: var(--green-muted); }
.dim-status-item.active { color: #409eff; font-weight: 600; }
.dim-status-item.pending { color: var(--text-dim); }
.profile-mini-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; width: 100%; }
.dim-mini-card {
  display: flex; justify-content: space-between; align-items: center;
  padding: 8px 10px; background: var(--ink-surface); border-radius: 6px; font-size: 12px;
}
.dim-mini-card.done .check { color: var(--green-muted); }
.status-tag { font-size: 11px; padding: 2px 8px; border-radius: 4px; }
.status-tag.ready { background: rgba(91,140,90,0.12); color: var(--green-muted); }
.status-tag.running { background: rgba(64,158,255,0.12); color: #409eff; }
.status-tag.failed { background: rgba(245,108,108,0.12); color: #f56c6c; }
.error-detail { background: var(--ink-surface); padding: 12px; border-radius: 6px; font-size: 12px; color: #cf1322; max-height: 200px; overflow-y: auto; text-align: left; white-space: pre-wrap; margin-top: 12px; }
.active-dot { color: #409eff; }
.empty-hint { text-align: center; color: var(--text-dim); font-size: 14px; padding: 32px 0; }
.tag-benchmark { font-size: 10px; padding: 2px 8px; border-radius: 10px; background: var(--amber-glow); color: var(--amber-light); font-weight: 600; }
</style>
