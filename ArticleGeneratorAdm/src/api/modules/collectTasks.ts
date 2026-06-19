/**
 * 采集任务 API
 */
import { get, post, put, del } from "@/api/client";
import type { CollectTask } from "@/api/types";

export default {
  fetchCollectTasks: (params?: { status?: string }) =>
    get<CollectTask[]>("/collect-tasks", params as Record<string, unknown>),

  createCollectTask: (data: {
    name: string;
    credential_id: number;
    track_ids?: string;
    account_ids?: string;
    collect_mode?: string;
    date_start?: string;
    date_end?: string;
    schedule_type?: string;
    cron?: string;
    interval_hours?: number;
  }) => post<CollectTask>("/collect-tasks", data),

  getCollectTask: (id: number) => get<CollectTask>(`/collect-tasks/${id}`),

  updateCollectTask: (id: number, data: {
    name?: string;
    credential_id?: number;
    track_ids?: string;
    account_ids?: string;
    collect_mode?: string;
    date_start?: string;
    date_end?: string;
    schedule_type?: string;
    cron?: string;
    interval_hours?: number;
  }) => put<CollectTask>(`/collect-tasks/${id}`, data),

  deleteCollectTask: (id: number) => del(`/collect-tasks/${id}`),

  executeTask: (id: number) => post(`/collect-tasks/${id}/execute`),

  pauseTask: (id: number) => post(`/collect-tasks/${id}/pause`),

  resumeTask: (id: number) => post(`/collect-tasks/${id}/resume`),
};
