<template>
  <div class="materials-view">
    <PageHeader title="素材中心" subtitle="浏览和管理采集的文章素材" />

    <div class="toolbar">
      <div class="filters">
        <el-select v-model="filterAccountId" placeholder="全部公众号" clearable style="width: 180px;">
          <el-option v-for="acc in accounts" :key="acc.id" :label="acc.name" :value="acc.id" />
        </el-select>
        <el-input v-model="searchText" placeholder="搜索标题..." style="width: 220px;" clearable />
      </div>
    </div>

    <el-table :data="materials" v-loading="loading" @row-click="openDetail" style="width: 100%; cursor: pointer;">
      <el-table-column prop="title" label="标题" min-width="280" show-overflow-tooltip />
      <el-table-column label="公众号" width="140">
        <template #default="{ row }">{{ row.account?.name || '-' }}</template>
      </el-table-column>
      <el-table-column prop="word_count" label="字数" width="80" align="center" />
      <el-table-column label="发布时间" width="110">
        <template #default="{ row }">{{ row.published_at?.slice(0, 10) || '-' }}</template>
      </el-table-column>
      <el-table-column label="采集时间" width="110">
        <template #default="{ row }">{{ row.collected_at?.slice(0, 10) || '-' }}</template>
      </el-table-column>
      <el-table-column label="操作" width="160">
        <template #default="{ row }">
          <el-button size="small" text type="primary" @click.stop="openDetail(row)">查看</el-button>
          <el-button size="small" text style="color: #7b1fa2;" @click.stop="onCreateDirection(row)">💡 创作方向</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-pagination
      v-model:current-page="page"
      :page-size="pageSize"
      :total="total"
      layout="prev, pager, next"
      style="margin-top: 16px; justify-content: center;"
      @current-change="fetchMaterials"
    />

    <!-- Detail Drawer -->
    <el-drawer v-model="drawerVisible" title="文章详情" size="60%">
      <template v-if="currentMaterial">
        <h2 style="margin-bottom: 8px;">{{ currentMaterial.title }}</h2>
        <p style="color: #888; margin-bottom: 16px;">
          {{ currentMaterial.account?.name }} · {{ currentMaterial.author || '未知作者' }} · {{ currentMaterial.word_count }}字
        </p>
        <el-tabs v-model="activeTab">
          <el-tab-pane label="原文 (HTML)" name="html">
            <div class="html-preview" v-html="currentMaterial.raw_html || '(无内容)'" />
          </el-tab-pane>
          <el-tab-pane label="Markdown (清洗后)" name="markdown" @click="loadMarkdown">
            <pre class="markdown-preview" v-if="markdownContent">{{ markdownContent }}</pre>
            <div v-else-if="markdownLoading" style="text-align:center; padding:40px; color:#888;">正在解析...</div>
            <div v-else style="text-align:center; padding:40px; color:#888;">点击加载 Markdown 内容</div>
          </el-tab-pane>
        </el-tabs>
      </template>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch } from "vue";
import { ElMessage } from "element-plus";
import materialsApi from "@/api/modules/materials";
import mpAccountsApi from "@/api/modules/mpAccounts";
import type { MpMaterial, MpAccount } from "@/api/types";
import PageHeader from "@/components/PageHeader.vue";

const materials = ref<MpMaterial[]>([]);
const accounts = ref<MpAccount[]>([]);
const loading = ref(false);
const searchText = ref("");
const filterAccountId = ref<number | undefined>();
const page = ref(1);
const pageSize = ref(20);
const total = ref(0);

const drawerVisible = ref(false);
const currentMaterial = ref<any>(null);
const activeTab = ref("html");
const markdownContent = ref("");
const markdownLoading = ref(false);

let searchTimer: any = null;

async function fetchMaterials() {
  loading.value = true;
  try {
    const params: any = { page: page.value, page_size: pageSize.value };
    if (filterAccountId.value) params.account_id = filterAccountId.value;
    if (searchText.value) params.search = searchText.value;
    const { data } = await materialsApi.fetchMaterials(params);
    materials.value = (data as any).data || [];
    total.value = (data as any).total || 0;
  } finally {
    loading.value = false;
  }
}

async function fetchAccounts() {
  try {
    const { data } = await mpAccountsApi.fetchMpAccounts();
    accounts.value = data as any;
  } catch (_) {}
}

async function openDetail(row: MpMaterial) {
  try {
    const { data } = await materialsApi.getMaterial(row.id);
    currentMaterial.value = data;
    activeTab.value = "html";
    markdownContent.value = "";
    drawerVisible.value = true;
  } catch (e: any) {
    ElMessage.error("加载素材详情失败");
  }
}

async function loadMarkdown() {
  if (!currentMaterial.value || markdownContent.value || markdownLoading.value) return;
  markdownLoading.value = true;
  try {
    const { data } = await materialsApi.parseMaterial(currentMaterial.value.id);
    markdownContent.value = (data as any).content_markdown || "";
  } catch (_) {
    markdownContent.value = "解析失败";
  } finally {
    markdownLoading.value = false;
  }
}

function onCreateDirection(row: MpMaterial) {
  ElMessage.info("创作方向功能将在后续版本中开放");
}

watch(searchText, () => {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(() => { page.value = 1; fetchMaterials(); }, 300);
});

watch(filterAccountId, () => { page.value = 1; fetchMaterials(); });

onMounted(() => {
  fetchAccounts();
  fetchMaterials();
});
</script>

<style scoped>
.materials-view { max-width: 1100px; margin: 0 auto; }
.toolbar { margin-bottom: 16px; }
.filters { display: flex; gap: 12px; }
.html-preview { max-height: 70vh; overflow-y: auto; font-size: 14px; line-height: 1.7; }
.html-preview :deep(img) { max-width: 100%; }
.markdown-preview { white-space: pre-wrap; font-size: 14px; line-height: 1.8; max-height: 70vh; overflow-y: auto; background: #f9f9f9; padding: 20px; border-radius: 8px; }
</style>
