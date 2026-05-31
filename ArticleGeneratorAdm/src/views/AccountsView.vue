<template>
  <div class="accounts-view">
    <header class="page-header">
      <div>
        <h1 class="page-title">账号风格</h1>
        <p class="page-subtitle">管理写作账号及其风格画像，蒸馏提取写作特征</p>
      </div>
      <el-button type="primary" size="large" @click="openCreate">＋ 新增账号</el-button>
    </header>

    <!-- 账号卡片网格 -->
    <div class="accounts-grid">
      <div
        v-for="acc in accounts"
        :key="acc.id"
        class="account-card"
        @click="openDetail(acc)"
      >
        <div class="card-top">
          <div class="card-avatar">{{ acc.account_name.charAt(0) }}</div>
          <div class="card-meta">
            <span class="card-name">{{ acc.account_name }}</span>
            <span class="card-platform">{{ acc.platform }}</span>
          </div>
          <span class="card-badge" :class="{ ready: acc.style_profile_status === 'ready' }">
            {{ acc.style_profile_status === 'ready' ? '画像就绪' : '待蒸馏' }}
          </span>
        </div>
        <div class="card-bottom">
          <span v-if="acc.style_profile_updated_at" class="card-date">
            更新于 {{ acc.style_profile_updated_at.slice(0, 10) }}
          </span>
          <span v-else class="card-date">尚未蒸馏</span>
          <span class="card-actions-inline">
            <el-button size="small" text @click.stop="handleDelete(acc)">删除</el-button>
          </span>
        </div>
      </div>

      <!-- 新增卡片 -->
      <div class="account-card add-card" @click="openCreate">
        <span class="add-icon">＋</span>
        <span class="add-text">新增账号</span>
      </div>
    </div>

    <!-- 详情对话框 -->
    <el-dialog
      v-model="detailVisible"
      :title="editingAccount?.account_name || '账号详情'"
      width="760px"
    >
      <el-tabs v-model="activeTab">
        <!-- Tab 1: 基本信息 -->
        <el-tab-pane label="基本信息" name="basic">
          <el-form :model="form" label-width="80px" class="detail-form">
            <el-form-item label="平台">
              <el-input v-model="form.platform" placeholder="公众号 / 小红书 / 知乎" />
            </el-form-item>
            <el-form-item label="账号名">
              <el-input v-model="form.account_name" placeholder="账号名称" />
            </el-form-item>
          </el-form>
          <div style="text-align:right">
            <el-button type="primary" @click="saveAccount" :loading="saving">保存基本信息</el-button>
          </div>
        </el-tab-pane>

        <!-- Tab 2: 参考文章 -->
        <el-tab-pane label="参考文章" name="articles">
          <div style="margin-bottom:12px">
            <el-button size="small" @click="openAddArticle">＋ 添加文章</el-button>
          </div>
          <div v-if="refArticles.length" class="article-list">
            <div v-for="a in refArticles" :key="a.id" class="article-row">
              <div class="article-info">
                <span class="article-title">{{ a.title }}</span>
                <span v-if="a.is_benchmark" class="article-benchmark">代表篇</span>
              </div>
              <div class="article-actions">
                <el-button size="small" text @click="openEditArticle(a)">编辑</el-button>
                <el-button size="small" text type="danger" @click="handleDeleteArticle(a)">删除</el-button>
              </div>
            </div>
          </div>
          <div v-else class="empty-hint">暂无参考文章，请添加至少一篇文章用于蒸馏</div>
        </el-tab-pane>

        <!-- Tab 3: 风格画像 -->
        <el-tab-pane label="风格画像" name="profile">
          <!-- 结构化画像 -->
          <div v-if="editingAccount?.style_profile_structured" class="profile-grid">
            <div v-for="dim in styleDimensions" :key="dim.key" class="profile-card">
              <div class="profile-card-header">
                <span class="profile-card-icon">{{ dim.icon }}</span>
                <span class="profile-card-label">{{ dim.label }}</span>
              </div>
              <p class="profile-card-content">
                {{ editingAccount.style_profile_structured[dim.key] || '未定义' }}
              </p>
            </div>
          </div>

          <!-- 旧版文本画像 -->
          <div v-else-if="editingAccount?.style_profile" class="legacy-profile">
            <div class="legacy-profile-meta">
              <el-tag type="success" size="small">已生成</el-tag>
              <span class="legacy-date">更新于 {{ editingAccount.style_profile_updated_at?.slice(0, 10) }}</span>
            </div>
            <el-input :model-value="editingAccount.style_profile" type="textarea" :rows="18" readonly />
          </div>

          <!-- 空 -->
          <div v-else class="empty-hint">
            尚未生成风格画像。请在「参考文章」tab 添加文章后点击蒸馏。
          </div>

          <div class="profile-actions">
            <div v-if="editingAccount?.style_profile_status === 'ready'" class="profile-status">
              <span class="status-dot"></span>
              画像就绪 · v{{ editingAccount.style_profile_version }}
            </div>
            <el-button
              type="primary"
              @click="triggerDistill"
              :loading="distilling"
              :disabled="!refArticles.length"
            >
              {{ editingAccount?.style_profile_structured ? '重新蒸馏' : '蒸馏风格' }}
            </el-button>
          </div>
        </el-tab-pane>
      </el-tabs>
    </el-dialog>

    <!-- 添加/编辑参考文章 -->
    <el-dialog
      v-model="articleDialogVisible"
      :title="editingArticleId ? '编辑参考文章' : '添加参考文章'"
      width="520px"
      append-to-body
    >
      <el-form :model="articleForm" label-width="80px">
        <el-form-item label="标题" required>
          <el-input v-model="articleForm.title" placeholder="文章标题" />
        </el-form-item>
        <el-form-item label="正文" required>
          <el-input v-model="articleForm.content" type="textarea" :rows="8" placeholder="粘贴文章正文" />
        </el-form-item>
        <el-form-item label="来源链接">
          <el-input v-model="articleForm.source_url" placeholder="https://...（可选）" />
        </el-form-item>
        <el-form-item label="代表篇">
          <el-switch v-model="articleForm.is_benchmark" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="articleDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="saveArticle" :loading="savingArticle">
          {{ editingArticleId ? '保存' : '添加' }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { api, Account, ReferenceArticle, StyleProfile } from "@/api/client";

const styleDimensions: { key: keyof StyleProfile; label: string; icon: string }[] = [
  { key: 'thinking_pattern', label: '思维特征', icon: '🧠' },
  { key: 'structure_pattern', label: '结构模式', icon: '🏗️' },
  { key: 'sentence_pattern', label: '句式特征', icon: '✍️' },
  { key: 'vocabulary_pattern', label: '词汇偏好', icon: '📝' },
  { key: 'evidence_type', label: '论据类型', icon: '📊' },
  { key: 'taboos', label: '禁忌清单', icon: '🚫' },
  { key: 'blank_leaving', label: '留白程度', icon: '💭' },
]

const accounts = ref<Account[]>([]);
const refArticles = ref<ReferenceArticle[]>([]);
const detailVisible = ref(false);
const editingAccount = ref<Account | null>(null);
const activeTab = ref("basic");
const saving = ref(false);
const distilling = ref(false);

const form = reactive({ platform: "", account_name: "" });

const articleDialogVisible = ref(false);
const editingArticleId = ref<number | null>(null);
const savingArticle = ref(false);
const articleForm = reactive({ title: "", content: "", source_url: "", is_benchmark: false });

async function loadAccounts() {
  const { data } = await api.getAccounts();
  accounts.value = data;
}

async function loadRefArticles(accountId: number) {
  if (!accountId) return;
  try { const { data } = await api.getReferenceArticles(accountId); refArticles.value = data; }
  catch { refArticles.value = []; }
}

function openCreate() {
  editingAccount.value = null;
  form.platform = ""; form.account_name = "";
  refArticles.value = []; activeTab.value = "basic";
  detailVisible.value = true;
}

function openDetail(row: Account) {
  editingAccount.value = row;
  form.platform = row.platform; form.account_name = row.account_name;
  loadRefArticles(row.id); activeTab.value = "basic";
  detailVisible.value = true;
}

async function saveAccount() {
  saving.value = true;
  try {
    if (editingAccount.value?.id) {
      await api.updateAccount(editingAccount.value.id, { ...form });
      ElMessage.success("已更新");
    } else {
      const { data } = await api.createAccount({ ...form });
      editingAccount.value = data;
      ElMessage.success("已创建");
    }
    detailVisible.value = false; await loadAccounts();
  } catch (e: any) { ElMessage.error(e?.response?.data?.detail || "操作失败"); }
  finally { saving.value = false; }
}

async function handleDelete(row: Account) {
  try {
    await ElMessageBox.confirm(`确定删除「${row.account_name}」？`, "确认", { type: "warning" });
    await api.deleteAccount(row.id); ElMessage.success("已删除"); await loadAccounts();
  } catch { /* cancelled */ }
}

function openAddArticle() {
  editingArticleId.value = null;
  articleForm.title = ""; articleForm.content = ""; articleForm.source_url = ""; articleForm.is_benchmark = false;
  articleDialogVisible.value = true;
}

function openEditArticle(row: ReferenceArticle) {
  editingArticleId.value = row.id;
  articleForm.title = row.title; articleForm.content = row.content;
  articleForm.source_url = row.source_url || ""; articleForm.is_benchmark = !!row.is_benchmark;
  articleDialogVisible.value = true;
}

async function saveArticle() {
  if (!editingAccount.value?.id) return;
  savingArticle.value = true;
  try {
    if (editingArticleId.value) {
      await api.updateReferenceArticle(editingAccount.value.id, editingArticleId.value, { ...articleForm, account_id: editingAccount.value.id });
      ElMessage.success("已保存");
    } else {
      await api.createReferenceArticle(editingAccount.value.id, { ...articleForm });
      ElMessage.success("已添加");
    }
    articleDialogVisible.value = false; await loadRefArticles(editingAccount.value.id);
  } catch (e: any) { ElMessage.error(e?.response?.data?.detail || "操作失败"); }
  finally { savingArticle.value = false; }
}

async function handleDeleteArticle(row: ReferenceArticle) {
  if (!editingAccount.value?.id) return;
  try {
    await ElMessageBox.confirm("确定删除此参考文章？", "确认", { type: "warning" });
    await api.deleteReferenceArticle(editingAccount.value.id, row.id);
    ElMessage.success("已删除"); await loadRefArticles(editingAccount.value.id);
  } catch { /* cancelled */ }
}

async function triggerDistill() {
  if (!editingAccount.value?.id) return;
  distilling.value = true;
  try {
    await api.triggerDistill(editingAccount.value.id);
    ElMessage.success("蒸馏任务已提交，请稍后刷新");
    await loadAccounts();
    const updated = accounts.value.find(a => a.id === editingAccount.value?.id);
    if (updated) editingAccount.value = updated;
  } catch (e: any) { ElMessage.error(e?.response?.data?.detail || "蒸馏失败"); }
  finally { distilling.value = false; }
}

onMounted(loadAccounts);
</script>

<style scoped>
/* ── 页面标题 ── */
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: var(--space-xl);
}

