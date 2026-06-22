/**
 * 生成任务 API（含方向生成、大纲生成）
 */
import { get, post } from "@/api/client";
import type { PaginatedResponse, DirectionItem, OutlinePoint, UnifiedTaskItem, UnifiedTasksResponse } from "@/api/types";

export default {
  triggerGenerate: (
    accountId: number,
    hotspotIds?: number[],
    customTopic?: string,
    outline?: string[],
  ) => post("/generate/trigger", {
    hotspot_ids: hotspotIds || [],
    account_id: accountId,
    custom_topic: customTopic || null,
    outline,
  }),

  triggerGenerateWithOutline: (
    accountId: number,
    topic: string,
    outline?: string[],
  ) => post("/generate/trigger", {
    hotspot_ids: [],
    account_id: accountId,
    custom_topic: topic,
    outline: outline || [],
  }),

  generateTitles: (accountId: number, idea: string, direction: string, outline?: string[]) =>
    post<{ task_id: string; status: string; message: string }>("/generate/titles", { account_id: accountId, idea, direction, outline: outline || [] }),

  triggerRefine: (articleId: number, keywords: string) =>
    post(`/generate/refine/${articleId}`, { keywords }),

  fetchTaskStatus: (taskId: string) => get(`/generate/task/${taskId}`),

  fetchTasksBatch: (taskIds: string[]) =>
    get("/generate/tasks", { task_ids: taskIds.join(",") } as Record<string, unknown>),

  fetchTaskList: (params?: {
    status?: string;
    page?: number;
    page_size?: number;
  }) => get<UnifiedTasksResponse>("/generate/tasks/list", params as Record<string, unknown>),

  cancelTask: (taskId: string) => post(`/generate/tasks/${taskId}/cancel`),

  fetchRefineTaskStatus: (taskId: string) => get(`/generate/refine-task/${taskId}`),

  generateDirections: (accountId: number, idea: string) =>
    post<{ directions: DirectionItem[] }>("/generate/directions", {
      account_id: accountId,
      idea,
    }),

  generateOutline: (accountId: number, idea: string, direction: string) =>
    post<{ outline: OutlinePoint[] }>("/generate/outline", {
      account_id: accountId,
      idea,
      direction,
    }),
};
