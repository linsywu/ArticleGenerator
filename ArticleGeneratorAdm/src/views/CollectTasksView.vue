<template>
  <div class="collect-tasks-view">
    <PageHeader title="采集任务" subtitle="管理公众号内容采集任务" />

    <div class="toolbar">
      <div class="toolbar-left">
        <el-select
          v-model="filterStatus"
          placeholder="状态筛选"
          clearable
          style="width: 130px"
          @change="fetchCollectTasks"
        >
          <el-option label="空闲" value="idle" />
          <el-option label="运行中" value="running" />
          <el-option label="已暂停" value="paused" />
          <el-option label="异常" value="error" />
        </el-select>
      </div>
      <el-button type="primary" @click="openCreateDialog">+ 新增采集任务</el-button>
    </div>

    <el-table :data="collectTasks" v-loading="loading" style="width: 100%">
      <el-table-column prop="name" label="任务名称" min-width="160">
        <template #default="{ row }">
          <span style="font-weight: 600;">{{ row.name }}</span>
        </template>
      </el-table-column>
      <el-table-column label="采集模式" width="120" align="center">
        <template #default="{ row }">
          <el-tag size="small">{{ collectModeLabel(row.collect_mode) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="调度类型" width="120" align="center">
        <template #default="{ row }">
          <el-tag size="small" type="info">{{ scheduleTypeLabel(row.schedule_type) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="状态" width="100" align="center">
        <template #default="{ row }">
          <el-tag :type="statusType(row.status)" size="small">
            {{ statusLabel(row.status) }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="created_at" label="创建时间" width="160">
        <template #default="{ row }">
          {{ formatTime(row.created_at) }}
        </template>
      </el-table-column>
      <el-table-column label="操作" width="320">
        <template #default="{ row }">
          <el-button size="small" text type="primary" @click="handleExecute(row.id)" :disabled="row.status === 'running'">
            执行
          </el-button>
          <el-button
            size="small"
            text
            type="warning"
            @click="handlePause(row.id)"
            :disabled="row.status !== 'running'"
          >
            暂停
          </el-button>
          <el-button
            size="small"
            text
            type="success"
            @click="handleResume(row.id)"
            :disabled="row.status !== 'paused'"
          >
            恢复
          </el-button>
          <el-button size="small" text @click="openEditDialog(row)">编辑</el-button>
          <el-popconfirm title="确认删除此采集任务？" @confirm="handleDelete(row.id)">
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
      :title="editingTask ? '编辑采集任务' : '新增采集任务'"
      width="600px"
    >
      <el-form :model="form" label-position="top">
        <el-form-item label="任务名称" required>
          <el-input v-model="form.name" placeholder="如：每日热点采集" />
        </el-form-item>
        <el-form-item label="关联凭证" required>
          <el-select v-model="form.credential_id" placeholder="选择凭证" style="width: 100%">
            <el-option
              v-for="cred in credentials"
              :key="cred.id"
              :label="cred.name"
              :value="cred.id"
            />
          </el-select>
        </el-form-item>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="采集模式">
              <el-select v-model="form.collect_mode" style="width: 100%">
                <el-option label="增量采集" value="incremental" />
                <el-option label="全量采集" value="full" />
                <el-option label="按日期范围" value="daterange" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="调度类型">
              <el-select v-model="form.schedule_type" style="width: 100%" @change="onScheduleTypeChange">
                <el-option label="手动" value="manual" />
                <el-option label="定时 (Cron)" value="cron" />
                <el-option label="间隔执行" value="interval" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>

        <template v-if="form.schedule_type === 'cron'">
          <el-form-item label="Cron 表达式">
            <el-input v-model="form.cron" placeholder="如：0 9 * * *" />
          </el-form-item>
        </template>
        <template v-if="form.schedule_type === 'interval'">
          <el-form-item label="间隔时间（小时）">
            <el-input-number v-model="form.interval_hours" :min="1" :max="168" style="width: 100%" />
          </el-form-item>
        </template>

        <el-row :gutter="16" v-if="form.collect_mode === 'daterange'">
          <el-col :span="12">
            <el-form-item label="开始日期">
              <el-date-picker v-model="form.date_start" type="date" placeholder="选择日期" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="结束日期">
              <el-date-picker v-model="form.date_end" type="date" placeholder="选择日期" style="width: 100%" />
            </el-form-item>
          </el-col>
        </el-row>

        <el-form-item label="赛道 ID (JSON 数组)">
          <el-input v-model="form.track_ids" placeholder='[1, 2, 3]' />
        </el-form-item>
        <el-form-item label="公众号 ID (JSON 数组)">
          <el-input v-model="form.account_ids" placeholder='[1, 2, 3]' />
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
import collectTasksApi from "@/api/modules/collectTasks";
import credentialsApi from "@/api/modules/credentials";
import type { CollectTask, MpCredential } from "@/api/types";
import PageHeader from "@/components/PageHeader.vue";

const collectTasks = ref<CollectTask[]>([]);
const credentials = ref<MpCredential[]>([]);
const loading = ref(false);
const saving = ref(false);

const filterStatus = ref<string | undefined>(undefined);

const dialogVisible = ref(false);
const editingTask = ref<CollectTask | null>(null);
const form = ref({
  name: "",
  credential_id: null as number | null,
  track_ids: "",
  account_ids: "",
  collect_mode: "incremental",
  date_start: null as string | null,
  date_end: null as string | null,
  schedule_type: "manual",
  cron: "",
  interval_hours: null as number | null,
});

function statusType(status: string): string {
  const map: Record<string, string> = {
    idle: "info",
    running: "primary",
    paused: "warning",
    error: "danger",
  };
  return map[status] || "info";
}

function statusLabel(status: string): string {
  const map: Record<string, string> = {
    idle: "空闲",
    running: "运行中",
    paused: "已暂停",
    error: "异常",
  };
  return map[status] || status;
}

function collectModeLabel(mode: string): string {
  const map: Record<string, string> = {
    incremental: "增量采集",
    full: "全量采集",
    daterange: "按日期范围",
  };
  return map[mode] || mode;
}

function scheduleTypeLabel(type: string): string {
  const map: Record<string, string> = {
    manual: "手动",
    cron: "定时",
    interval: "间隔执行",
  };
  return map[type] || type;
}

function formatTime(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleDateString("zh-CN") + " " + d.toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit" });
}

function onScheduleTypeChange() {
  if (form.value.schedule_type !== "cron") form.value.cron = "";
  if (form.value.schedule_type !== "interval") form.value.interval_hours = null;
}

function openCreateDialog() {
  editingTask.value = null;
  form.value = {
    name: "",
    credential_id: null,
    track_ids: "",
    account_ids: "",
    collect_mode: "incremental",
    date_start: null,
    date_end: null,
    schedule_type: "manual",
    cron: "",
    interval_hours: null,
  };
  dialogVisible.value = true;
}

function openEditDialog(row: CollectTask) {
  editingTask.value = row;
  form.value = {
    name: row.name,
    credential_id: row.credential_id,
    track_ids: row.track_ids || "",
    account_ids: row.account_ids || "",
    collect_mode: row.collect_mode,
    date_start: row.date_start || null,
    date_end: row.date_end || null,
    schedule_type: row.schedule_type,
    cron: row.cron || "",
    interval_hours: row.interval_hours || null,
  };
  dialogVisible.value = true;
}

async function handleSave() {
  if (!form.value.name.trim()) {
    ElMessage.warning("请输入任务名称");
    return;
  }
  if (!form.value.credential_id) {
    ElMessage.warning("请选择关联凭证");
    return;
  }
  saving.value = true;
  try {
    const payload: Record<string, any> = {
      name: form.value.name,
      credential_id: form.value.credential_id,
      collect_mode: form.value.collect_mode,
      schedule_type: form.value.schedule_type,
      track_ids: form.value.track_ids || undefined,
      account_ids: form.value.account_ids || undefined,
    };
    if (form.value.date_start) payload.date_start = form.value.date_start;
    if (form.value.date_end) payload.date_end = form.value.date_end;
    if (form.value.schedule_type === "cron") payload.cron = form.value.cron;
    if (form.value.schedule_type === "interval") payload.interval_hours = form.value.interval_hours;

    if (editingTask.value) {
      await collectTasksApi.updateCollectTask(editingTask.value.id, payload as any);
      ElMessage.success("采集任务已更新");
    } else {
      await collectTasksApi.createCollectTask(payload as any);
      ElMessage.success("采集任务已创建");
    }
    dialogVisible.value = false;
    await fetchCollectTasks();
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || "操作失败");
  } finally {
    saving.value = false;
  }
}

async function handleExecute(id: number) {
  try {
    await collectTasksApi.executeTask(id);
    ElMessage.info("功能开发中");
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || "操作失败");
  }
}

async function handlePause(id: number) {
  try {
    await collectTasksApi.pauseTask(id);
    ElMessage.success("任务已暂停");
    await fetchCollectTasks();
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || "操作失败");
  }
}

async function handleResume(id: number) {
  try {
    await collectTasksApi.resumeTask(id);
    ElMessage.success("任务已恢复");
    await fetchCollectTasks();
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || "操作失败");
  }
}

async function handleDelete(id: number) {
  try {
    await collectTasksApi.deleteCollectTask(id);
    ElMessage.success("采集任务已删除");
    await fetchCollectTasks();
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || "操作失败");
  }
}

async function fetchCollectTasks() {
  loading.value = true;
  try {
    const params: Record<string, unknown> = {};
    if (filterStatus.value) params.status = filterStatus.value;
    const { data } = await collectTasksApi.fetchCollectTasks(params);
    collectTasks.value = data as any;
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || "获取列表失败");
  } finally {
    loading.value = false;
  }
}

async function fetchCredentials() {
  try {
    const { data } = await credentialsApi.fetchCredentials();
    credentials.value = data as any;
  } catch {
    // credentials not required for view rendering
  }
}

onMounted(() => {
  fetchCollectTasks();
  fetchCredentials();
});
</script>

<style scoped>
.collect-tasks-view {
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
}
</style>
