<template>
  <div class="generate-view">
    <!-- 顶部操作栏 -->
    <header class="cmd-header">
      <div class="cmd-title">文章生成</div>
      <div class="cmd-actions">
        <div class="search-box">
          <svg class="search-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
          <input v-model="keyword" placeholder="搜索热点选题..." @keyup.enter="load" class="search-input" />
        </div>
        <el-select v-model="sourceFilter" placeholder="全部来源" size="large" clearable class="source-select">
          <el-option label="全部来源" value="" />
          <el-option v-for="s in sourceOptions" :key="s" :label="s" :value="s" />
        </el-select>
        <button class="btn-secondary" @click="load">刷新</button>
        <button class="btn-accent" :disabled="crawling" @click="doCrawl">
          {{ crawling ? '拉取中...' : '拉取最新热点' }}
        </button>
      </div>
    </header>

    <!-- 状态横幅 -->
    <transition name="banner-fade">
      <div v-if="generatingStatus === 'polling'" class="status-banner polling">
        <div class="status-dot"></div>
        <span>正在生成 {{ lastTaskIds.length }} 篇文章...</span>
      </div>
      <div v-else-if="generatingStatus === 'done'" class="status-banner success">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="status-icon"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>
        <span>全部生成完成</span>
        <router-link to="/review" class="status-link">前往评审 →</router-link>
      </div>
    </transition>

    <!-- 自定义主题 -->
    <section class="custom-topic-section">
      <div class="custom-topic-row">
        <div class="custom-topic-input-wrap">
          <svg class="topic-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
          <input
            v-model="customTopic"
            placeholder="手动输入写作主题，回车直接生成..."
            class="custom-topic-input"
            @keyup.enter="doCustomGenerate"
          />
        </div>
        <el-select v-model="generateAccountId" placeholder="选择账号" size="large" class="topic-account-select">
          <el-option v-for="a in accounts" :key="a.id" :label="`${a.account_name} · ${a.platform}`" :value="a.id">
            <div class="account-option">
              <span class="option-name">{{ a.account_name }}</span>
              <span class="option-platform">{{ a.platform }}</span>
              <el-tag v-if="a.style_profile" size="small" type="success" class="option-tag">有画像</el-tag>
            </div>
          </el-option>
        </el-select>
        <button
          class="topic-generate-btn"
          :disabled="!customTopic.trim() || !generateAccountId || generating"
          @click="doCustomGenerate"
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="btn-icon"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>
          生成
        </button>
      </div>
    </section>

    <!-- 热点选题卡片网格 -->
    <section class="hotspot-grid" v-loading="loading">
      <div v-if="!loading && list.length === 0" class="empty-state">
        <div class="empty-icon">📭</div>
        <p class="empty-title">暂无热点</p>
        <p class="empty-desc">点击「拉取最新热点」获取今日选题</p>
      </div>
      <article
        v-for="item in list"
        :key="item.id"
        class="hotspot-card"
        :class="{ selected: selectedIds.includes(item.id), 'already-generated': item.status === 'generated' }"
        @click="item.status !== 'generated' && toggleSelect(item)"
      >
        <div class="card-check">
          <div class="check-circle" :class="{ checked: selectedIds.includes(item.id) }">
            <svg v-if="selectedIds.includes(item.id)" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"><polyline points="20 6 9 17 4 12"/></svg>
          </div>
        </div>
        <div class="card-body">
          <h3 class="card-title">
            <a v-if="item.url" :href="item.url" target="_blank" rel="noopener" @click.stop class="card-link">{{ item.title }}</a>
            <span v-else>{{ item.title }}</span>
          </h3>
          <div class="card-meta">
            <span class="meta-source">{{ item.source }}</span>
            <span class="meta-heat">🔥 {{ formatHeat(item.heat) }}</span>
            <span v-if="item.status === 'generated'" class="meta-generated">已生成</span>
          </div>
        </div>
      </article>
    </section>

    <el-pagination
      v-if="total > 0"
      v-model:current-page="page"
      v-model:page-size="pageSize"
      :total="total"
      :page-sizes="[12, 24, 48]"
      layout="total, prev, pager, next"
      @current-change="load"
      @size-change="load"
      class="pagination-bar"
    />

    <!-- 底部生成操作栏 -->
    <footer class="generate-bar" :class="{ active: selectedIds.length > 0 }">
      <div class="bar-inner">
        <div class="bar-selection">
          <span class="selection-count">{{ selectedIds.length }}</span>
          <span class="selection-label">个热点已选</span>
        </div>
        <div class="bar-account">
          <span class="account-label">生成账号</span>
          <el-select v-model="generateAccountId" placeholder="选择账号风格" size="large" class="account-select">
            <el-option v-for="a in accounts" :key="a.id" :label="`${a.account_name} · ${a.platform}`" :value="a.id">
              <div class="account-option">
                <span class="option-name">{{ a.account_name }}</span>
                <span class="option-platform">{{ a.platform }}</span>
                <el-tag v-if="a.style_profile" size="small" type="success" class="option-tag">有画像</el-tag>
              </div>
            </el-option>
          </el-select>
        </div>
        <button
          class="generate-btn"
          :disabled="!selectedIds.length || !generateAccountId || generating"
          @click="doGenerate"
        >
          <svg v-if="!generating" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="btn-icon"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>
          <span v-if="generating">生成中...</span>
          <span v-else>一键生成文章</span>
        </button>
      </div>
      <!-- 任务状态列表 -->
      <div v-if="generatingStatus === 'polling' && taskStates.length" class="task-progress">
        <div v-for="t in taskStates" :key="t.id" class="task-item" :class="t.status">
          <span class="task-icon">
            <template v-if="t.status === 'success'">✅</template>
            <template v-else-if="t.status === 'failed'">❌</template>
            <template v-else>🔄</template>
          </span>
          <span class="task-label">热点 #{{ t.hotspotId }}</span>
          <span class="task-status-text">{{ t.status === 'success' ? '已完成' : t.status === 'failed' ? '失败' : '生成中' }}</span>
        </div>
      </div>
    </footer>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from "vue";
