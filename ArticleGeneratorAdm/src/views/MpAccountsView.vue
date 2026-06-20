<template>
  <div class="mp-accounts-view">
    <PageHeader title="公众号管理" subtitle="管理采集目标公众号" />

    <div class="toolbar">
      <div class="toolbar-left">
        <el-select
          v-model="filterTrackId"
          placeholder="选择赛道"
          clearable
          style="width: 150px"
          @change="fetchMpAccounts"
        >
          <el-option
            v-for="t in tracks"
            :key="t.id"
            :label="t.name"
            :value="t.id"
          />
        </el-select>
        <el-select
          v-model="filterStatus"
          placeholder="状态筛选"
          clearable
          style="width: 120px"
          @change="fetchMpAccounts"
        >
          <el-option label="启用" :value="1" />
          <el-option label="禁用" :value="0" />
        </el-select>
        <el-input
          v-model="searchText"
          placeholder="搜索公众号名称..."
          style="width: 220px"
          clearable
          @clear="fetchMpAccounts"
          @keyup.enter="fetchMpAccounts"
        />
      </div>
      <el-button type="primary" @click="openCreateDialog">+ 新增公众号</el-button>
      <el-button @click="openImportDialog">导入公众号</el-button>
    </div>

    <el-table :data="mpAccounts" v-loading="loading" style="width: 100%">
      <el-table-column label="头像" width="60" align="center">
        <template #default="{ row }">
          <el-avatar shape="square" size="small">{{ row.name.charAt(0) }}</el-avatar>
        </template>
      </el-table-column>
      <el-table-column prop="name" label="名称" min-width="160">
        <template #default="{ row }">
          <span style="font-weight: 600;">{{ row.name }}</span>
          <span v-if="row.alias" style="color: #999; margin-left: 6px; font-size: 12px;">({{ row.alias }})</span>
        </template>
      </el-table-column>
      <el-table-column prop="alias" label="微信号" width="130" />
      <el-table-column label="赛道" min-width="160">
        <template #default="{ row }">
          <el-tag
            v-for="tid in parseTrackIds(row.track_ids)"
            :key="tid"
            size="small"
            style="margin-right: 4px; margin-bottom: 2px;"
          >
            {{ getTrackName(tid) }}
          </el-tag>
          <span v-if="!row.track_ids || parseTrackIds(row.track_ids).length === 0" style="color: #999;">未分配</span>
        </template>
      </el-table-column>
      <el-table-column prop="article_count" label="文章数" width="70" align="center" />
      <el-table-column label="最后采集时间" width="150">
        <template #default="{ row }">
          <span v-if="row.last_collect_time">{{ formatTime(row.last_collect_time) }}</span>
          <span v-else style="color: #999;">-</span>
        </template>
      </el-table-column>
      <el-table-column label="状态" width="70" align="center">
        <template #default="{ row }">
          <el-tag :type="row.status === 1 ? 'success' : 'info'" size="small">
            {{ row.status === 1 ? '启用' : '禁用' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="240">
        <template #default="{ row }">
          <el-button size="small" text @click="openDetail(row)">查看</el-button>
          <el-button size="small" text type="primary" @click="openEditDialog(row)">编辑</el-button>
          <el-button size="small" text @click="toggleStatus(row)">
            {{ row.status === 1 ? '停用' : '启用' }}
          </el-button>
          <el-popconfirm title="确认删除此公众号？" @confirm="handleDelete(row.id)">
            <template #reference>
              <el-button size="small" text type="danger">删除</el-button>
            </template>
          </el-popconfirm>
        </template>
      </el-table-column>
    </el-table>

    <!-- Add / Edit Dialog -->
    <el-dialog
      v-model="dialogVisible"
      :title="editingAccount ? '编辑公众号' : '新增公众号'"
      width="560px"
    >
      <el-form :model="form" label-position="top">
        <el-form-item label="公众号名称" required>
          <el-input v-model="form.name" placeholder="如：AI科技前沿" />
        </el-form-item>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="微信号(alias)">
              <el-input v-model="form.alias" placeholder="微信号" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="fakeid">
              <el-input v-model="form.fakeid" placeholder="fakeid" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="biz">
          <el-input v-model="form.biz" placeholder="biz 参数" />
        </el-form-item>
        <el-form-item label="头像 URL">
          <el-input v-model="form.avatar" placeholder="https://..." />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="form.description" type="textarea" :rows="3" placeholder="公众号简介..." />
        </el-form-item>
        <el-form-item label="所属赛道">
          <el-select v-model="selectedTrackIds" multiple placeholder="选择赛道" style="width: 100%;">
            <el-option v-for="t in tracks" :key="t.id" :label="t.name" :value="t.id" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="handleSave">保存</el-button>
      </template>
    </el-dialog>

    
    <!-- Detail Drawer -->
    <el-drawer v-model="detailVisible" title="公众号详情" size="600px">
      <template v-if="detailAccount">
        <div class="detail-section">
          <div class="detail-avatar">{{ detailAccount.name?.charAt(0) }}</div>
          <h2 class="detail-name">{{ detailAccount.name }}</h2>
          <p class="detail-desc">{{ detailAccount.description || '暂无简介' }}</p>
        </div>
        <el-divider />
        <el-descriptions :column="1" size="small" class="detail-descriptions">
          <el-descriptions-item label-width="80px" label="ID">{{ detailAccount.id }}</el-descriptions-item>
          <el-descriptions-item label-width="80px" label="微信号">{{ detailAccount.alias || '-' }}</el-descriptions-item>
          <el-descriptions-item label-width="80px" label="fakeid">{{ detailAccount.fakeid || '未获取' }}</el-descriptions-item>
          <el-descriptions-item label-width="80px" label="biz">{{ detailAccount.biz || '未获取' }}</el-descriptions-item>
          <el-descriptions-item label-width="80px" label="所属赛道">{{ getTrackNames(detailAccount.track_ids) }}</el-descriptions-item>
          <el-descriptions-item label-width="80px" label="文章数">{{ detailAccount.article_count }}</el-descriptions-item>
          <el-descriptions-item label-width="80px" label="最后采集时间">{{ detailAccount.last_collect_time ? formatTime(detailAccount.last_collect_time) : '从未采集' }}</el-descriptions-item>
          <el-descriptions-item label-width="80px" label="状态">
            <el-tag :type="detailAccount.status === 1 ? 'success' : 'info'" size="small">
              {{ detailAccount.status === 1 ? '启用' : '禁用' }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label-width="80px" label="创建时间">{{ formatTime(detailAccount.created_at) }}</el-descriptions-item>
          <el-descriptions-item label-width="80px" label="更新时间">{{ formatTime(detailAccount.updated_at) }}</el-descriptions-item>
        </el-descriptions>
      </template>
    </el-drawer>

<!-- Import Dialog -->
    <el-dialog v-model="importDialogVisible" title="导入公众号" width="600px">
      <el-tabs v-model="importTab">
        <el-tab-pane label="名称导入" name="name">
          <p style="color: #999; margin-bottom: 8px; font-size: 13px;">
            每行一个公众号名称
          </p>
          <el-input
            v-model="importNames"
            type="textarea"
            :rows="6"
            placeholder="AI科技前沿&#10;财经观察&#10;数码评测"
          />
          <div style="margin-top: 12px;">
            <el-button type="primary" :disabled="!importNames.trim()" @click="handleImportByName">
              开始导入
            </el-button>
          </div>
        </el-tab-pane>
        <el-tab-pane label="链接导入" name="url">
          <p style="color: #999; margin-bottom: 8px; font-size: 13px;">
            每行一个公众号链接
          </p>
          <el-input
            v-model="importUrls"
            type="textarea"
            :rows="6"
            placeholder="https://mp.weixin.qq.com/s/...&#10;https://mp.weixin.qq.com/s/..."
          />
          <div style="margin-top: 12px;">
            <el-button type="primary" :disabled="!importUrls.trim()" @click="handleImportByUrl">
              开始导入
            </el-button>
          </div>
        </el-tab-pane>
      </el-tabs>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from "vue";
import { ElMessage } from "element-plus";
import mpAccountsApi from "@/api/modules/mpAccounts";
import tracksApi from "@/api/modules/tracks";
import type { MpAccount, Track } from "@/api/types";
import PageHeader from "@/components/PageHeader.vue";
import credentialsApi from "@/api/modules/credentials";

const mpAccounts = ref<MpAccount[]>([]);
const tracks = ref<Track[]>([]);
const credentials = ref<any[]>([]);
const loading = ref(false);
const saving = ref(false);

const filterTrackId = ref<number | undefined>(undefined);
const filterStatus = ref<number | undefined>(undefined);
const searchText = ref("");

const dialogVisible = ref(false);
const editingAccount = ref<MpAccount | null>(null);
const selectedTrackIds = ref<number[]>([]);
const form = ref({
  name: "",
  alias: "",
  fakeid: "",
  biz: "",
  avatar: "",
  description: "",
  track_ids: "",
});

const importDialogVisible = ref(false);
const importTab = ref("name");
const importNames = ref("");
const importUrls = ref("");

// Detail drawer
const detailVisible = ref(false);
const detailAccount = ref<MpAccount | null>(null);

function parseTrackIds(trackIdsStr?: string): number[] {
  if (!trackIdsStr) return [];
  try {
    return JSON.parse(trackIdsStr);
  } catch {
    return [];
  }
}

function getTrackName(trackId: number): string {
  const t = tracks.value.find((t) => t.id === trackId);
  return t ? t.name : `赛道${trackId}`;
}

function formatTime(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleDateString("zh-CN") + " " + d.toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit" });
}

function openCreateDialog() {
  editingAccount.value = null;
  selectedTrackIds.value = [];
  form.value = { name: "", alias: "", fakeid: "", biz: "", avatar: "", description: "", track_ids: "" };
  dialogVisible.value = true;
}

function openDetail(row: MpAccount) {
  detailAccount.value = row;
  detailVisible.value = true;
}

function getTrackNames(trackIdsStr: string | undefined): string {
  if (!trackIdsStr) return '未分配';
  try {
    const ids = JSON.parse(trackIdsStr);
    return ids.map((id: number) => getTrackName(id)).join(', ');
  } catch { return trackIdsStr; }
}

function openEditDialog(row: MpAccount) {
  editingAccount.value = row;
  selectedTrackIds.value = parseTrackIds(row.track_ids);
  form.value = {
    name: row.name,
    alias: row.alias || "",
    fakeid: row.fakeid || "",
    biz: row.biz || "",
    avatar: row.avatar || "",
    description: row.description || "",
    track_ids: row.track_ids || "",
  };
  dialogVisible.value = true;
}

async function handleSave() {
  if (!form.value.name.trim()) {
    ElMessage.warning("请输入公众号名称");
    return;
  }
  saving.value = true;
  try {
    const payload = { ...form.value, track_ids: JSON.stringify(selectedTrackIds.value) };
    if (editingAccount.value) {
      await mpAccountsApi.updateMpAccount(editingAccount.value.id, payload);
      ElMessage.success("公众号已更新");
    } else {
      await mpAccountsApi.createMpAccount(payload);
      ElMessage.success("公众号已创建");
    }
    dialogVisible.value = false;
    await fetchMpAccounts();
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || "操作失败");
  } finally {
    saving.value = false;
  }
}

async function toggleStatus(row: MpAccount) {
  const newStatus = row.status === 1 ? 0 : 1;
  try {
    await mpAccountsApi.toggleMpAccountStatus(row.id);
    row.status = newStatus;
    ElMessage.success(newStatus === 1 ? "已启用" : "已停用");
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || "操作失败");
  }
}

async function handleDelete(id: number) {
  try {
    await mpAccountsApi.deleteMpAccount(id);
    ElMessage.success("公众号已删除");
    await fetchMpAccounts();
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || "操作失败");
  }
}

