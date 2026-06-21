<template>
  <div class="collect-logs-view">
    <PageHeader title="采集日志" subtitle="查看采集任务的执行记录" />

    <div class="toolbar">
      <div class="filters">
        <el-select v-model="filterTaskId" placeholder="全部任务" clearable filterable style="width: 220px;">
          <el-option v-for="t in tasks" :key="t.id" :label="t.name" :value="t.id" />
        </el-select>
      </div>
    </div>

    <el-table :data="logs" v-loading="loading" style="width: 100%; cursor: pointer;" @row-click="openLogDetail">
      <template #empty>暂无采集日志</template>
      <el-table-column prop="task_name" label="任务名称" min-width="180" />
      <el-table-column label="公众号" width="140">
        <template #default="{ row }">{{ row.account?.name || '-' }}</template>
      </el-table-column>
      <el-table-column label="开始时间" width="160">
        <template #default="{ row }">{{ row.start_time?.replace('T',' ').slice(0,19) || '-' }}</template>
      </el-table-column>
      <el-table-column label="结束时间" width="160">
        <template #default="{ row }">{{ row.end_time?.replace('T',' ').slice(0,19) || '-' }}</template>
      </el-table-column>
      <el-table-column prop="success_count" label="成功" width="70" align="center" />
      <el-table-column prop="fail_count" label="失败" width="70" align="center" />
      <el-table-column prop="total_count" label="总计" width="70" align="center" />
      <el-table-column label="错误信息" min-width="160">
        <template #default="{ row }">
          <el-tooltip v-if="row.error_message" :content="row.error_message" placement="top">
            <span style="color:#f56c6c; cursor:pointer;">{{ row.error_message.slice(0,50) }}...</span>
          </el-tooltip>
          <span v-else style="color:#999;">-</span>
        </template>
      </el-table-column>
    </el-table>

    <el-pagination
      v-model:current-page="page" :page-size="pageSize" :total="total"
      layout="prev, pager, next" style="margin-top:16px; justify-content:center;"
      @current-change="fetchLogs"
    />

    <!-- Log Detail Drawer -->
    <el-drawer v-model="drawerVisible" title="日志详情" size="45%">
      <template v-if="currentLog">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="任务">{{ currentLog.task_name }}</el-descriptions-item>
          <el-descriptions-item label="公众号">{{ currentLog.account?.name || '-' }}</el-descriptions-item>
          <el-descriptions-item label="开始时间">{{ currentLog.start_time?.replace('T',' ').slice(0,19) || '-' }}</el-descriptions-item>
          <el-descriptions-item label="结束时间">{{ currentLog.end_time?.replace('T',' ').slice(0,19) || '-' }}</el-descriptions-item>
          <el-descriptions-item label="成功">{{ currentLog.success_count }}</el-descriptions-item>
          <el-descriptions-item label="失败">{{ currentLog.fail_count }}</el-descriptions-item>
          <el-descriptions-item label="总计">{{ currentLog.total_count }}</el-descriptions-item>
          <el-descriptions-item label="错误信息" :span="2">{{ currentLog.error_message || '无' }}</el-descriptions-item>
        </el-descriptions>

        <div v-if="currentLog.progress?.length" style="margin-top:20px;">
          <h4>执行时间线</h4>
          <el-timeline style="margin-top:12px;">
            <el-timeline-item
              v-for="(item, idx) in currentLog.progress"
              :key="idx"
              :timestamp="item.time?.replace('T',' ').slice(0,19) || ''"
              size="small"
            >
              {{ item.detail || item.step }}
            </el-timeline-item>
          </el-timeline>
        </div>

        <div v-if="currentLog.siblings?.length" style="margin-top:20px;">
          <h4>同批次日志</h4>
          <el-table :data="currentLog.siblings" size="small" style="margin-top:8px;">
            <el-table-column label="公众号" width="120">
              <template #default="{ row }">{{ row.account?.name || row.id }}</template>
            </el-table-column>
            <el-table-column prop="success_count" label="成功" width="80" />
            <el-table-column prop="fail_count" label="失败" width="80" />
          </el-table>
        </div>
      </template>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch } from "vue";
import { useRoute } from "vue-router";
import collectLogsApi from "@/api/modules/collectLogs";
import collectTasksApi from "@/api/modules/collectTasks";
import type { CollectLog, CollectTask } from "@/api/types";
import PageHeader from "@/components/PageHeader.vue";

const logs = ref<CollectLog[]>([]);
const tasks = ref<CollectTask[]>([]);
const loading = ref(false);
const filterTaskId = ref<number | undefined>();
const page = ref(1);
const pageSize = ref(20);
const total = ref(0);

const route = useRoute();

async function fetchLogs() {
  loading.value = true;
  try {
    const params: Record<string, unknown> = { page: page.value, page_size: pageSize.value };
    if (filterTaskId.value) params.task_id = filterTaskId.value;
    const { data } = await collectLogsApi.fetchCollectLogs(params);
    logs.value = data.data;
    total.value = data.total;
  } finally {
    loading.value = false;
  }
}

async function fetchTasks() {
  try {
    const { data } = await collectTasksApi.fetchCollectTasks();
    tasks.value = data;
  } catch (e) {
    console.error("Failed to load tasks for filter", e);
  }
}

watch(filterTaskId, () => { page.value = 1; fetchLogs(); });

const drawerVisible = ref(false);
const currentLog = ref<CollectLog | null>(null);

async function openLogDetail(row: CollectLog) {
  try {
    const { data } = await collectLogsApi.getCollectLog(row.id);
    currentLog.value = data as any;
    drawerVisible.value = true;
  } catch (e) {
    console.error("Failed to load log detail", e);
  }
}

onMounted(() => {
  if (route.query.task_id) {
    filterTaskId.value = Number(route.query.task_id);
  }
  fetchTasks();
  fetchLogs();
});
</script>

<style scoped>
.collect-logs-view {
  max-width: 1100px;
  margin: 0 auto;
}
.toolbar {
  margin-bottom: 16px;
}
.filters {
  display: flex;
  gap: 12px;
}
</style>
