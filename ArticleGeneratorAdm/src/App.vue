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
