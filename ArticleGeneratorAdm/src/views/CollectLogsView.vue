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

    <el-table :data="logs" v-loading="loading" style="width: 100%">
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