async function openImportDialog() {
  importNames.value = "";
  importUrls.value = "";
  importTab.value = "name";
  await fetchCredentials();
  importDialogVisible.value = true;
}

async function handleImportByName() {
  if (!importNames.value.trim()) { ElMessage.warning("请输入公众号名称"); return; }
  const credId = getActiveCredentialId();
  if (!credId) { ElMessage.warning("请先添加有效的采集凭证"); return; }
  try {
    const names = importNames.value.split('\n').filter(n => n.trim());
    const { data } = await mpAccountsApi.importByName({ names, credential_id: credId });
    const result = data as any;
    ElMessage.success(`导入完成: ${result.success?.length || 0} 成功, ${result.failed?.length || 0} 失败`);
    importDialogVisible.value = false;
    await fetchMpAccounts();
  } catch (e: any) { ElMessage.error(e?.response?.data?.detail || "导入失败"); }
}

async function handleImportByUrl() {
  if (!importUrls.value.trim()) { ElMessage.warning("请输入文章链接"); return; }
  const credId = getActiveCredentialId();
  if (!credId) { ElMessage.warning("请先添加有效的采集凭证"); return; }
  try {
    const urls = importUrls.value.split('\n').filter(u => u.trim());
    const { data } = await mpAccountsApi.importByUrl({ urls, credential_id: credId });
    const result = data as any;
    ElMessage.success(`导入完成: ${result.success?.length || 0} 成功, ${result.failed?.length || 0} 失败`);
    importDialogVisible.value = false;
    await fetchMpAccounts();
  } catch (e: any) { ElMessage.error(e?.response?.data?.detail || "导入失败"); }
}