import { ElMessage } from "element-plus";
import { api, type Hotspot, type Account } from "@/api/client";

const list = ref<Hotspot[]>([]);
const loading = ref(false);
const keyword = ref("");
const sourceFilter = ref("");
const sourceOptions = ref<string[]>([]);
const page = ref(1);
const pageSize = ref(12);
const total = ref(0);
const selectedIds = ref<number[]>([]);
const accounts = ref<Account[]>([]);
const generateAccountId = ref<number | null>(null);
const generating = ref(false);
const crawling = ref(false);
const customTopic = ref("");

const lastTaskIds = ref<{ task_id: string; hotspot_id: number }[]>([]);
const generatingStatus = ref<"idle" | "polling" | "done">("idle");
const taskStates = ref<{ id: string; hotspotId: number; status: string }[]>([]);

function formatHeat(n: number): string {
  if (n >= 10000) return (n / 10000).toFixed(0) + "万";
  if (n >= 1000) return (n / 1000).toFixed(1) + "k";
  return String(n);
}

function toggleSelect(item: Hotspot) {
  const idx = selectedIds.value.indexOf(item.id);
  if (idx >= 0) {
    selectedIds.value.splice(idx, 1);
  } else {
    selectedIds.value.push(item.id);
  }
}

async function load() {
  loading.value = true;
  try {
    const res = await api.getHotspots({
      keyword: keyword.value || undefined,
      source: sourceFilter.value || undefined,
      status: "unselected",
      page: page.value,
      page_size: pageSize.value,
    });
    const payload = res.data as { data: Hotspot[]; total: number };
    list.value = payload.data;
    total.value = payload.total;
  } catch {
    ElMessage.error("加载失败");
  } finally {
    loading.value = false;
  }
}

async function loadSources() {
  try {
    const res = await api.getHotspotSourceOptions();
    sourceOptions.value = res.data.sources || [];
  } catch {
    sourceOptions.value = [];
  }
}

async function doCrawl() {
  crawling.value = true;
  try {
    const res = await api.crawlHotspots();
    const data = res.data as { created?: number; total?: number; error?: string };
    if (data.error) {
      ElMessage.error(`拉取失败：${data.error}`);
    } else {
      ElMessage.success(`拉取完成，新增 ${data.created ?? 0} 条热点`);
      load();
      loadSources();
    }
  } catch {
    ElMessage.error("拉取失败");
  } finally {
    crawling.value = false;
  }
}

