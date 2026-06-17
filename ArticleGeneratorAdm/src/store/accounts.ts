/**
 * accounts store — 账号列表跨页共享
 */
import { defineStore } from "pinia";
import { api, type Account } from "@/api/client";

export const useAccountsStore = defineStore("accounts", {
  state: () => ({
    accounts: [] as Account[],
    loading: false,
    loaded: false,
  }),
  actions: {
    async fetch() {
      if (this.loaded) return;
      this.loading = true;
      try {
        const { data } = await api.getAccounts();
        this.accounts = data;
        this.loaded = true;
      } finally {
        this.loading = false;
      }
    },
    invalidate() {
      this.loaded = false;
    },
  },
});
