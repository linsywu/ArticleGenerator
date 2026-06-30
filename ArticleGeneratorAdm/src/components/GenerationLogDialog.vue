<template>
  <el-dialog
    v-model="visible"
    :title="`任务日志${taskTitle ? ' — ' + taskTitle : ''}`"
    width="900px"
    top="5vh"
    destroy-on-close
  >
    <div v-if="loading" class="log-loading">加载中...</div>
    <el-empty v-else-if="logs.length === 0" description="暂无日志记录" />

    <div v-else class="log-list">
      <div v-for="log in logs" :key="log.id" class="log-card">
        <div class="log-header">
          <span class="log-scenario">{{ scenarioLabel(log.scenario) }}</span>
          <el-tag :type="log.status === 'success' ? 'success' : 'danger'" size="small">
            {{ log.status === 'success' ? '成功' : '失败' }}
          </el-tag>
          <span class="log-model">{{ log.model || '-' }}</span>
          <span class="log-tokens">⏱ {{ log.latency_ms }}ms · {{ log.prompt_tokens + log.completion_tokens }} tokens</span>
          <span class="log-time">{{ formatTime(log.created_at) }}</span>
          <el-button size="small" text type="primary" @click="togglePrompt(log.id)">
            {{ expandedLogs.has(log.id) ? '收起提示词 ▲' : '查看提示词 ▼' }}
          </el-button>
        </div>

        <div v-if="log.error_message" class="log-error">{{ log.error_message }}</div>

        <!-- 展开的完整提示词 -->
        <div v-if="expandedLogs.has(log.id)" class="prompt-section">
          <div v-if="log.system_prompt" class="prompt-block">
            <div class="prompt-label">System Prompt</div>
            <pre class="prompt-content">{{ log.system_prompt }}</pre>
          </div>
          <div v-if="log.user_prompt" class="prompt-block">
            <div class="prompt-label">User Message</div>
            <pre class="prompt-content">{{ log.user_prompt }}</pre>
          </div>
          <div v-if="!log.system_prompt && !log.user_prompt" class="prompt-empty">
            此日志记录于旧版本，不包含提示词内容
          </div>
        </div>
      </div>
    </div>

    <template #footer>
      <el-button @click="visible = false">关闭</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, watch } from "vue";
import { api, type GenerationLog } from "@/api/client";
import { formatDateTime } from "@/utils/format";

const SCENARIO_LABELS: Record<string, string> = {
  "material-summary": "⓪ 素材摘要",
  distill: "① 风格蒸馏",
  direction: "② 方向生成",
  outline: "③ 大纲生成",
  title: "④ 标题生成",
  generate: "⑤ 文章生成",
  humanize: "⑥ 去AI味",
  quality_review: "⑦ 质量评审",
  compliance_review: "⑧ 合规评审",
  refine: "⑨ 微调重写",
};

function scenarioLabel(s: string) {
  return SCENARIO_LABELS[s] || s;
}

function formatTime(iso: string) {
  return formatDateTime(iso, "short");
}

const visible = ref(false);
const loading = ref(false);
const logs = ref<GenerationLog[]>([]);
const expandedLogs = ref(new Set<number>());
const taskTitle = ref("");

function togglePrompt(id: number) {
  if (expandedLogs.value.has(id)) {
    expandedLogs.value.delete(id);
  } else {
    expandedLogs.value.add(id);
  }
  // Trigger reactivity
  expandedLogs.value = new Set(expandedLogs.value);
}

async function open(genTaskId: number, title?: string) {
  visible.value = true;
  taskTitle.value = title || "";
  loading.value = true;
  expandedLogs.value = new Set();
  try {
    const res = await api.getGenerationLogsByTask(genTaskId);
    logs.value = (res.data as any).data || [];
  } catch {
    logs.value = [];
  } finally {
    loading.value = false;
  }
}

async function openByTaskId(taskId: string, title?: string) {
  visible.value = true;
  taskTitle.value = title || "";
  loading.value = true;
  expandedLogs.value = new Set();
  try {
    const res = await api.getGenerationLogs({ task_id: taskId });
    logs.value = (res.data as any).data || [];
  } catch {
    logs.value = [];
  } finally {
    loading.value = false;
  }
}

defineExpose({ open, openByTaskId });
</script>

<style scoped>
.log-loading {
  text-align: center;
  padding: 40px;
  color: var(--text-muted);
}
.log-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  max-height: 65vh;
  overflow-y: auto;
}
.log-card {
  background: var(--ink-surface);
  border: 1px solid var(--ink-border);
  border-radius: var(--radius-md);
  padding: 12px 16px;
}
.log-header {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}
.log-scenario {
  font-weight: 600;
  font-size: 14px;
  color: var(--text-on-dark);
  min-width: 100px;
}
.log-model {
  font-size: 12px;
  color: var(--text-dim);
}
.log-tokens {
  font-size: 12px;
  color: var(--text-muted);
}
.log-time {
  font-size: 12px;
  color: var(--text-muted);
  margin-left: auto;
}
.log-error {
  margin-top: 8px;
  padding: 8px 12px;
  background: rgba(220, 80, 80, 0.1);
  border-radius: var(--radius-sm);
  color: #e06060;
  font-size: 13px;
}
.prompt-section {
  margin-top: 12px;
}
.prompt-block {
  margin-bottom: 12px;
}
.prompt-label {
  font-size: 12px;
  font-weight: 600;
  color: var(--amber-light);
  margin-bottom: 4px;
}
.prompt-content {
  background: #0c0e13;
  color: #c8ccd4;
  padding: 12px;
  border-radius: var(--radius-sm);
  font-size: 13px;
  line-height: 1.7;
  white-space: pre-wrap;
  word-break: break-word;
  max-height: 300px;
  overflow-y: auto;
  border: 1px solid var(--ink-border);
}
.prompt-empty {
  color: var(--text-dim);
  font-size: 13px;
  font-style: italic;
}
</style>
