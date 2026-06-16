/**
 * API 供应商 / 场景配置 / 参考文章 / 蒸馏 / 生成日志 API
 */
import { get, post, put, del } from "@/api/client";
import type {
  Provider,
  ScenarioConfig,
  ReferenceArticle,
  GenerationLog,
  PaginatedResponse,
} from "@/api/types";

export default {
  // ── 供应商 ──
  fetchProviders: () => get<Provider[]>("/providers"),

  createProvider: (data: {
    name: string;
    base_url: string;
    api_key: string;
    models?: string;
    enabled?: boolean;
  }) => post<Provider>("/providers", data),

  updateProvider: (id: number, data: {
    name?: string;
    base_url?: string;
    api_key?: string;
    models?: string;
    enabled?: boolean;
  }) => put<Provider>(`/providers/${id}`, data),

  deleteProvider: (id: number) => del(`/providers/${id}`),

  // ── 场景配置 ──
  fetchScenarioConfigs: () => get<ScenarioConfig[]>("/scenario-configs"),

  createScenarioConfig: (data: {
    scenario: string;
    provider_id: number;
    model: string;
    system_prompt_template?: string;
    params?: string;
    priority?: number;
    enabled?: boolean;
  }) => post<ScenarioConfig>("/scenario-configs", data),

  updateScenarioConfig: (id: number, data: {
    provider_id?: number;
    model?: string;
    system_prompt_template?: string;
    params?: string;
    priority?: number;
    enabled?: boolean;
  }) => put<ScenarioConfig>(`/scenario-configs/${id}`, data),

  deleteScenarioConfig: (id: number) => del(`/scenario-configs/${id}`),

  // ── 参考文章 ──
  fetchReferenceArticles: (accountId: number) =>
    get<ReferenceArticle[]>(`/accounts/${accountId}/reference-articles`),

  createReferenceArticle: (
    accountId: number,
    data: {
      title: string;
      content: string;
      source_url?: string;
      is_benchmark?: boolean;
    },
  ) => post<ReferenceArticle>(`/accounts/${accountId}/reference-articles`, {
    ...data,
    account_id: accountId,
  }),

  updateReferenceArticle: (
    accountId: number,
    articleId: number,
    data: {
      title: string;
      content: string;
      source_url?: string;
      is_benchmark?: boolean;
    },
  ) =>
    put<ReferenceArticle>(
      `/accounts/${accountId}/reference-articles/${articleId}`,
      { ...data, account_id: accountId },
    ),

  deleteReferenceArticle: (accountId: number, articleId: number) =>
    del(`/accounts/${accountId}/reference-articles/${articleId}`),

  // ── 风格蒸馏 ──
  triggerDistill: (accountId: number) =>
    post(`/accounts/${accountId}/distill`),

  // ── 生成日志 ──
  fetchGenerationLogs: (params?: {
    scenario?: string;
    page?: number;
    page_size?: number;
  }) => get<PaginatedResponse<GenerationLog>>(
    "/generation-logs",
    params as Record<string, unknown>,
  ),
};
