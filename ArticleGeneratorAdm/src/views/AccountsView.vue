<template>
  <div class="accounts-view">
    <header class="page-header">
      <div>
        <h1 class="page-title">账号风格</h1>
        <p class="page-subtitle">管理写作账号及其风格画像，蒸馏提取写作特征</p>
      </div>
      <el-button type="primary" size="large" @click="wizardRef?.show()">＋ 新增账号</el-button>
    </header>

    <div class="accounts-grid" v-loading="loading">
      <AccountCard
        v-for="acc in accounts"
        :key="acc.id"
        :account="acc"
        @edit-basic="openBasicInfo(acc)"
        @distill="openDistill(acc)"
        @word-count="openWordCount(acc)"
        @delete="handleDelete(acc)"
      />

      <div class="add-card" @click="wizardRef?.show()">
        <span class="add-icon">＋</span>
        <span class="add-text">新增账号</span>
      </div>
    </div>

    <AccountWizard ref="wizardRef" @created="onRefresh" />
    <BasicInfoDialog v-model="basicVisible" :account="selectedAccount" @saved="onRefresh" />
    <DistillDialog v-model="distillVisible" :account="selectedAccount" @profile-updated="onRefresh" />
    <WordCountDialog v-model="wordCountVisible" :account="selectedAccount" @saved="onRefresh" />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { api } from "@/api/client";
import type { Account } from "@/api/types";
import { useAccountsStore } from "@/store/accounts";
import AccountCard from "@/components/accounts/AccountCard.vue";
import AccountWizard from "@/components/accounts/AccountWizard.vue";
import BasicInfoDialog from "@/components/accounts/BasicInfoDialog.vue";
import DistillDialog from "@/components/accounts/DistillDialog.vue";
import WordCountDialog from "@/components/accounts/WordCountDialog.vue";

const accountsStore = useAccountsStore();
const accounts = computed(() => accountsStore.accounts);
const loading = ref(false);

const selectedAccount = ref<Account | null>(null);
const basicVisible = ref(false);
const distillVisible = ref(false);
const wordCountVisible = ref(false);
const wizardRef = ref<InstanceType<typeof AccountWizard>>();

function openBasicInfo(acc: Account) { selectedAccount.value = acc; basicVisible.value = true; }
function openDistill(acc: Account) { selectedAccount.value = acc; distillVisible.value = true; }
function openWordCount(acc: Account) { selectedAccount.value = acc; wordCountVisible.value = true; }

async function onRefresh() {
  await accountsStore.invalidate();
  await accountsStore.fetch();
}

async function handleDelete(acc: Account) {
  try {
    await ElMessageBox.confirm(`确定删除「${acc.account_name}」？`, "确认", { type: "warning" });
    await api.deleteAccount(acc.id);
    ElMessage.success("已删除");
    await onRefresh();
  } catch { /* cancelled */ }
}

onMounted(async () => {
  loading.value = true;
  await accountsStore.fetch();
  loading.value = false;
});
</script>

<style scoped>
.page-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: var(--space-xl); }
.page-title { font-family: var(--font-serif); font-size: 28px; font-weight: 900; color: var(--text-on-dark); letter-spacing: 1px; margin-bottom: 4px; }
.page-subtitle { font-size: 14px; color: var(--text-muted); }
.accounts-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 14px; }

.add-card {
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  gap: 8px; border: 1px dashed var(--ink-border); border-radius: var(--radius-lg);
  min-height: 130px; cursor: pointer; transition: all var(--duration-fast) var(--ease-out);
}
.add-card:hover { border-color: var(--amber); }
.add-icon { font-size: 28px; color: var(--text-dim); font-weight: 300; }
.add-text { font-size: 13px; color: var(--text-muted); }
</style>
