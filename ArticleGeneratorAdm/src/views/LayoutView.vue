<template>
  <div class="app-shell">
    <!-- 侧边栏 -->
    <aside class="sidebar">
      <div class="sidebar-brand">
        <span class="brand-icon">墨</span>
        <span class="brand-text">ArticleGenerator</span>
      </div>

      <nav class="sidebar-nav">
        <div class="nav-section">
          <span class="nav-section-title">创作</span>
          <router-link to="/create" class="nav-item" :class="{ active: $route.path === '/create' }">
            <span class="nav-icon">✎</span>
            <span class="nav-label">文章创作</span>
          </router-link>
          <router-link to="/review" class="nav-item" :class="{ active: $route.path === '/review' }">
            <span class="nav-icon">◉</span>
            <span class="nav-label">评审队列</span>
          </router-link>
          <router-link to="/publish" class="nav-item" :class="{ active: $route.path === '/publish' }">
            <span class="nav-icon">↗</span>
            <span class="nav-label">文章发布</span>
          </router-link>
        </div>

        <div class="nav-section">
          <span class="nav-section-title">资源</span>
          <router-link to="/accounts" class="nav-item" :class="{ active: $route.path === '/accounts' }">
            <span class="nav-icon">☺</span>
            <span class="nav-label">账号风格</span>
          </router-link>
          <router-link to="/inspiration" class="nav-item" :class="{ active: $route.path === '/inspiration' }">
            <span class="nav-icon">☀</span>
            <span class="nav-label">灵感墙</span>
          </router-link>
          <router-link to="/tasks" class="nav-item" :class="{ active: $route.path === '/tasks' }">
            <span class="nav-icon">☰</span>
            <span class="nav-label">任务记录</span>
          </router-link>
        </div>

        <div class="nav-section">
          <span class="nav-section-title">配置</span>
          <router-link to="/hotspot-sources" class="nav-item" :class="{ active: $route.path === '/hotspot-sources' }">
            <span class="nav-icon">⚑</span>
            <span class="nav-label">热点源管理</span>
          </router-link>
          <router-link to="/providers" class="nav-item" :class="{ active: $route.path === '/providers' }">
            <span class="nav-icon">⚙</span>
            <span class="nav-label">API 供应商</span>
          </router-link>
          <router-link to="/scenario-configs" class="nav-item" :class="{ active: $route.path === '/scenario-configs' }">
            <span class="nav-icon">⚒</span>
            <span class="nav-label">场景配置</span>
          </router-link>
        </div>
      </nav>

      <!-- 任务中心入口 -->
      <div
        class="task-center-entry"
        @mouseenter="handleMouseEnter"
        @mouseleave="handleMouseLeave"
        @click="goToTaskCenter"
      >
        <span class="task-center-bell">🔔</span>
        <span v-if="totalActive > 0" class="task-center-badge">{{ totalActive }}</span>
        <span class="task-center-label">任务中心</span>

        <transition name="dropdown-fade">
          <div v-if="showDropdown" class="task-center-dropdown" @click.stop>
            <div class="dropdown-header">
              <span class="dropdown-title">进行中的任务</span>
              <span class="dropdown-view-all" @click="goToTaskCenter">查看全部</span>
            </div>
            <div v-if="dropdownTasks.length === 0" class="dropdown-empty">暂无进行中的任务</div>
            <div v-for="t in dropdownTasks" :key="t.task_id" class="dropdown-item" @click="goToTaskCenter">
              <span class="dropdown-icon">{{ t.task_type === 'generate' ? '✏️' : '🔧' }}</span>
              <div class="dropdown-info">
                <span class="dropdown-target">{{ t.target }}</span>
                <span class="dropdown-status" :class="t.status">{{ t.status === 'running' ? '运行中' : '排队中' }}</span>
              </div>
            </div>
          </div>
        </transition>
      </div>

      <div class="sidebar-footer">
        <span class="footer-version">v2 · 墨斋</span>
      </div>
    </aside>

    <!-- 主内容区 -->
    <main class="main-content">
      <router-view v-slot="{ Component }">
        <transition name="page-fade" mode="out-in">
          <component :is="Component" />
        </transition>
      </router-view>
    </main>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from "vue";
