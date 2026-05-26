<template>
  <div class="distill-view">
    <h2>风格蒸馏</h2>
    <div class="distill-layout">
      <!-- 左侧：账号列表 -->
      <div class="account-panel">
        <div class="panel-title">账号列表</div>
        <div v-if="!accounts.length" class="empty-hint">暂无账号</div>
        <div
          v-for="acc in accounts"
          :key="acc.id"
          class="account-item"
          :class="{ active: selectedId === acc.id }"
          @click="selectAccount(acc)"
        >
          <div class="account-name">{{ acc.account_name }}</div>
          <div class="account-platform">{{ acc.platform }}</div>
          <el-tag v-if="acc.style_profile" type="success" size="small">已生成画像</el-tag>
          <el-tag v-else type="info" size="small">未生成</el-tag>
        </div>
      </div>

      <!-- 右侧：参考文章 + 风格画像 -->
      <div class="content-panel">
        <div v-if="!selectedAccount" class="empty-hint">请从左侧选择一个账号</div>
        <template v-else>
          <el-tabs v-model="activeTab">
            <!-- 参考文章 Tab -->
            <el-tab-pane label="参考文章" name="articles">
              <div style="margin-bottom:12px">
                <el-button type="primary" size="small" @click="openAddArticle">添加文章</el-button>
                <span class="article-count">共 {{ refArticles.length }} 篇</span>
              </div>
              <el-table :data="refArticles" stripe size="small">
                <el-table-column prop="title" label="标题" min-width="200" />
                <el-table-column label="代表篇" width="80">
                  <template #default="{ row }">{{ row.is_benchmark ? '是' : '否' }}</template>
                </el-table-column>
                <el-table-column label="操作" width="80">
                  <template #default="{ row }">
                    <el-button size="small" type="danger" @click="handleDeleteArticle(row)">删除</el-button>
                  </template>
                </el-table-column>
              </el-table>
              <div v-if="!refArticles.length" class="empty-hint">暂无参考文章，请添加</div>
            </el-tab-pane>

            <!-- 风格画像 Tab -->
            <el-tab-pane label="风格画像" name="profile">
              <div v-if="selectedAccount.style_profile">
                <div class="profile-meta">
                  <el-tag type="success">已生成</el-tag>
                  <span v-if="selectedAccount.style_profile_updated_at" class="profile-date">
                    更新于 {{ selectedAccount.style_profile_updated_at.slice(0, 10) }}
                  </span>
                </div>
                <el-input
                  v-model="selectedAccount.style_profile"
                  type="textarea"
                  :rows="14"
                  readonly
                  class="profile-textarea"
                />
              </div>
              <div v-else class="empty-hint">
                {{ distilling ? '正在蒸馏中，请稍候...' : '尚未生成风格画像' }}
              </div>
              <div style="margin-top:16px">
                <el-button
                  type="warning"
                  class="distill-btn"
                  @click="triggerDistill"
                  :loading="distilling"
                  :disabled="!refArticles.length"
                >
                  {{ distilling ? '蒸馏中...' : '蒸馏风格' }}
                </el-button>
                <span v-if="!refArticles.length" class="hint-text">请先添加参考文章</span>
              </div>
            </el-tab-pane>
          </el-tabs>
        </template>
      </div>
    </div>

    <!-- 添加参考文章对话框 -->
    <el-dialog v-model="articleDialogVisible" title="添加参考文章" width="560px">
      <el-form :model="articleForm" label-width="80px">
        <el-form-item label="标题" required>
          <el-input v-model="articleForm.title" placeholder="文章标题" />
        </el-form-item>
        <el-form-item label="正文" required>
          <el-input v-model="articleForm.content" type="textarea" :rows="8" placeholder="粘贴文章正文" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="articleDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="saveArticle" :loading="savingArticle">添加</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { api, Account, ReferenceArticle } from "@/api/client";

const accounts = ref<Account[]>([]);
const selectedId = ref<number | null>(null);
const selectedAccount = ref<Account | null>(null);
const refArticles = ref<ReferenceArticle[]>([]);
const activeTab = ref("articles");
const distilling = ref(false);