async function doGenerate() {
  if (!generateAccountId.value || !selectedIds.value.length) return;
  generating.value = true;
  try {
    const res = await api.triggerGenerate(generateAccountId.value, selectedIds.value);
    const tasks = (res.data as { tasks?: { task_id: string; hotspot_id: number }[] }).tasks || [];
    lastTaskIds.value = tasks;
    taskStates.value = tasks.map((t: any) => ({ id: t.task_id, hotspotId: t.hotspot_id || 0, status: "pending" }));
    generatingStatus.value = "polling";
    selectedIds.value = [];
    pollTasks();
  } catch {
    ElMessage.error("提交失败");
    generating.value = false;
  }
}

async function doCustomGenerate() {
  const topic = customTopic.value.trim();
  if (!topic || !generateAccountId.value) return;
  generating.value = true;
  try {
    const res = await api.triggerGenerate(generateAccountId.value, undefined, topic);
    const tasks = (res.data as { tasks?: { task_id: string; topic?: string }[] }).tasks || [];
    lastTaskIds.value = tasks.map((t: any) => ({ task_id: t.task_id, hotspot_id: 0 }));
    taskStates.value = tasks.map((t: any) => ({ id: t.task_id, hotspotId: 0, status: "pending" }));
    generatingStatus.value = "polling";
    customTopic.value = "";
    pollTasks();
  } catch {
    ElMessage.error("提交失败");
    generating.value = false;
  }
}

let pollTimer: ReturnType<typeof setInterval> | null = null;

function pollTasks() {
  if (pollTimer) clearInterval(pollTimer);
  pollTimer = setInterval(async () => {
    try {
      const res = await api.getTasksBatch(lastTaskIds.value.map((t) => t.task_id));
      const data = res.data as { tasks?: { task_id: string; status: string }[] };
      const results = data.tasks || [];
      results.forEach((r) => {
        const ts = taskStates.value.find((t) => t.id === r.task_id);
        if (ts) ts.status = r.status;
      });
      const done = results.every((t) => t.status === "success" || t.status === "failed");
      if (done) {
        if (pollTimer) clearInterval(pollTimer);
        pollTimer = null;
        generatingStatus.value = "done";
        generating.value = false;
        load();
      }
    } catch {
      // ignore poll errors
    }
  }, 2000);
}

onMounted(() => {
  load();
  loadSources();
  api.getAccounts().then((r) => {
    accounts.value = r.data;
    generateAccountId.value = r.data[0]?.id ?? null;
  });
});
</script>

<style scoped>
/* ── Typography ── */
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+SC:wght@400;500;600;700&family=DM+Mono:wght@400;500&display=swap');

.generate-view {
  max-width: 1280px;
  margin: 0 auto;
  font-family: 'Noto Sans SC', -apple-system, sans-serif;
  color: #1a1a2e;
}