import { useRouter } from "vue-router";
import { storeToRefs } from "pinia";
import { useTasksStore } from "@/store/tasks";

const router = useRouter();
const tasksStore = useTasksStore();
const {
  activeTasks,
  runningCount,
  pendingCount,
  totalActive,
} = storeToRefs(tasksStore);
const {
  fetch: fetchActiveTasks,
  startPolling,
  stopPolling,
} = tasksStore;
const showDropdown = ref(false);
let hoverTimer: ReturnType<typeof setTimeout> | null = null;

const dropdownTasks = computed(() => activeTasks.value.slice(0, 3));

function handleMouseEnter() {
  if (hoverTimer) clearTimeout(hoverTimer);
  showDropdown.value = true;
  fetchActiveTasks();
}

function handleMouseLeave() {
  hoverTimer = setTimeout(() => {
    showDropdown.value = false;
  }, 300);
}

function goToTaskCenter() {
  showDropdown.value = false;
  router.push("/tasks-center");
}

onMounted(() => {
  startPolling(5000);
});

onUnmounted(() => {
  stopPolling();
  if (hoverTimer) clearTimeout(hoverTimer);
});
</script>

<style>
/* ═══════════════════════════════════════════
   应用外壳 — 墨斋 Ink Studio
   ═══════════════════════════════════════════ */

.app-shell {
  display: flex;
  height: 100vh;
  overflow: hidden;
}

/* ── 侧边栏 ── */
.sidebar {
  width: 220px;
  flex-shrink: 0;
  background: #0c0e13;
  border-right: 1px solid #1a1d26;
  display: flex;
  flex-direction: column;
  overflow-y: auto;
  z-index: 10;
}

.sidebar-brand {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 22px 20px 18px;
  border-bottom: 1px solid #1a1d26;
}

.brand-icon {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--amber);
  color: #0c0e13;
  border-radius: 6px;
  font-family: var(--font-serif);
  font-size: 18px;
  font-weight: 900;
  flex-shrink: 0;
}

.brand-text {
  font-family: var(--font-serif);
  font-size: 14px;
  font-weight: 700;
  color: var(--text-on-dark);
  letter-spacing: 0.5px;
  white-space: nowrap;
}

/* ── 导航 ── */
.sidebar-nav {
  flex: 1;
  padding: 12px 0;
  overflow-y: auto;
}

.nav-section {
  padding: 6px 0 10px;
}

.nav-section-title {
  display: block;
  padding: 6px 20px 4px;
  font-size: 10px;
  font-weight: 600;
  letter-spacing: 1.5px;
  text-transform: uppercase;
  color: #3d3f48;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 9px 20px;
  margin: 1px 8px;
  border-radius: var(--radius-md);
  color: var(--text-muted);
  text-decoration: none;
  font-size: 13px;
  font-weight: 450;
  transition: all var(--duration-fast) var(--ease-out);
  position: relative;
}

.nav-item:hover {
  background: rgba(255,255,255,0.03);
  color: var(--text-on-dark);
}

.nav-item.active {
  background: rgba(200,132,60,0.08);
  color: var(--amber-light);
  font-weight: 550;
}

.nav-item.active::before {
  content: '';
  position: absolute;
  left: 0;
  top: 6px;
  bottom: 6px;
  width: 2px;
  background: var(--amber);
  border-radius: 0 2px 2px 0;
}

.nav-icon {
  width: 18px;
  text-align: center;
  font-size: 13px;
  flex-shrink: 0;
  opacity: 0.7;
}

.nav-item.active .nav-icon {
  opacity: 1;
}

.nav-label {
  white-space: nowrap;
}

