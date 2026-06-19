<template>
  <div class="credentials-view">
    <PageHeader title="采集凭证" subtitle="管理微信公众号后台采集凭证" />

    <div class="toolbar">
      <el-button type="primary" @click="openCreateDialog">+ 新增凭证</el-button>
    </div>

    <div class="credential-grid" v-loading="loading">
      <div v-for="cred in credentials" :key="cred.id" class="credential-card">
        <div class="card-header">
          <span class="card-name">{{ cred.name }}</span>
          <el-tag :type="statusType(cred.status)" size="small">
            {{ statusLabel(cred.status) }}
          </el-tag>
        </div>
        <div class="card-body">
          <div class="card-field">
            <span class="field-label">Token</span>
            <span class="field-value">{{ cred.token }}</span>
          </div>
          <div class="card-field">
            <span class="field-label">Cookie</span>
            <span class="field-value cookie-value">{{ cred.cookie }}</span>
          </div>
          <div class="card-field">
            <span class="field-label">最后检测</span>
            <span class="field-value">{{ cred.check_time ? formatTime(cred.check_time) : '未检测' }}</span>
          </div>
          <div class="card-field">
            <span class="field-label">创建时间</span>
            <span class="field-value">{{ formatTime(cred.created_at) }}</span>
          </div>
        </div>
        <div class="card-actions">
          <el-button size="small" text type="primary" @click="handleCheck(cred.id)">检测</el-button>
          <el-button size="small" text @click="openEditDialog(cred)">编辑</el-button>
          <el-popconfirm title="确认删除此凭证？" @confirm="handleDelete(cred.id)">
            <template #reference>
              <el-button size="small" text type="danger">删除</el-button>
            </template>
          </el-popconfirm>
        </div>
      </div>

      <div v-if="credentials.length === 0 && !loading" class="empty-state">
        暂无凭证，点击上方按钮新增
      </div>
    </div>

    <!-- Add / Edit Dialog -->
    <el-dialog
      v-model="dialogVisible"
      :title="editingCredential ? '编辑凭证' : '新增凭证'"
      width="560px"
    >
      <el-form :model="form" label-position="top">
        <el-form-item label="凭证名称" required>
          <el-input v-model="form.name" placeholder="如：公众号主账号" />
        </el-form-item>
        <el-form-item label="Token" required>
          <el-input v-model="form.token" type="textarea" :rows="3" placeholder="微信公众号后台 token" />
        </el-form-item>
        <el-form-item label="Cookie" required>
          <el-input v-model="form.cookie" type="textarea" :rows="5" placeholder="微信公众号后台 cookie" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="handleSave">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from "vue";
import { ElMessage } from "element-plus";
import credentialsApi from "@/api/modules/credentials";
import type { MpCredential } from "@/api/types";
import PageHeader from "@/components/PageHeader.vue";

const credentials = ref<MpCredential[]>([]);
const loading = ref(false);
const saving = ref(false);

const dialogVisible = ref(false);
const editingCredential = ref<MpCredential | null>(null);
const form = ref({
  name: "",
  token: "",
  cookie: "",
});

function statusType(status: string): "success" | "warning" | "danger" | "info" {
  const map: Record<string, "success" | "warning" | "danger" | "info"> = {
    normal: "success",
    expiring_soon: "warning",
    expired: "danger",
    error: "info",
  };
  return map[status] || "info";
}

function statusLabel(status: string): string {
  const map: Record<string, string> = {
    normal: "正常",
    expiring_soon: "即将过期",
    expired: "已过期",
    error: "异常",
  };
  return map[status] || status;
}

function formatTime(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleDateString("zh-CN") + " " + d.toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit" });
}

function openCreateDialog() {
  editingCredential.value = null;
  form.value = { name: "", token: "", cookie: "" };
  dialogVisible.value = true;
}

function openEditDialog(row: MpCredential) {
  editingCredential.value = row;
  form.value = {
    name: row.name,
    token: row.token,
    cookie: row.cookie,
  };
  dialogVisible.value = true;
}

async function handleSave() {
  if (!form.value.name.trim()) {
    ElMessage.warning("请输入凭证名称");
    return;
  }
  if (!form.value.token.trim()) {
    ElMessage.warning("请输入 Token");
    return;
  }
  if (!form.value.cookie.trim()) {
    ElMessage.warning("请输入 Cookie");
    return;
  }
  saving.value = true;
  try {
    if (editingCredential.value) {
      await credentialsApi.updateCredential(editingCredential.value.id, form.value);
      ElMessage.success("凭证已更新");
    } else {
      await credentialsApi.createCredential(form.value);
      ElMessage.success("凭证已创建");
    }
    dialogVisible.value = false;
    await fetchCredentials();
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || "操作失败");
  } finally {
    saving.value = false;
  }
}

async function handleCheck(id: number) {
  try {
    await credentialsApi.checkCredential(id);
    ElMessage.info("功能开发中");
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || "操作失败");
  }
}

async function handleDelete(id: number) {
  try {
    await credentialsApi.deleteCredential(id);
    ElMessage.success("凭证已删除");
    await fetchCredentials();
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || "操作失败");
  }
}

async function fetchCredentials() {
  loading.value = true;
  try {
    const { data } = await credentialsApi.fetchCredentials();
    credentials.value = data as any;
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || "获取列表失败");
  } finally {
    loading.value = false;
  }
}

onMounted(fetchCredentials);
</script>

<style scoped>
.credentials-view {
  max-width: 960px;
  margin: 0 auto;
}
.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}
.credential-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(380px, 1fr));
  gap: 16px;
}
.credential-card {
  background: var(--ink-mid);
  border: 1px solid var(--ink-border);
  border-radius: var(--radius-lg);
  overflow: hidden;
  transition: box-shadow 0.2s ease;
}
.credential-card:hover {
  box-shadow: var(--shadow-elevated);
}
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 14px 16px;
  border-bottom: 1px solid var(--ink-border);
}
.card-name {
  font-weight: 600;
  font-size: 15px;
  color: var(--text-on-dark);
}
.card-body {
  padding: 12px 16px;
}
.card-field {
  display: flex;
  margin-bottom: 6px;
  font-size: 13px;
}
.field-label {
  width: 80px;
  color: var(--text-dim);
  flex-shrink: 0;
}
.field-value {
  color: var(--text-muted);
  word-break: break-all;
}
.cookie-value {
  font-family: monospace;
  font-size: 12px;
}
.card-actions {
  display: flex;
  gap: 4px;
  padding: 8px 16px;
  border-top: 1px solid var(--ink-border);
  background: rgba(0,0,0,0.1);
}
.empty-state {
  grid-column: 1 / -1;
  text-align: center;
  padding: 60px 20px;
  color: var(--text-dim);
  font-size: 14px;
}
</style>
