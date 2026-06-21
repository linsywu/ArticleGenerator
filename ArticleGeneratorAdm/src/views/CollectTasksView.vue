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
          <el-option label="已完成" value="completed" />
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
          <el-tag :type="statusType(row.status)" size="small" :class="{ 'status-running': row.status === 'running' }">
            {{ statusLabel(row.status) }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="最近结果" width="150" align="center">
        <template #default="{ row }">
          <template v-if="row.last_result">
            <span style="font-size:12px; color:#333;">成功 {{ row.last_result.success_count }} / 失败 {{ row.last_result.fail_count }}</span>
            <br>
            <span style="font-size:11px; color:#999;">{{ row.last_result.executed_at?.replace('T',' ').slice(0,16) || '' }}</span>
          </template>
          <span v-else style="color:#ccc; font-size:12px;">暂无</span>
        </template>
      </el-table-column>
      <el-table-column prop="created_at" label="创建时间" width="160">
        <template #default="{ row }">
          {{ formatTime(row.created_at) }}
        </template>
      </el-table-column>
      <el-table-column label="任务执行" width="200">
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
          
        </template>
      </el-table-column>
      <el-table-column label="操作" width="200">
        <template #default="{ row }">
          <el-button size="small" text @click="openEditDialog(row)">编辑</el-button>
          <el-button size="small" text type="info" @click.stop="viewLogs(row)">日志</el-button>
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

        <el-form-item label="采集范围（赛道 → 公众号）">
          <div class="tree-selector">
            <div v-for="track in trackTree" :key="'t'+track.id" class="tree-track">
              <el-checkbox
                :model-value="isTrackChecked(track.id)"
                :indeterminate="isTrackIndeterminate(track.id)"
                @change="onTrackToggle(track.id, $event)"
              >
                <strong>{{ track.name }}</strong>
                <span style="color: #999; font-size: 12px; margin-left: 4px;">({{ track.accounts?.length || 0 }}个公众号)</span>
              </el-checkbox>
              <div v-if="isTrackExpanded(track.id)" class="tree-accounts">
                <el-checkbox
                  v-for="acc in track.accounts"
                  :key="'a'+acc.id"
                  :model-value="selectedAccountIds.includes(acc.id)"
                  @change="onAccountToggle(acc.id, $event)"
                  style="margin-left: 28px; display: block; padding: 2px 0;"
                >
                  {{ acc.name }}
                  <span v-if="acc.alias" style="color: #bbb; font-size: 11px;">({{ acc.alias }})</span>
                </el-checkbox>
              </div>
              <div v-if="!track.accounts?.length" style="margin-left: 28px; color: #999; font-size: 12px; padding: 4px 0;">
                暂无公众号
              </div>
            </div>
            <div v-if="!trackTree.length" style="color: #999; font-size: 13px; padding: 8px 0;">
              暂无赛道数据，请先在「赛道管理」中添加赛道
            </div>
          </div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="handleSave">保存</el-button>
      </template>
    </el-dialog>

    <!-- Lifecycle Drawer -->
    <el-drawer v-model="logDrawerVisible" title="任务执行日志" size="50%" @close="stopLogPolling">
      <template v-if="logTaskId">
        <h4 style="margin-bottom:12px;">{{ logTaskName }}</h4>
        <div v-loading="logLoading">
          <el-timeline v-if="allLogProgress.length > 0">
            <el-timeline-item
              v-for="(item, idx) in allLogProgress"
              :key="idx"
              :timestamp="item.time?.replace('T',' ').slice(0,19) || ''"
              :type="item.step === 'task_complete' ? 'success' : item.step.includes('error') || item.step.includes('fail') ? 'danger' : 'primary'"
              size="small"
            >
              {{ item.detail || item.step }}
            </el-timeline-item>
          </el-timeline>
          <div v-else-if="!logLoading" style="text-align:center;padding:40px;color:#999;">
            暂无执行记录
          </div>
        </div>
      </template>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from "vue";
import { useRouter } from "vue-router";
import { ElMessage } from "element-plus";
import collectTasksApi from "@/api/modules/collectTasks";
import credentialsApi from "@/api/modules/credentials";
import tracksApi from "@/api/modules/tracks";
import mpAccountsApi from "@/api/modules/mpAccounts";
import type { CollectTask, MpCredential, Track, MpAccount, CollectLog } from "@/api/types";
import collectLogsApi from "@/api/modules/collectLogs";
import PageHeader from "@/components/PageHeader.vue";

const router = useRouter();
const collectTasks = ref<CollectTask[]>([]);
const credentials = ref<MpCredential[]>([]);
const loading = ref(false);
const saving = ref(false);

const filterStatus = ref<string | undefined>(undefined);

const dialogVisible = ref(false);
const editingTask = ref<CollectTask | null>(null);

// Tree selector state
interface TreeTrack extends Track {
  accounts: MpAccount[];
}
const trackTree = ref<TreeTrack[]>([]);
const selectedTrackIds = ref<number[]>([]);
const selectedAccountIds = ref<number[]>([]);
const allAccounts = ref<MpAccount[]>([]);

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
    completed: "success",
  };
  return map[status] || "info";
}

