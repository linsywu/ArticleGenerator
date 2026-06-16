import { createRouter, createWebHistory, type RouteRecordRaw } from "vue-router";

export const routes: RouteRecordRaw[] = [
  { path: "/", redirect: "/create" },
  { path: "/login", name: "Login", component: () => import("@/views/LoginView.vue"), meta: { title: "登录", noAuth: true } },
  { path: "/create", name: "Create", component: () => import("@/views/CreateView.vue"), meta: { title: "文章创作" } },
  { path: "/review", name: "Review", component: () => import("@/views/ReviewView.vue"), meta: { title: "评审队列" } },
  { path: "/publish", name: "Publish", component: () => import("@/views/PublishView.vue"), meta: { title: "文章发布" } },
  { path: "/accounts", name: "Accounts", component: () => import("@/views/AccountsView.vue"), meta: { title: "账号风格" } },
  { path: "/inspiration", name: "Inspiration", component: () => import("@/views/HotspotsView.vue"), meta: { title: "灵感墙" } },
  { path: "/tasks", name: "Tasks", component: () => import("@/views/TasksView.vue"), meta: { title: "任务记录" } },
  { path: "/hotspot-sources", name: "HotspotSources", component: () => import("@/views/HotspotSourcesView.vue"), meta: { title: "热点源管理" } },
  { path: "/providers", name: "Providers", component: () => import("@/views/ProvidersView.vue"), meta: { title: "API供应商" } },
  { path: "/scenario-configs", name: "ScenarioConfigs", component: () => import("@/views/ScenarioConfigsView.vue"), meta: { title: "场景配置" } },
  { path: "/tasks-center", name: "TaskCenter", component: () => import("@/views/TaskCenterView.vue"), meta: { title: "任务中心" } },
];

const router = createRouter({
  history: createWebHistory(),
  routes,
});

// ── 路由守卫：未登录跳转登录页 ──
router.beforeEach((to, _from, next) => {
  const token = localStorage.getItem("access_token");

  if (to.meta.noAuth) {
    // /login 等公开页面
    if (token && to.path === "/login") {
      // 已登录时访问登录页，跳转首页
      next("/");
    } else {
      next();
    }
  } else {
    // 需要认证的页面
    if (!token) {
      next("/login");
    } else {
      next();
    }
  }
});

export default router;
