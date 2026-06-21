<template>
  <div class="account-card">
    <div class="card-top">
      <div class="card-avatar">{{ account.account_name.charAt(0) }}</div>
      <div class="card-meta">
        <span class="card-name">{{ account.account_name }}</span>
        <span class="card-platform">{{ account.platform }}</span>
      </div>
      <span class="card-badge" :class="badgeClass">
        {{ badgeText }}
      </span>
    </div>
    <div class="card-bottom">
      <span class="card-date">{{ dateText }}</span>
      <el-dropdown trigger="click" @command="(cmd: string) => { if (cmd === 'delete') $emit('delete'); }">
        <el-button size="small" text type="info" @click.stop>⋯</el-button>
        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item command="delete">删除账号</el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
    </div>
    <div class="card-actions">
      <el-button size="small" @click.stop="$emit('edit-basic')">基本信息</el-button>
      <el-button size="small" type="primary" @click.stop="$emit('distill')">风格蒸馏</el-button>
      <el-button size="small" @click.stop="$emit('word-count')">字数配置</el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue";
import type { Account } from "@/api/types";
import { formatDateTime } from "@/utils/format";

const props = defineProps<{ account: Account }>();

defineEmits<{
  (e: "edit-basic"): void;
  (e: "distill"): void;
  (e: "word-count"): void;
  (e: "delete"): void;
}>();

const badgeInfo = computed(() => {
  const status = props.account.style_profile_status || "none";
  if (status === "ready") {
    const v = props.account.style_profile_version || 1;
    return { text: `画像就绪 v${v}`, class: "badge-ready" };
  }
  const map: Record<string, { text: string; class: string }> = {
    running: { text: "蒸馏中...", class: "badge-running" },
    failed: { text: "蒸馏失败", class: "badge-failed" },
  };
  return map[status] || { text: "待蒸馏", class: "badge-idle" };
});

const badgeText = computed(() => badgeInfo.value.text);
const badgeClass = computed(() => badgeInfo.value.class);

const dateText = computed(() => {
  if (props.account.style_profile_updated_at) {
    return `更新于 ${formatDateTime(props.account.style_profile_updated_at, "date")}`;
  }
  if (props.account.created_at) {
    return `创建于 ${formatDateTime(props.account.created_at, "date")}`;
  }
  return "尚未蒸馏";
});
</script>

<style scoped>
.account-card {
  background: var(--ink-mid);
  border: 1px solid var(--ink-border);
  border-radius: var(--radius-lg);
  padding: 20px;
  transition: all var(--duration-fast) var(--ease-out);
}
.account-card:hover { border-color: var(--text-dim); background: var(--ink-surface); }
.card-top { display: flex; align-items: center; gap: 12px; margin-bottom: 14px; }
.card-avatar {
  width: 42px; height: 42px; border-radius: var(--radius-md);
  background: var(--amber-glow); color: var(--amber-light);
  display: flex; align-items: center; justify-content: center;
  font-family: var(--font-serif); font-size: 20px; font-weight: 700; flex-shrink: 0;
}
.card-meta { flex: 1; display: flex; flex-direction: column; gap: 2px; }
.card-name { font-size: 15px; font-weight: 600; color: var(--text-on-dark); }
.card-platform { font-size: 12px; color: var(--text-dim); }
.card-badge { font-size: 11px; padding: 3px 10px; border-radius: 20px; font-weight: 500; }
.badge-ready { background: rgba(91,140,90,0.12); color: var(--green-muted); }
.badge-idle { background: rgba(139,135,128,0.1); color: var(--text-dim); }
.badge-running { background: rgba(64,158,255,0.12); color: #409eff; }
.badge-failed { background: rgba(245,108,108,0.12); color: #f56c6c; }
.card-bottom { display: flex; justify-content: space-between; align-items: center; }
.card-date { font-size: 12px; color: var(--text-dim); }
.card-actions { display: flex; gap: 6px; margin-top: 14px; padding-top: 14px; border-top: 1px solid var(--ink-border); }
</style>
