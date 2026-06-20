/**
 * 采集日志 API
 */
import { get } from "@/api/client";
import type { CollectLog } from "@/api/types";

export default {
  fetchCollectLogs: (params?: { task_id?: number; page?: number; page_size?: number }) =>
    get<{ data: CollectLog[]; total: number }>("/collect-logs", params as Record<string, unknown>),
};