/* ── Header ── */
.cmd-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 24px;
  flex-wrap: wrap;
  gap: 16px;
}
.cmd-title {
  font-size: 26px;
  font-weight: 700;
  letter-spacing: -0.02em;
  color: #0f0f1a;
}
.cmd-actions {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

/* ── Search ── */
.search-box {
  position: relative;
  display: flex;
  align-items: center;
}
.search-icon {
  position: absolute;
  left: 14px;
  width: 18px;
  height: 18px;
  color: #94a3b8;
  pointer-events: none;
}
.search-input {
  width: 240px;
  height: 42px;
  padding: 0 16px 0 42px;
  border: 1.5px solid #e2e8f0;
  border-radius: 10px;
  font-size: 14px;
  font-family: inherit;
  background: #f8fafc;
  color: #334155;
  outline: none;
  transition: border-color 0.2s, box-shadow 0.2s;
}
.search-input:focus {
  border-color: #6366f1;
  box-shadow: 0 0 0 3px rgba(99,102,241,0.1);
  background: #fff;
}
.search-input::placeholder { color: #94a3b8; }
.source-select { width: 140px; }

/* ── Buttons ── */
.btn-secondary {
  height: 42px;
  padding: 0 20px;
  border: 1.5px solid #e2e8f0;
  border-radius: 10px;
  background: #fff;
  font-size: 14px;
  font-family: inherit;
  font-weight: 500;
  color: #475569;
  cursor: pointer;
  transition: all 0.2s;
}
.btn-secondary:hover { border-color: #cbd5e1; background: #f8fafc; }
.btn-accent {
  height: 42px;
  padding: 0 20px;
  border: none;
  border-radius: 10px;
  background: linear-gradient(135deg, #6366f1, #8b5cf6);
  font-size: 14px;
  font-family: inherit;
  font-weight: 600;
  color: #fff;
  cursor: pointer;
  transition: all 0.2s;
}
.btn-accent:hover { transform: translateY(-1px); box-shadow: 0 4px 12px rgba(99,102,241,0.35); }
.btn-accent:disabled { opacity: 0.5; cursor: not-allowed; transform: none; }

/* ── Status Banner ── */
.status-banner {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 20px;
  border-radius: 12px;
  margin-bottom: 20px;
  font-size: 14px;
  font-weight: 500;
}
.status-banner.polling { background: #eef2ff; color: #4338ca; }
.status-banner.success { background: #ecfdf5; color: #065f46; }
.status-dot {
  width: 8px; height: 8px; border-radius: 50%;
  background: #6366f1; animation: pulse 1.5s infinite;
}
@keyframes pulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.5; transform: scale(0.8); }
}
.status-icon { width: 18px; height: 18px; }
.status-link { color: #059669; font-weight: 600; margin-left: auto; text-decoration: none; }
.status-link:hover { text-decoration: underline; }
.banner-fade-enter-active, .banner-fade-leave-active { transition: all 0.3s ease; }
.banner-fade-enter-from, .banner-fade-leave-to { opacity: 0; transform: translateY(-8px); }

/* ── Custom Topic ── */
.custom-topic-section { margin-bottom: 24px; }
.custom-topic-row { display: flex; align-items: center; gap: 12px; }
.custom-topic-input-wrap {
  flex: 1; position: relative; display: flex; align-items: center;
}
.topic-icon {
  position: absolute; left: 16px; width: 20px; height: 20px;
  color: #6366f1; pointer-events: none; z-index: 1;
}
.custom-topic-input {
  width: 100%; height: 48px; padding: 0 16px 0 50px;
  border: 1.5px solid #e2e8f0; border-radius: 12px;
  font-size: 15px; font-family: inherit; background: #fff; color: #1e293b;
  outline: none; transition: border-color 0.2s, box-shadow 0.2s;
}
.custom-topic-input:focus {
  border-color: #6366f1;
  box-shadow: 0 0 0 3px rgba(99,102,241,0.1);
}
.custom-topic-input::placeholder { color: #94a3b8; }
.topic-account-select { width: 200px; flex-shrink: 0; }
.topic-generate-btn {
  display: flex; align-items: center; gap: 6px;
  height: 48px; padding: 0 28px; border: none; border-radius: 12px;
  background: linear-gradient(135deg, #6366f1, #8b5cf6);
  font-size: 15px; font-weight: 600; font-family: inherit; color: #fff;
  cursor: pointer; transition: all 0.2s; white-space: nowrap; flex-shrink: 0;
}
.topic-generate-btn:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 4px 14px rgba(99,102,241,0.35);
}
.topic-generate-btn:disabled { opacity: 0.4; cursor: not-allowed; transform: none; }

/* ── Hotspot Grid ── */
.hotspot-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(360px, 1fr));
  gap: 12px;
  margin-bottom: 24px;
}

/* ── Card ── */
.hotspot-card {
  display: flex;
  gap: 14px;
  padding: 16px 18px;
  border: 1.5px solid #e8ecf1;
  border-radius: 14px;
  background: #fff;
  cursor: pointer;
  transition: all 0.2s ease;
  position: relative;
}
.hotspot-card:hover {
  border-color: #c7d2fe;
  box-shadow: 0 2px 12px rgba(99,102,241,0.08);
  transform: translateY(-1px);
}
.hotspot-card.selected {
  border-color: #6366f1;
  background: linear-gradient(135deg, #fafafe 0%, #eef2ff 100%);
  box-shadow: 0 2px 16px rgba(99,102,241,0.12);
}
.hotspot-card.already-generated {
  opacity: 0.5;
  cursor: not-allowed;
  background: #f1f5f9;
}
.hotspot-card.already-generated:hover { transform: none; box-shadow: none; border-color: #e8ecf1; }

/* ── Check Circle ── */
.card-check { display: flex; align-items: flex-start; padding-top: 2px; }
.check-circle {
  width: 22px; height: 22px; border-radius: 50%;
  border: 2px solid #d1d5db;
  display: flex; align-items: center; justify-content: center;
  transition: all 0.2s ease;
  flex-shrink: 0;
}
.check-circle svg { width: 14px; height: 14px; color: #fff; }
.check-circle.checked { border-color: #6366f1; background: #6366f1; }
.hotspot-card:hover .check-circle:not(.checked) { border-color: #a5b4fc; }

/* ── Card Body ── */
.card-body { flex: 1; min-width: 0; }
.card-title {
  font-size: 15px; font-weight: 600; line-height: 1.5; margin: 0 0 8px 0;
  color: #1e293b; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical;
  overflow: hidden;
}
.card-link { color: inherit; text-decoration: none; }
.card-link:hover { color: #6366f1; }
.card-meta { display: flex; align-items: center; gap: 12px; font-size: 13px; color: #94a3b8; }
.meta-source {
  padding: 2px 8px; border-radius: 6px; background: #f1f5f9;
  font-weight: 500; color: #64748b;
}
.meta-heat { font-weight: 600; color: #f59e0b; font-family: 'DM Mono', monospace; }
.meta-generated { font-size: 12px; color: #10b981; font-weight: 600; margin-left: auto; }

/* ── Empty State ── */
.empty-state { grid-column: 1 / -1; text-align: center; padding: 80px 0; }
.empty-icon { font-size: 48px; margin-bottom: 16px; }
.empty-title { font-size: 18px; font-weight: 600; color: #64748b; margin-bottom: 8px; }
.empty-desc { font-size: 14px; color: #94a3b8; }

/* ── Pagination ── */
.pagination-bar { margin-bottom: 120px; }

/* ── Bottom Generate Bar ── */
.generate-bar {
  position: fixed; bottom: 0; left: 200px; right: 0;
  background: #fff; border-top: 1px solid #e8ecf1;
  padding: 16px 24px; z-index: 100;
  transition: all 0.3s ease;
}
.generate-bar.active { box-shadow: 0 -4px 24px rgba(0,0,0,0.06); }
.bar-inner {
  max-width: 1280px; margin: 0 auto;
  display: flex; align-items: center; gap: 24px;
}
.bar-selection {
  display: flex; align-items: baseline; gap: 6px;
  padding: 8px 16px; border-radius: 10px; background: #eef2ff;
  flex-shrink: 0;
}
.selection-count { font-size: 24px; font-weight: 700; color: #4338ca; font-family: 'DM Mono', monospace; }
.selection-label { font-size: 13px; color: #6366f1; font-weight: 500; }
.bar-account { display: flex; align-items: center; gap: 10px; }
.account-label { font-size: 14px; font-weight: 500; color: #64748b; white-space: nowrap; }
.account-select { width: 240px; }

/* ── Generate Button ── */
.generate-btn {
  display: flex; align-items: center; gap: 8px;
  margin-left: auto; padding: 0 32px; height: 48px;
  border: none; border-radius: 12px;
  background: linear-gradient(135deg, #0f172a, #1e293b);
  font-size: 15px; font-weight: 700; font-family: inherit; color: #fff;
  cursor: pointer; transition: all 0.2s ease;
  white-space: nowrap;
}
.generate-btn:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 8px 20px rgba(15,23,42,0.3);
}
.generate-btn:disabled {
  opacity: 0.35; cursor: not-allowed;
}
.btn-icon { width: 20px; height: 20px; }

/* ── Account Option ── */
.account-option { display: flex; align-items: center; gap: 8px; }
.option-name { font-weight: 500; }
.option-platform { font-size: 12px; color: #94a3b8; }
.option-tag { margin-left: auto; }

/* ── Task Progress ── */
.task-progress {
  max-width: 1280px; margin: 12px auto 0;
  display: flex; gap: 16px; flex-wrap: wrap;
}
.task-item {
  display: flex; align-items: center; gap: 6px;
  padding: 6px 14px; border-radius: 8px;
  font-size: 13px; font-weight: 500;
}
.task-item.pending { background: #fef3c7; color: #92400e; }
.task-item.success { background: #d1fae5; color: #065f46; }
.task-item.failed   { background: #fee2e2; color: #991b1b; }
.task-icon { font-size: 14px; }
.task-label { font-weight: 600; }
.task-status-text { opacity: 0.7; }
</style>
