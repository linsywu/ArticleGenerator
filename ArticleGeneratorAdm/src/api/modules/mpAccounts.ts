/**
 * 公众号 API
 */
import { get, post, put, del, patch } from "@/api/client";
import type { MpAccount } from "@/api/types";

export default {
  fetchMpAccounts: (params?: {
    track_id?: number;
    status?: number;
    search?: string;
  }) => get<MpAccount[]>("/mp-accounts", params as Record<string, unknown>),

  createMpAccount: (data: {
    name: string;
    alias?: string;
    fakeid?: string;
    biz?: string;
    avatar?: string;
    description?: string;
    track_ids?: string;
  }) => post<MpAccount>("/mp-accounts", data),

  getMpAccount: (id: number) => get<MpAccount>(`/mp-accounts/${id}`),

  updateMpAccount: (id: number, data: {
    name?: string;
    alias?: string;
    fakeid?: string;
    biz?: string;
    avatar?: string;
    description?: string;
    track_ids?: string;
  }) => put<MpAccount>(`/mp-accounts/${id}`, data),

  toggleMpAccountStatus: (id: number) =>
    patch(`/mp-accounts/${id}/status`),

  deleteMpAccount: (id: number) => del(`/mp-accounts/${id}`),

  importByName: (data: { names: string[]; credential_id: number }) =>
    post("/mp-accounts/import-by-name", data),

  importByUrl: (data: { urls: string[]; credential_id: number }) =>
    post("/mp-accounts/import-by-url", data),
};
