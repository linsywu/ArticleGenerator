<template>
  <div class="page">
    <div class="toolbar">
      <el-input
        v-model="keyword"
        placeholder="搜索热点"
        clearable
        style="width: 200px; margin-right: 12px"
        @keyup.enter="load"
      />
      <el-select v-model="sourceFilter" placeholder="来源" clearable style="width: 120px; margin-right: 12px">
        <el-option label="全部" value="" />
        <el-option v-for="s in sourceOptions" :key="s" :label="s" :value="s" />
      </el-select>
      <el-select v-model="statusFilter" placeholder="状态" clearable style="width: 120px; margin-right: 12px">
        <el-option label="全部" value="" />
        <el-option label="未选择" value="unselected" />
        <el-option label="已选择" value="selected" />
        <el-option label="已生成" value="generated" />
      </el-select>
      <el-button type="primary" @click="load">查询</el-button>
      <el-button @click="load">刷新</el-button>
      <el-button type="warning" :loading="crawling" @click="doCrawl">拉取最新</el-button>
    </div>

    <el-empty v-if="!loading && list.length === 0" description="暂无热点">
      <template #description>
        <p>点击「拉取最新」按钮获取热点，或执行热点抓取脚本</p>
      </template>
    </el-empty>
    <el-table
      v-else
      :data="list"
      v-loading="loading"
      style="width: 100%"
    >
      <el-table-column label="标题" min-width="200">
        <template #default="{ row }">
          <el-link
            v-if="row.url"
            type="primary"
            :href="row.url"
            target="_blank"
            rel="noopener"
            class="hotspot-link"
          >
            {{ row.title }}
          </el-link>
          <span v-else>{{ row.title }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="source" label="来源" width="100" />
      <el-table-column prop="heat" label="热度" width="100" sortable />
      <el-table-column prop="status" label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="statusMap[row.status]">{{ statusText[row.status] || row.status }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="created_at" label="时间" width="180" />
    </el-table>

    <el-pagination
      v-if="total > 0"
      v-model:current-page="page"
      v-model:page-size="pageSize"
      :total="total"
      :page-sizes="[10, 20, 50]"
      layout="total, sizes, prev, pager, next"
      @current-change="load"
      @size-change="load"
    />

  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from "vue";
import { ElMessage } from "element-plus";
import { api, type Hotspot } from "@/api/client";

const list = ref<Hotspot[]>([]);
const loading = ref(false);
const keyword = ref("");
const sourceFilter = ref("");
const statusFilter = ref("");
const sourceOptions = ref<string[]>([]);
const page = ref(1);
const pageSize = ref(20);
const total = ref(0);
const crawling = ref(false);

const statusMap: Record<string, string> = {
  unselected: "info",
  selected: "warning",
  generated: "success",
};
const statusText: Record<string, string> = {
  unselected: "未选择",
  selected: "已选择",
  generated: "已生成",
};

async function load() {
  loading.value = true;
  try {
    const res = await api.getHotspots({
      keyword: keyword.value || undefined,
      source: sourceFilter.value || undefined,
      status: statusFilter.value || undefined,
      page: page.value,
      page_size: pageSize.value,
    });
    const payload = res.data as { data: Hotspot[]; total: number };
    list.value = payload.data;
    total.value = payload.total;
  } catch (e) {
    ElMessage.error("加载失败");
  } finally {
    loading.value = false;
  }
}

async function loadSources() {
  try {
    const res = await api.getHotspotSourceOptions();
    sourceOptions.value = res.data.sources || [];
  } catch {
    sourceOptions.value = [];
  }
}

async function doCrawl() {
  crawling.value = true;
  try {
    const res = await api.crawlHotspots();
    const data = res.data as { created?: number; total?: number; error?: string };
    if (data.error) {
      ElMessage.error(`抓取失败：${data.error}`);
    } else {
      ElMessage.success(`抓取完成，新增 ${data.created ?? 0} 条热点`);
      load();
      loadSources();
    }
  } catch (e) {
    ElMessage.error("抓取失败");
  } finally {
    crawling.value = false;
  }
}

onMounted(() => {
  load();
  loadSources();
});
</script>

<style scoped>
.page {
  background: #fff;
  padding: 20px;
  border-radius: 4px;
}
.toolbar {
  margin-bottom: 16px;
}
.el-pagination {
  margin-top: 16px;
}
.generate-tip {
  margin-bottom: 16px;
  color: #606266;
}
.status-banner {
  margin-bottom: 16px;
}
.empty-hint {
  font-size: 12px;
  color: #909399;
  margin-top: 8px;
}
.hotspot-link {
  display: inline-block;
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
