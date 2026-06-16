/**
 * API 请求封装
 */
import axios from "axios";

const client = axios.create({
  baseURL: "/api",
  timeout: 30000,
  headers: { "Content-Type": "application/json" },
});

export interface Hotspot {
  id: number;
  title: string;
  source: string;
  heat: number;
  summary?: string;
  url?: string;
  status: string;
  created_at: string;
}

export interface StyleProfile {
  thinking_pattern: string
  structure_pattern: string
  sentence_pattern: string
  vocabulary_pattern: string
  evidence_type: string
  taboos: string
  blank_leaving: string
}

export interface Account {
  id: number;
  platform: string;
  account_name: string;
  lora_path?: string;
  sample_articles?: string;
  style_profile?: string;
  style_profile_updated_at?: string;
  style_profile_structured?: StyleProfile | null;
  style_profile_version?: number;
  style_profile_status?: string;
  word_count_options?: string;   // JSON: ["1500字左右","2000到3000字","3000字以上"]
  word_count?: string;   // 默认字数
  created_at: string;
}

export interface HotspotSource {
  id: number;
  name: string;
  type: string;
  config?: string;
  enabled: boolean;
  created_at: string;
}

export interface Article {
  id: number;
  title?: string;
  hotspot_id: number;
  account_id: number;
  content: string;
  status: string;
  refine_history?: string;
  quality_score?: number;
  compliance_score?: number;
  review_notes?: string;
  published_at?: string;
  created_at: string;
  updated_at: string;
  hotspot?: Hotspot;
  account?: Account;
}

export interface Provider {
  id: number;
  name: string;
  base_url: string;
  api_key: string;
  models?: string;
  enabled: boolean;
  created_at: string;
}

export interface ScenarioConfig {
  id: number;
  scenario: string;
  provider_id: number;
  model: string;
  system_prompt_template?: string;
  params?: string;
  priority: number;
  description?: string;
  sort_order?: number;
  enabled: boolean;
  provider?: Provider;
  created_at: string;
}

export interface ReferenceArticle {
  id: number;
  account_id: number;
  title: string;
  content: string;
  source_url?: string;
  embedding?: string;
  is_benchmark: boolean;
  created_at: string;
}

export interface GenerationLog {
  id: number;
  scenario: string;
  provider_id?: number;
  model?: string;
  prompt_tokens: number;
  completion_tokens: number;
  latency_ms: number;
  status: string;
  error_message?: string;
  created_at: string;
}

export interface UnifiedTaskItem {
  task_id: string;
  task_type: string;
  status: string;
  target: string;
  article_id?: number;
  account_name?: string;
  extra_info?: string;
  error_message?: string;
  created_at: string;
  updated_at: string;
}

export interface UnifiedTasksResponse {
  tasks: UnifiedTaskItem[];
  running_count: number;
  pending_count: number;
  completed_count: number;
}

export interface DirectionItem { id: string; title: string }
export interface OutlinePoint { order: number; point: string }

export interface PaginatedResponse<T> {
  data: T[];
  total: number;
}