async function fetchMpAccounts() {
  loading.value = true;
  try {
    const params: Record<string, unknown> = {};
    if (filterTrackId.value !== undefined && filterTrackId.value !== null) {
      params.track_id = filterTrackId.value;
    }
    if (filterStatus.value !== undefined && filterStatus.value !== null) {
      params.status = filterStatus.value;
    }
    if (searchText.value) {
      params.search = searchText.value;
    }
    const { data } = await mpAccountsApi.fetchMpAccounts(params);
    mpAccounts.value = data as any;
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || "获取列表失败");
  } finally {
    loading.value = false;
  }
}

async function fetchTracks() {
  try {
    const { data } = await tracksApi.fetchTracks();
    tracks.value = data as any;
  } catch {
    // tracks not required for basic operation
  }
}

async function fetchCredentials() {
  try {
    const { data } = await credentialsApi.fetchCredentials();
    credentials.value = (data as any) || [];
  } catch {
    // credentials not required for basic operation
  }
}

function getActiveCredentialId(): number | null {
  const normal = credentials.value.find(c => c.status === "normal");
  return normal ? normal.id : null;
}

onMounted(() => {
  fetchMpAccounts();
  fetchTracks();
  fetchCredentials();
});
</script>

<style scoped>
.mp-accounts-view {
  max-width: 1200px;
  margin: 0 auto;
}
.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  flex-wrap: wrap;
  gap: 8px;
}
.toolbar-left {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}
.detail-section { text-align: center; padding: 16px 0; }
.detail-avatar { width: 64px; height: 64px; border-radius: 50%; background: var(--amber, #c8843c); color: #fff; display: flex; align-items: center; justify-content: center; font-size: 28px; font-weight: 700; margin: 0 auto; }
.detail-name { font-size: 20px; font-weight: 700; color: var(--text-on-dark, #e0e0e0); margin: 12px 0 4px; }
.detail-desc { color: var(--text-muted, #999); margin: 0; font-size: 14px; }
.detail-descriptions :deep(.el-descriptions__label) { color: var(--text-muted, #999); }
.detail-descriptions :deep(.el-descriptions__content) { color: var(--text-on-dark, #e0e0e0); }
</style>
