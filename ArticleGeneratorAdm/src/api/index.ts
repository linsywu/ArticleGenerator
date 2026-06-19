/**
 * API 模块统一导出
 *
 * 使用方式：
 *   import Api from "@/api";
 *   Api.fetchHotspots(...)
 *   Api.fetchAccounts()
 */
import HotspotsApi from "@/api/modules/hotspots";
import AccountsApi from "@/api/modules/accounts";
import ArticlesApi from "@/api/modules/articles";
import TasksApi from "@/api/modules/tasks";
import ProvidersApi from "@/api/modules/providers";
import MpAccountsApi from "@/api/modules/mpAccounts";

const api = {
  ...HotspotsApi,
  ...AccountsApi,
  ...ArticlesApi,
  ...TasksApi,
  ...ProvidersApi,
  ...MpAccountsApi,
};

export default api;
export type ApiType = typeof api;

// 重新导出类型，方便消费者直接 import { Hotspot, ... } from "@/api"
export * from "@/api/types";