const articleDialogVisible = ref(false);
const savingArticle = ref(false);
const articleForm = reactive({ title: "", content: "" });

let pollTimer: ReturnType<typeof setInterval> | null = null;

onMounted(loadAccounts);

async function loadAccounts() {
  const { data } = await api.getAccounts();
  accounts.value = data;
}

function selectAccount(acc: Account) {
  selectedId.value = acc.id;
  selectedAccount.value = acc;
  loadRefArticles(acc.id);
}

async function loadRefArticles(accountId: number) {
  try {
    const { data } = await api.getReferenceArticles(accountId);
    refArticles.value = data;
  } catch {
    refArticles.value = [];
  }
}

function openAddArticle() {
  articleForm.title = "";
  articleForm.content = "";
  articleDialogVisible.value = true;
}

async function saveArticle() {
  if (!selectedAccount.value?.id) return;
  savingArticle.value = true;
  try {
    await api.createReferenceArticle(selectedAccount.value.id, { ...articleForm, is_benchmark: false });
    ElMessage.success("已添加");
    articleDialogVisible.value = false;
    await loadRefArticles(selectedAccount.value.id);
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || "操作失败");
  } finally {
    savingArticle.value = false;
  }
}

async function handleDeleteArticle(row: ReferenceArticle) {
  if (!selectedAccount.value?.id) return;
  try {
    await ElMessageBox.confirm("确定删除此参考文章？", "确认", { type: "warning" });
    await api.deleteReferenceArticle(selectedAccount.value.id, row.id);
    ElMessage.success("已删除");
    await loadRefArticles(selectedAccount.value.id);
  } catch {
    /* cancelled */
  }
}

async function triggerDistill() {
  if (!selectedAccount.value?.id || !refArticles.value.length) return;
  distilling.value = true;
  try {
    const { data } = await api.triggerDistill(selectedAccount.value.id);
    ElMessage.success("蒸馏任务已提交");
    startPolling();
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || "蒸馏失败");
    distilling.value = false;
  }
}

function startPolling() {
  if (pollTimer) clearInterval(pollTimer);
  pollTimer = setInterval(async () => {
    if (!selectedAccount.value?.id) return;
    const { data } = await api.getAccounts();
    const updated = data.find((a: Account) => a.id === selectedAccount.value?.id);
    if (updated?.style_profile) {
      selectedAccount.value = updated;
      accounts.value = data;
      distilling.value = false;
      if (pollTimer) clearInterval(pollTimer);
      pollTimer = null;
      activeTab.value = "profile";
      ElMessage.success("风格画像已生成");
    }
  }, 3000);
}
</script>

<style scoped>
.distill-view { max-width: 1200px; margin: 0 auto; }
.distill-layout { display: flex; gap: 24px; margin-top: 16px; min-height: 500px; }
.account-panel {
  width: 240px; flex-shrink: 0; border: 1px solid #e0e0e0; border-radius: 8px;
  padding: 12px; overflow-y: auto;
}
.content-panel { flex: 1; border: 1px solid #e0e0e0; border-radius: 8px; padding: 20px; }
.panel-title { font-size: 14px; font-weight: 600; color: #333; margin-bottom: 12px; }
.account-item {
  padding: 10px 12px; border-radius: 6px; cursor: pointer; margin-bottom: 6px;
  border: 1px solid transparent; transition: all 0.2s;
}
.account-item:hover { background: #f5f7fa; }
.account-item.active { border-color: #409eff; background: #ecf5ff; }
.account-name { font-weight: 500; font-size: 14px; }
.account-platform { font-size: 12px; color: #999; margin-top: 2px; margin-bottom: 4px; }
.empty-hint { color: #999; text-align: center; padding: 40px 0; }
.profile-meta { margin-bottom: 8px; display: flex; align-items: center; gap: 8px; }
.profile-date { font-size: 12px; color: #999; }
.profile-textarea { margin-top: 8px; }
.hint-text { color: #999; margin-left: 8px; font-size: 12px; }
.article-count { margin-left: 12px; color: #999; font-size: 13px; }
</style>
