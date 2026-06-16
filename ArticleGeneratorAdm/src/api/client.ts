/**
 * Axios 实例 + 拦截器 + 请求辅助函数
 *
 * 所有 API 模块统一导入 { get, post, put, del } 发起请求。
 * JWT token 由请求拦截器自动从 localStorage 读取并附加。
 * 401 响应由响应拦截器统一处理：清 token + 跳转登录页。
 */
import axios from "axios";
// 动态导入 ElMessage 避免 jsdom 测试环境报错
let ElMessage: any = null;
async function ensureElMessage() {
  if (!ElMessage) {
    try {
      const mod = await import("element-plus");
      ElMessage = mod.ElMessage;
    } catch {
      // 非浏览器环境静默降级
    }
  }
}

const client = axios.create({
  baseURL: "/api",
  timeout: 30000,
  headers: { "Content-Type": "application/json" },
});

// ── 请求拦截器：自动附加 JWT ──
client.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem("access_token");
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error),
);

// ── 响应拦截器：401 时跳转登录 ──
client.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem("access_token");
      if (window.location.pathname !== "/login") {
        await ensureElMessage();
        if (ElMessage) {
          ElMessage.error("登录已过期，请重新登录");
        }
        window.location.href = "/login";
      }
    }
    return Promise.reject(error);
  },
);

// ── 请求辅助函数 ──
export function get<T = unknown>(url: string, params?: Record<string, unknown>) {
  return client.get<T>(url, { params });
}

export function post<T = unknown>(url: string, data?: unknown) {
  return client.post<T>(url, data);
}

export function put<T = unknown>(url: string, data?: unknown) {
  return client.put<T>(url, data);
}

export function del<T = unknown>(url: string) {
  return client.delete<T>(url);
}

export function patch<T = unknown>(url: string, data?: unknown) {
  return client.patch<T>(url, data);
}

export default client;

// ── 向下兼容：旧版 api 对象（新代码请使用 @/api/index 的模块化 API）──

// 重新导出类型，供旧版视图代码使用
// 视图文件逐步迁移到统一导入，过渡期间保留此导出
export type {
  Hotspot,
  StyleProfile,
  Account,
  HotspotSource,
  Article,
  Provider,
  ScenarioConfig,
  ReferenceArticle,
  GenerationLog,
  DirectionItem,
  OutlinePoint,
  PaginatedResponse,
} from "@/api/types";

import type {
  Hotspot,
  Account,
  Article,
  HotspotSource,
  Provider,
  ScenarioConfig,
  ReferenceArticle,
  GenerationLog,
  DirectionItem,
  OutlinePoint,
  PaginatedResponse,
} from "@/api/types";

/**
 * @deprecated 请逐步迁移到 @/api/index 的模块化 API 导入
 *   旧: import { api } from "@/api/client"
 *   新: import api from "@/api"
 */
