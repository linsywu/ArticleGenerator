<template>
  <div class="accounts-view">
    <div class="page-header">
      <h2>账号管理</h2>
      <el-button type="primary" @click="openCreate">新增账号</el-button>
    </div>

    <el-table :data="accounts" stripe @row-click="openDetail" style="cursor:pointer">
      <el-table-column prop="platform" label="平台" width="120" />
      <el-table-column prop="account_name" label="账号名" />
      <el-table-column label="风格画像" width="100">
        <template #default="{ row }">
          <el-tag v-if="row.style_profile" type="success" size="small">已生成</el-tag>
          <el-tag v-else type="info" size="small">未生成</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="160">
        <template #default="{ row }">
          <el-button size="small" @click.stop="openDetail(row)">详情</el-button>
          <el-button size="small" type="danger" @click.stop="handleDelete(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 详情/编辑对话框 -->
    <el-dialog v-model="detailVisible" :title="editingAccount?.account_name || '账号详情'" width="720px">
      <el-tabs v-model="activeTab">
        <el-tab-pane label="基本信息" name="basic">
          <el-form :model="form" label-width="100px">
            <el-form-item label="平台">
              <el-input v-model="form.platform" placeholder="公众号/小红书/知乎" />
            </el-form-item>
            <el-form-item label="账号名">
              <el-input v-model="form.account_name" placeholder="账号名称" />
            </el-form-item>
          </el-form>
          <el-button type="primary" @click="saveAccount" :loading="saving">保存基本信息</el-button>
        </el-tab-pane>

        <el-tab-pane label="参考文章" name="articles">
          <div style="margin-bottom:12px">
            <el-button type="primary" size="small" @click="openAddArticle">添加文章</el-button>
          </div>
          <el-table :data="refArticles" stripe size="small">
            <el-table-column prop="title" label="标题" />
            <el-table-column label="代表篇" width="80">
              <template #default="{ row }">🏆 {{ row.is_benchmark ? '是' : '否' }}</template>
            </el-table-column>
            <el-table-column label="操作" width="160">
              <template #default="{ row }">
                <el-button size="small" @click="openEditArticle(row)">编辑</el-button>
                <el-button size="small" type="danger" @click="handleDeleteArticle(row)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
          <div v-if="!refArticles.length" style="color:#999;padding:20px;text-align:center">
            暂无参考文章，请添加
          </div>
        </el-tab-pane>

        <el-tab-pane label="风格画像" name="profile">
          <div v-if="editingAccount?.style_profile">
            <div style="margin-bottom:8px">
              <el-tag type="success">已生成</el-tag>
              <span style="color:#999;margin-left:8px;font-size:12px">
                更新于 {{ editingAccount.style_profile_updated_at?.slice(0, 10) }}
              </span>
            </div>
            <el-input v-model="editingAccount.style_profile" type="textarea" :rows="10" readonly />
          </div>
          <div v-else style="color:#999;padding:20px;text-align:center">
            尚未生成风格画像
          </div>
          <div style="margin-top:12px">
            <el-button type="warning" @click="triggerDistill" :loading="distilling" :disabled="!refArticles.length">
              蒸馏风格
            </el-button>
            <span v-if="!refArticles.length" style="color:#999;margin-left:8px;font-size:12px">
              请先在「参考文章」tab添加文章
            </span>
          </div>
        </el-tab-pane>
      </el-tabs>
    </el-dialog>

    <!-- 添加/编辑参考文章子对话框 -->
    <el-dialog v-model="articleDialogVisible" :title="editingArticleId ? '编辑参考文章' : '添加参考文章'" width="560px" append-to-body>
      <el-form :model="articleForm" label-width="80px">
        <el-form-item label="标题" required>
          <el-input v-model="articleForm.title" placeholder="文章标题" />
        </el-form-item>
        <el-form-item label="正文" required>
          <el-input v-model="articleForm.content" type="textarea" :rows="8" placeholder="粘贴文章正文（或通过链接自动解析）" />
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
        <el-button type="primary" @click="saveArticle" :loading="savingArticle">{{ editingArticleId ? '保存' : '添加' }}</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { api, Account, ReferenceArticle } from "@/api/client";

const accounts = ref<Account[]>([]);
const refArticles = ref<ReferenceArticle[]>([]);
const detailVisible = ref(false);
const editingAccount = ref<Account | null>(null);
const activeTab = ref("basic");
const saving = ref(false);
const distilling = ref(false);

const form = reactive({ platform: "", account_name: "" });

// 参考文章子对话框
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
  try {
    const { data } = await api.getReferenceArticles(accountId);
    refArticles.value = data;
  } catch { refArticles.value = []; }
}

function openCreate() {
  editingAccount.value = null;
  form.platform = "";
  form.account_name = "";
  refArticles.value = [];
  activeTab.value = "basic";
  detailVisible.value = true;
}

function openDetail(row: Account) {
  editingAccount.value = row;
  form.platform = row.platform;
  form.account_name = row.account_name;
  loadRefArticles(row.id);
  activeTab.value = "basic";
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
    detailVisible.value = false;
    await loadAccounts();
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || "操作失败");
  } finally { saving.value = false; }
}

async function handleDelete(row: Account) {
  try {
    await ElMessageBox.confirm(`确定删除「${row.account_name}」？`, "确认", { type: "warning" });
    await api.deleteAccount(row.id);
    ElMessage.success("已删除");
    await loadAccounts();
  } catch { /* cancelled */ }
}

// 参考文章操作
function openAddArticle() {
  editingArticleId.value = null;
  articleForm.title = "";
  articleForm.content = "";
  articleForm.source_url = "";
  articleForm.is_benchmark = false;
  articleDialogVisible.value = true;
}

function openEditArticle(row: ReferenceArticle) {
  editingArticleId.value = row.id;
  articleForm.title = row.title;
  articleForm.content = row.content;
  articleForm.source_url = row.source_url || "";
  articleForm.is_benchmark = !!row.is_benchmark;
  articleDialogVisible.value = true;
}

async function saveArticle() {
  if (!editingAccount.value?.id) return;
  savingArticle.value = true;
  try {
    if (editingArticleId.value) {
      await api.updateReferenceArticle(editingAccount.value.id, editingArticleId.value, {
        ...articleForm, account_id: editingAccount.value.id,
      });
      ElMessage.success("已保存");
    } else {
      await api.createReferenceArticle(editingAccount.value.id, { ...articleForm });
      ElMessage.success("已添加");
    }
    articleDialogVisible.value = false;
    await loadRefArticles(editingAccount.value.id);
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || "操作失败");
  } finally { savingArticle.value = false; }
}

async function handleDeleteArticle(row: ReferenceArticle) {
  if (!editingAccount.value?.id) return;
  try {
    await ElMessageBox.confirm("确定删除此参考文章？", "确认", { type: "warning" });
    await api.deleteReferenceArticle(editingAccount.value.id, row.id);
    ElMessage.success("已删除");
    await loadRefArticles(editingAccount.value.id);
  } catch { /* cancelled */ }
}

// 蒸馏
async function triggerDistill() {
  if (!editingAccount.value?.id) return;
  distilling.value = true;
  try {
    const { data } = await api.triggerDistill(editingAccount.value.id);
    ElMessage.success("蒸馏任务已提交，请稍后刷新查看");
    // 刷新账号信息
    await loadAccounts();
    const updated = accounts.value.find(a => a.id === editingAccount.value?.id);
    if (updated) editingAccount.value = updated;
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || "蒸馏失败");
  } finally { distilling.value = false; }
}

onMounted(loadAccounts);
</script>

<style scoped>
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
</style>
