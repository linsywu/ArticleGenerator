import { createRouter, createWebHistory, type RouteRecordRaw } from "vue-router";

export const routes: RouteRecordRaw[] = [
  {
    path: "/login",
    name: "Login",
    component: () => import("@/views/LoginView.vue"),
    meta: { title: "登录", noAuth: true },
  },
  {
    path: "/",
    component: () => import("@/views/LayoutView.vue"),
    children: [
      { path: "", redirect: "/create" },
      { path: "create", name: "Create", component: () => import("@/views/CreateView.vue"), meta: { title: "文章创作" } },
      { path: "review", name: "Review", component: () => import("@/views/ReviewView.vue"), meta: { title: "评审队列" } },
      { path: "publish", name: "Publish", component: () => import("@/views/PublishView.vue"), meta: { title: "文章发布" } },
      { path: "accounts", name: "Accounts", component: () => import("@/views/AccountsView.vue"), meta: { title: "账号风格" } },
      { path: "inspiration", name: "Inspiration", component: () => import("@/views/HotspotsView.vue"), meta: { title: "灵感墙" } },
      { path: "tasks", name: "Tasks", component: () => import("@/views/TasksView.vue"), meta: { title: "任务记录" } },
      { path: "hotspot-sources", name: "HotspotSources", component: () => import("@/views/HotspotSourcesView.vue"), meta: { title: "热点源管理" } },
      { path: "providers", name: "Providers", component: () => import("@/views/ProvidersView.vue"), meta: { title: "API供应商" } },
      { path: "scenario-configs", name: "ScenarioConfigs", component: () => import("@/views/ScenarioConfigsView.vue"), meta: { title: "场景配置" } },
      { path: "tracks", name: "Tracks", component: () => import("@/views/TracksView.vue"), meta: { title: "赛道管理" } },
      { path: "mp-accounts", name: "MpAccounts", component: () => import("@/views/MpAccountsView.vue"), meta: { title: "公众号管理" } },
      { path: "credentials", name: "Credentials", component: () => import("@/views/CredentialsView.vue"), meta: { title: "采集凭证" } },
      { path: "collect-tasks", name: "CollectTasks", component: () => import("@/views/CollectTasksView.vue"), meta: { title: "采集任务" } },
      { path: "tasks-center", name: "TaskCenter", component: () => import("@/views/TaskCenterView.vue"), meta: { title: "任务中心" } },
      { path: "materials", name: "Materials", component: () => import("@/views/MaterialsView.vue"), meta: { title: "素材中心" } },
      { path: "collect-logs", name: "CollectLogs", component: () => import("@/views/CollectLogsView.vue"), meta: { title: "采集日志" } },
    ],
  },
];

const router = createRouter({
  history: createWebHistory(),
  routes,
});

router.beforeEach((to, _from, next) => {
  const token = localStorage.getItem("access_token");

  if (to.meta.noAuth) {
    if (token && to.path === "/login") {
      next("/");
    } else {
      next();
    }
  } else {
    if (!token) {
      next("/login");
    } else {
      next();
    }
  }
});

export default router;