export const api = {
  // 热点
  getHotspots: (params?: { status?: string; source?: string; keyword?: string; page?: number; page_size?: number }) =>
    get<PaginatedResponse<Hotspot>>("/hotspots", params as Record<string, unknown>),
  getHotspotSourceOptions: () => get<{ sources: string[] }>("/hotspots/sources"),

  // 账号
  getAccounts: () => get<Account[]>("/accounts"),
  createAccount: (data: { platform: string; account_name: string; lora_path?: string }) =>
    post<Account>("/accounts", data),
  updateAccount: (id: number, data: { platform?: string; account_name?: string; lora_path?: string }) =>
    put<Account>(`/accounts/${id}`, data),
  deleteAccount: (id: number) => del(`/accounts/${id}`),

  // 文章
  getArticles: (params?: { status?: string; page?: number; page_size?: number }) =>
    get<PaginatedResponse<Article>>("/articles", params as Record<string, unknown>),
  getArticle: (id: number) => get<Article>(`/articles/${id}`),
  updateArticleStatus: (id: number, status: string) =>
    patch(`/articles/${id}/status`, { status }),
  updateArticle: (id: number, data: { content?: string; review_notes?: string }) =>
    put(`/articles/${id}`, data),

  // 生成
  triggerGenerate: (accountId: number, hotspotIds?: number[], customTopic?: string) =>
    post("/generate/trigger", { hotspot_ids: hotspotIds || [], account_id: accountId, custom_topic: customTopic || null }),
  generateDirections: (accountId: number, idea: string) =>
    post<{ directions: DirectionItem[] }>("/generate/directions", { account_id: accountId, idea }),
  generateOutline: (accountId: number, idea: string, direction: string) =>
    post<{ outline: OutlinePoint[] }>("/generate/outline", { account_id: accountId, idea, direction }),
  triggerGenerateWithOutline: (accountId: number, customTopic: string, outline: string[]) =>
    post("/generate/trigger", { hotspot_ids: [], account_id: accountId, custom_topic: customTopic, outline }),
  triggerRefine: (articleId: number, keywords: string) =>
    post(`/generate/refine/${articleId}`, { keywords }),
  getTaskStatus: (taskId: string) => get(`/generate/task/${taskId}`),
  getTasksBatch: (taskIds: string[]) =>
    get("/generate/tasks", { task_ids: taskIds.join(",") } as Record<string, unknown>),
  getTaskList: (params?: { status?: string; page?: number; page_size?: number }) =>
    get<PaginatedResponse<unknown>>("/generate/tasks/list", params as Record<string, unknown>),
  cancelTask: (taskId: string) => post(`/generate/tasks/${taskId}/cancel`),
  getRefineTaskStatus: (taskId: string) => get(`/generate/refine-task/${taskId}`),

  // 热点抓取
  crawlHotspots: () => post<{ created: number; total: number; error?: string }>("/hotspots/crawl"),

  // 热点源配置
  getHotspotSourceList: () => get<HotspotSource[]>("/hotspot-sources"),
  createHotspotSource: (data: { name: string; type: string; config?: string; enabled?: boolean }) =>
    post<HotspotSource>("/hotspot-sources", data),
  updateHotspotSource: (id: number, data: { name?: string; type?: string; config?: string; enabled?: boolean }) =>
    put<HotspotSource>(`/hotspot-sources/${id}`, data),
  deleteHotspotSource: (id: number) => del(`/hotspot-sources/${id}`),

  // 供应商管理
  getProviders: () => get<Provider[]>("/providers"),
  createProvider: (data: { name: string; base_url: string; api_key: string; models?: string; enabled?: boolean }) =>
    post<Provider>("/providers", data),
  updateProvider: (id: number, data: { name?: string; base_url?: string; api_key?: string; models?: string; enabled?: boolean }) =>
    put<Provider>(`/providers/${id}`, data),
  deleteProvider: (id: number) => del(`/providers/${id}`),

  // 场景配置
  getScenarioConfigs: () => get<ScenarioConfig[]>("/scenario-configs"),
  createScenarioConfig: (data: { scenario: string; provider_id: number; model: string; system_prompt_template?: string; params?: string; priority?: number; enabled?: boolean }) =>
    post<ScenarioConfig>("/scenario-configs", data),
  updateScenarioConfig: (id: number, data: { provider_id?: number; model?: string; system_prompt_template?: string; params?: string; priority?: number; enabled?: boolean }) =>
    put<ScenarioConfig>(`/scenario-configs/${id}`, data),
  deleteScenarioConfig: (id: number) => del(`/scenario-configs/${id}`),

  // 参考文章
  getReferenceArticles: (accountId: number) =>
    get<ReferenceArticle[]>(`/accounts/${accountId}/reference-articles`),
  createReferenceArticle: (accountId: number, data: { title: string; content: string; source_url?: string; is_benchmark?: boolean }) =>
    post<ReferenceArticle>(`/accounts/${accountId}/reference-articles`, { ...data, account_id: accountId }),
  updateReferenceArticle: (accountId: number, articleId: number, data: { title: string; content: string; source_url?: string; is_benchmark?: boolean }) =>
    put<ReferenceArticle>(`/accounts/${accountId}/reference-articles/${articleId}`, { ...data, account_id: accountId }),
  deleteReferenceArticle: (accountId: number, articleId: number) =>
    del(`/accounts/${accountId}/reference-articles/${articleId}`),

  // 蒸馏
  triggerDistill: (accountId: number) =>
    post(`/accounts/${accountId}/distill`),

  // 生成日志
  getGenerationLogs: (params?: { scenario?: string; page?: number; page_size?: number }) =>
    get<PaginatedResponse<GenerationLog>>("/generation-logs", params as Record<string, unknown>),
};