.page-title {
  font-family: var(--font-serif);
  font-size: 28px;
  font-weight: 900;
  color: var(--text-on-dark);
  letter-spacing: 1px;
  margin-bottom: 4px;
}

.page-subtitle {
  font-size: 14px;
  color: var(--text-muted);
}

/* ── 账号卡片网格 ── */
.accounts-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 14px;
}

.account-card {
  background: var(--ink-mid);
  border: 1px solid var(--ink-border);
  border-radius: var(--radius-lg);
  padding: 20px;
  cursor: pointer;
  transition: all var(--duration-fast) var(--ease-out);
}

.account-card:hover {
  border-color: var(--text-dim);
  background: var(--ink-surface);
}

.card-top {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 14px;
}

.card-avatar {
  width: 42px;
  height: 42px;
  border-radius: var(--radius-md);
  background: var(--amber-glow);
  color: var(--amber-light);
  display: flex;
  align-items: center;
  justify-content: center;
  font-family: var(--font-serif);
  font-size: 20px;
  font-weight: 700;
  flex-shrink: 0;
}

.card-meta {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.card-name {
  font-size: 15px;
  font-weight: 600;
  color: var(--text-on-dark);
}

.card-platform {
  font-size: 12px;
  color: var(--text-dim);
}

.card-badge {
  font-size: 11px;
  padding: 3px 10px;
  border-radius: 20px;
  background: rgba(139,135,128,0.1);
  color: var(--text-dim);
  font-weight: 500;
}

.card-badge.ready {
  background: rgba(91,140,90,0.12);
  color: var(--green-muted);
}

.card-bottom {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.card-date {
  font-size: 12px;
  color: var(--text-dim);
}

/* 新增卡片 */
.add-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  border-style: dashed;
  border-color: var(--ink-border);
  min-height: 130px;
}

.add-card:hover { border-color: var(--amber); }

.add-icon {
  font-size: 28px;
  color: var(--text-dim);
  font-weight: 300;
}

.add-text {
  font-size: 13px;
  color: var(--text-muted);
}

/* ── 对话框内表单 ── */
.detail-form { margin-bottom: var(--space-md); }

/* ── 参考文章列表 ── */
.article-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.article-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 14px;
  background: var(--ink-surface);
  border-radius: var(--radius-md);
}

