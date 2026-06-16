/**
 * 账号 API
 */
import { get, post, put, del } from "@/api/client";
import type { Account } from "@/api/types";

export default {
  fetchAccounts: () => get<Account[]>("/accounts"),

  createAccount: (data: {
    platform: string;
    account_name: string;
    lora_path?: string;
    sample_articles?: string;
  }) => post<Account>("/accounts", data),

  updateAccount: (id: number, data: {
    platform?: string;
    account_name?: string;
    lora_path?: string;
    sample_articles?: string;
  }) => put<Account>(`/accounts/${id}`, data),

  deleteAccount: (id: number) => del(`/accounts/${id}`),
};