/* ── 任务中心入口 ── */
.task-center-entry {
  position: relative;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 20px;
  margin: 2px 8px 4px;
  border-radius: var(--radius-md);
  color: var(--text-muted);
  cursor: pointer;
  font-size: 13px;
  font-weight: 450;
  transition: all var(--duration-fast) var(--ease-out);
  user-select: none;
}
.task-center-entry:hover {
  background: rgba(255,255,255,0.03);
  color: var(--text-on-dark);
}
.task-center-bell {
  font-size: 14px;
  width: 18px;
  text-align: center;
  flex-shrink: 0;
  opacity: 0.7;
}
.task-center-entry:hover .task-center-bell {
  opacity: 1;
}
.task-center-badge {
  position: absolute;
  top: 4px;
  left: 30px;
  min-width: 16px;
  height: 16px;
  padding: 0 5px;
  background: var(--amber);
  color: #0c0e13;
  font-size: 10px;
  font-weight: 700;
  line-height: 16px;
  text-align: center;
  border-radius: 8px;
}
.task-center-label {
  white-space: nowrap;
}

/* 悬停下拉卡片 */
.task-center-dropdown {
  position: absolute;
  left: 220px;
  top: -10px;
  width: 320px;
  background: var(--ink-mid);
  border: 1px solid var(--ink-border);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-elevated);
  z-index: 1000;
  overflow: hidden;
}
.dropdown-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  border-bottom: 1px solid var(--ink-border);
}
.dropdown-title {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-muted);
}
.dropdown-view-all {
  font-size: 11px;
  color: var(--amber-light);
  cursor: pointer;
}
.dropdown-view-all:hover {
  text-decoration: underline;
}
.dropdown-empty {
  padding: 20px 16px;
  text-align: center;
  font-size: 12px;
  color: var(--text-dim);
}
.dropdown-item {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 10px 16px;
  cursor: pointer;
  transition: background var(--duration-fast) var(--ease-out);
}
.dropdown-item:hover {
  background: rgba(255,255,255,0.03);
}
.dropdown-item + .dropdown-item {
  border-top: 1px solid rgba(46, 49, 58, 0.5);
}
.dropdown-icon {
  font-size: 14px;
  flex-shrink: 0;
  margin-top: 1px;
}
.dropdown-info {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 3px;
}
.dropdown-target {
  font-size: 13px;
  color: var(--text-on-dark);
  font-weight: 500;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.dropdown-status {
  font-size: 10px;
  font-weight: 600;
  padding: 1px 6px;
  border-radius: 10px;
  align-self: flex-start;
}
.dropdown-status.running {
  background: rgba(200,132,60,0.1);
  color: var(--amber-light);
}
.dropdown-status.pending {
  background: rgba(90,125,154,0.1);
  color: var(--blue-muted);
}

.dropdown-fade-enter-active,
.dropdown-fade-leave-active {
  transition: opacity 0.15s ease, transform 0.15s ease;
}
.dropdown-fade-enter-from,
.dropdown-fade-leave-to {
  opacity: 0;
  transform: translateX(-6px);
}

/* ── 侧边栏底部 ── */
.sidebar-footer {
  padding: 14px 20px;
  border-top: 1px solid #1a1d26;
}

.footer-version {
  font-size: 11px;
  color: #3d3f48;
  letter-spacing: 0.5px;
}

/* ── 主内容区 ── */
.main-content {
  flex: 1;
  overflow-y: auto;
  padding: var(--space-xl);
  background:
    radial-gradient(ellipse at 20% 0%, rgba(200,132,60,0.03) 0%, transparent 50%),
    var(--ink-deep);
}

/* ── 页面过渡动画 ── */
.page-fade-enter-active,
.page-fade-leave-active {
  transition: opacity 0.25s ease, transform 0.25s ease;
}

.page-fade-enter-from {
  opacity: 0;
  transform: translateY(6px);
}

.page-fade-leave-to {
  opacity: 0;
  transform: translateY(-6px);
}
</style>