.article-info { display: flex; align-items: center; gap: 8px; }

.article-title {
  font-size: 14px;
  color: var(--text-on-dark);
  font-weight: 500;
}

.article-benchmark {
  font-size: 10px;
  padding: 2px 8px;
  border-radius: 10px;
  background: var(--amber-glow);
  color: var(--amber-light);
  font-weight: 600;
}

/* ── 画像卡片网格 ── */
.profile-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 12px;
  margin-bottom: var(--space-md);
}

.profile-card {
  background: var(--ink-surface);
  border-left: 2px solid var(--amber);
  border-radius: 0 var(--radius-md) var(--radius-md) 0;
  padding: 14px 16px;
}

.profile-card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.profile-card-icon { font-size: 15px; }

.profile-card-label {
  font-size: 13px;
  font-weight: 600;
  color: var(--amber-light);
}

.profile-card-content {
  font-size: 13px;
  line-height: 1.7;
  color: var(--text-muted);
  white-space: pre-wrap;
}

/* ── 旧版画像 ── */
.legacy-profile { margin-bottom: var(--space-md); }
.legacy-profile-meta { display: flex; align-items: center; gap: 8px; margin-bottom: 8px; }
.legacy-date { font-size: 12px; color: var(--text-dim); }

/* ── 画像底部操作 ── */
.profile-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: var(--space-md);
  padding-top: var(--space-md);
  border-top: 1px solid var(--ink-border);
}

.profile-status {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: var(--green-muted);
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--green-muted);
}

/* ── 空状态 ── */
.empty-hint {
  text-align: center;
  padding: var(--space-xl);
  color: var(--text-dim);
  font-size: 14px;
}
</style>
