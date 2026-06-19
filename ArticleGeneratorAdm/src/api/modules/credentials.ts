/**
 * 采集凭证 API
 */
import { get, post, put, del } from "@/api/client";
import type { MpCredential } from "@/api/types";

export default {
  fetchCredentials: () => get<MpCredential[]>("/credentials"),

  createCredential: (data: {
    name: string;
    token: string;
    cookie: string;
  }) => post<MpCredential>("/credentials", data),

  getCredential: (id: number) => get<MpCredential>(`/credentials/${id}`),

  updateCredential: (id: number, data: {
    name?: string;
    token?: string;
    cookie?: string;
  }) => put<MpCredential>(`/credentials/${id}`, data),

  deleteCredential: (id: number) => del(`/credentials/${id}`),

  checkCredential: (id: number) => post(`/credentials/${id}/check`),
};