export const api = {
  // 热点
  getHotspots: (params?: { status?: string; source?: string; keyword?: string; page?: number; page_size?: number }) =>
    client.get<PaginatedResponse<Hotspot>>("/hotspots", { params }),
  getHotspotSourceOptions: () => client.get<{ sources: string[] }>("/hotspots/sources"),

  // 账号
  getAccounts: () => client.get<Account[]>("/accounts"),
  createAccount: (data: { platform: string; account_name: string; lora_path?: string }) =>
    client.post<Account>("/accounts", data),
  updateAccount: (id: number, data: { platform?: string; account_name?: string; lora_path?: string }) =>
    client.put<Account>(`/accounts/${id}`, data),
  deleteAccount: (id: number) => client.delete(`/accounts/${id}`),

  // 文章
  getArticles: (params?: { status?: string; page?: number; page_size?: number }) =>
    client.get<PaginatedResponse<Article>>("/articles", { params }),
  getArticle: (id: number) => client.get<Article>(`/articles/${id}`),
  updateArticleStatus: (id: number, status: string) =>
    client.patch(`/articles/${id}/status`, { status }),
  updateArticle: (id: number, data: { content?: string; review_notes?: string }) =>
    client.put(`/articles/${id}`, data),

  // 生成
  triggerGenerate: (accountId: number, hotspotIds?: number[], customTopic?: string) =>
    client.post("/generate/trigger", { hotspot_ids: hotspotIds || [], account_id: accountId, custom_topic: customTopic || null }),
  // 方向 + 大纲
  generateDirections: (accountId: number, idea: string, wordCount?: string) =>
    client.post<{ directions: DirectionItem[] }>("/generate/directions", { account_id: accountId, idea, word_count: wordCount || null }),
  generateOutline: (accountId: number, idea: string, direction: string) =>
    client.post<{ outline: OutlinePoint[] }>("/generate/outline", { account_id: accountId, idea, direction }),
  generateTitles: (accountId: number, idea: string, direction: string, outline: string[]) =>
    client.post<{ titles: string[] }>("/generate/titles", { account_id: accountId, idea, direction, outline }),
  triggerGenerateWithOutline: (accountId: number, customTopic: string, outline: string[], wordCount?: string) =>
    client.post("/generate/trigger", { hotspot_ids: [], account_id: accountId, custom_topic: customTopic, outline, word_count: wordCount || null }),
  triggerRefine: (articleId: number, keywords: string) =>
    client.post(`/generate/refine/${articleId}`, { keywords }),
  getTaskStatus: (taskId: string) => client.get(`/generate/task/${taskId}`),
  getTasksBatch: (taskIds: string[]) =>
    client.get("/generate/tasks", { params: { task_ids: taskIds.join(",") } }),
  getTaskList: (params?: { status?: string; page?: number; page_size?: number }) =>
    client.get<PaginatedResponse<unknown>>("/generate/tasks/list", { params }),
  cancelTask: (taskId: string) => client.post(`/generate/tasks/${taskId}/cancel`),
  getRefineTaskStatus: (taskId: string) => client.get(`/generate/refine-task/${taskId}`),

  // 统一任务中心
  getUnifiedTasks: (params?: { status?: string; limit?: number }) =>
    client.get<UnifiedTasksResponse>("/tasks/unified", { params }),

  // 热点抓取
  crawlHotspots: () => client.post<{ created: number; total: number; error?: string }>("/hotspots/crawl"),

  // 热点源配置（hotspot_sources 表）
  getHotspotSourceList: () => client.get<HotspotSource[]>("/hotspot-sources"),
  createHotspotSource: (data: { name: string; type: string; config?: string; enabled?: boolean }) =>
    client.post<HotspotSource>("/hotspot-sources", data),
  updateHotspotSource: (id: number, data: { name?: string; type?: string; config?: string; enabled?: boolean }) =>
    client.put<HotspotSource>(`/hotspot-sources/${id}`, data),
  deleteHotspotSource: (id: number) => client.delete(`/hotspot-sources/${id}`),

  // 供应商管理
  getProviders: () => client.get<Provider[]>("/providers"),
  createProvider: (data: { name: string; base_url: string; api_key: string; models?: string; enabled?: boolean }) =>
    client.post<Provider>("/providers", data),
  updateProvider: (id: number, data: { name?: string; base_url?: string; api_key?: string; models?: string; enabled?: boolean }) =>
    client.put<Provider>(`/providers/${id}`, data),
  deleteProvider: (id: number) => client.delete(`/providers/${id}`),

  // 场景配置
  getScenarioConfigs: () => client.get<ScenarioConfig[]>("/scenario-configs"),
  createScenarioConfig: (data: { scenario: string; provider_id: number; model: string; system_prompt_template?: string; params?: string; priority?: number; enabled?: boolean }) =>
    client.post<ScenarioConfig>("/scenario-configs", data),
  updateScenarioConfig: (id: number, data: { provider_id?: number; model?: string; system_prompt_template?: string; params?: string; priority?: number; enabled?: boolean }) =>
    client.put<ScenarioConfig>(`/scenario-configs/${id}`, data),
  deleteScenarioConfig: (id: number) => client.delete(`/scenario-configs/${id}`),
  activateScenarioConfig: (id: number) => client.post(`/scenario-configs/${id}/activate`),

  // 参考文章
  getReferenceArticles: (accountId: number) =>
    client.get<ReferenceArticle[]>(`/accounts/${accountId}/reference-articles`),
  createReferenceArticle: (accountId: number, data: { title: string; content: string; source_url?: string; is_benchmark?: boolean }) =>
    client.post<ReferenceArticle>(`/accounts/${accountId}/reference-articles`, { ...data, account_id: accountId }),
  updateReferenceArticle: (accountId: number, articleId: number, data: { title: string; content: string; source_url?: string; is_benchmark?: boolean; account_id: number }) =>
    client.put<ReferenceArticle>(`/accounts/${accountId}/reference-articles/${articleId}`, data),
  deleteReferenceArticle: (accountId: number, articleId: number) =>
    client.delete(`/accounts/${accountId}/reference-articles/${articleId}`),

  // 蒸馏
  triggerDistill: (accountId: number) =>
    client.post(`/accounts/${accountId}/distill`),

  // 生成日志
  getGenerationLogs: (params?: { scenario?: string; page?: number; page_size?: number }) =>
    client.get<PaginatedResponse<GenerationLog>>("/generation-logs", { params }),
};
