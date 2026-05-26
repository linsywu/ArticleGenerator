import { createRouter, createWebHistory, type RouteRecordRaw } from "vue-router";

export const routes: RouteRecordRaw[] = [
  { path: "/", name: "Hotspots", component: () => import("@/views/HotspotsView.vue"), meta: { title: "热点列表" } },
  { path: "/tasks", name: "Tasks", component: () => import("@/views/TasksView.vue"), meta: { title: "任务列表" } },
  { path: "/review", name: "Review", component: () => import("@/views/ReviewView.vue"), meta: { title: "文章评审" } },
  { path: "/publish", name: "Publish", component: () => import("@/views/PublishView.vue"), meta: { title: "待发布" } },
  { path: "/hotspot-sources", name: "HotspotSources", component: () => import("@/views/HotspotSourcesView.vue"), meta: { title: "热点源管理" } },
  { path: "/accounts", name: "Accounts", component: () => import("@/views/AccountsView.vue"), meta: { title: "账号管理" } },
  { path: "/providers", name: "Providers", component: () => import("@/views/ProvidersView.vue"), meta: { title: "API供应商" } },
  { path: "/scenario-configs", name: "ScenarioConfigs", component: () => import("@/views/ScenarioConfigsView.vue"), meta: { title: "场景配置" } },
  { path: "/distill", name: "Distill", component: () => import("@/views/DistillView.vue"), meta: { title: "风格蒸馏" } },
  { path: "/generate", name: "Generate", component: () => import("@/views/GenerateView.vue"), meta: { title: "文章生成" } },
];

const router = createRouter({
  history: createWebHistory(),
  routes,
});

export default router;