function statusLabel(status: string): string {
  const map: Record<string, string> = {
    idle: "空闲",
    running: "运行中",
    paused: "已暂停",
    error: "异常",
    completed: "已完成",
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

// ── Tree selector: Track → Account multi-level ──
function isTrackChecked(trackId: number): boolean {
  return selectedTrackIds.value.includes(trackId);
}
function isTrackIndeterminate(trackId: number): boolean {
  const track = trackTree.value.find(t => t.id === trackId);
  if (!track || !track.accounts?.length) return false;
  const checkedCount = track.accounts.filter(a => selectedAccountIds.value.includes(a.id)).length;
  return checkedCount > 0 && checkedCount < track.accounts.length;
}
function isTrackExpanded(trackId: number): boolean {
  return selectedTrackIds.value.includes(trackId) || isTrackIndeterminate(trackId);
}
function onTrackToggle(trackId: number, checked: boolean) {
  const track = trackTree.value.find(t => t.id === trackId);
  if (!track) return;
  if (checked) {
    if (!selectedTrackIds.value.includes(trackId)) selectedTrackIds.value.push(trackId);
    for (const acc of track.accounts || []) {
      if (!selectedAccountIds.value.includes(acc.id)) selectedAccountIds.value.push(acc.id);
    }
  } else {
    selectedTrackIds.value = selectedTrackIds.value.filter(id => id !== trackId);
    const accIds = (track.accounts || []).map(a => a.id);
    selectedAccountIds.value = selectedAccountIds.value.filter(id => !accIds.includes(id));
  }
}
function onAccountToggle(accId: number, checked: boolean) {
  if (checked) {
    if (!selectedAccountIds.value.includes(accId)) selectedAccountIds.value.push(accId);
  } else {
    selectedAccountIds.value = selectedAccountIds.value.filter(id => id !== accId);
    for (const track of trackTree.value) {
      const accIds = (track.accounts || []).map(a => a.id);
      if (!accIds.some(id => selectedAccountIds.value.includes(id))) {
        selectedTrackIds.value = selectedTrackIds.value.filter(id => id !== track.id);
      }
    }
  }
}
function parseJsonArray(raw: string | undefined | null): number[] {
  if (!raw) return [];
  try {
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

async function loadTrackTree() {
  try {
    const { data: tracks } = await tracksApi.fetchTracks();
    const { data: accounts } = await mpAccountsApi.fetchMpAccounts();
    allAccounts.value = (accounts as any) || [];
    trackTree.value = ((tracks as any) || []).map((t: Track) => ({
      ...t,
      accounts: allAccounts.value.filter((a: MpAccount) => {
        if (!a.track_ids) return false;
        try { const ids: number[] = JSON.parse(a.track_ids); return ids.includes(t.id); }
        catch { return false; }
      }),
    }));
  } catch (_) {}
}


function openCreateDialog() {
  editingTask.value = null;
  selectedTrackIds.value = [];
  selectedAccountIds.value = [];
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
  selectedTrackIds.value = parseJsonArray(row.track_ids);
  selectedAccountIds.value = parseJsonArray(row.account_ids);
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
      track_ids: selectedTrackIds.value.length > 0 ? JSON.stringify(selectedTrackIds.value) : undefined,
      account_ids: selectedAccountIds.value.length > 0 ? JSON.stringify(selectedAccountIds.value) : undefined,
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

// Polling infrastructure
const pollingTimers = new Map<number, ReturnType<typeof setInterval>>();

async function pollTask(taskId: number) {
  if (pollingTimers.has(taskId)) clearInterval(pollingTimers.get(taskId));
  const timer = setInterval(async () => {
    try {
      const { data } = await collectTasksApi.getCollectTask(taskId);
      const idx = collectTasks.value.findIndex(t => t.id === taskId);
      if (idx !== -1) collectTasks.value[idx] = data;
      if (data.status !== "running") {
        clearInterval(timer);
        pollingTimers.delete(taskId);
        await fetchCollectTasks();
      }
    } catch { /* ignore poll errors */ }
  }, 2000);
  pollingTimers.set(taskId, timer);
}

async function handleExecute(id: number) {
  try {
    await collectTasksApi.executeTask(id);
    ElMessage.success("采集任务已提交执行");
    await fetchCollectTasks();
    pollTask(id);
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

const logDrawerVisible = ref(false);
const logTaskId = ref<number | null>(null);
const logTaskName = ref("");
const logLoading = ref(false);
const allLogProgress = ref<any[]>([]);
let logPollTimer: ReturnType<typeof setInterval> | null = null;

function viewLogs(row: CollectTask) {
  logTaskId.value = row.id;
  logTaskName.value = row.name;
  logDrawerVisible.value = true;
  fetchLogEntriesWithProgress();
  startLogPolling();
}

async function fetchLogEntriesWithProgress() {
  if (!logTaskId.value) return;
  logLoading.value = true;
  try {
    const { data } = await collectLogsApi.fetchCollectLogs({ task_id: logTaskId.value, page_size: 50 });
    // Merge all progress arrays from all log entries, sorted by time
    const allSteps: any[] = [];
    for (const log of (data.data || [])) {
      if ((log as any).progress) {
        for (const step of (log as any).progress) {
          allSteps.push({ ...step, account: (log as any).account?.name });
        }
      }
    }
    allSteps.sort((a, b) => (a.time || '').localeCompare(b.time || ''));
    allLogProgress.value = allSteps;
  } finally {
    logLoading.value = false;
  }
}

function startLogPolling() {
  if (logPollTimer) clearInterval(logPollTimer);
  logPollTimer = setInterval(async () => {
    if (!logDrawerVisible.value) { stopLogPolling(); return; }
    await fetchLogEntriesWithProgress();
  }, 2000);
}

function stopLogPolling() {
  if (logPollTimer) { clearInterval(logPollTimer); logPollTimer = null; }
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
  loadTrackTree();
});

onUnmounted(() => { pollingTimers.forEach(t => clearInterval(t)); });
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
@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}
.status-running {
  animation: pulse 1.2s ease-in-out infinite;
}
</style>
