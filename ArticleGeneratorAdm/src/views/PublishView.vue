<template>
  <div class="page">
    <PageHeader title="文章发布" subtitle="评审通过的终稿，复制全文发布到各平台，标记发布状态" />

    <el-empty v-if="!loading && list.length === 0" description="暂无待发布文章" />
    <el-table v-else :data="list" v-loading="loading" style="width: 100%">
      <el-table-column prop="id" label="ID" width="70" />
      <el-table-column label="文章标题" min-width="200">
        <template #default="{ row }">{{ row.title || row.hotspot?.title || "-" }}</template>
      </el-table-column>
      <el-table-column label="账号" width="120">
        <template #default="{ row }">{{ row.account?.account_name || "-" }}</template>
      </el-table-column>
      <el-table-column label="时间" width="180">
        <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
      </el-table-column>
      <el-table-column label="操作" width="280" fixed="right">
        <template #default="{ row }">
          <el-button size="small" @click="previewArticle(row)">预览</el-button>
          <el-button size="small" @click="editArticle(row)">编辑</el-button>
          <el-button size="small" type="primary" @click="copyContent(row)">复制全文</el-button>
          <el-button size="small" type="success" @click="markPublished(row)">标记已发布</el-button>
        </template>
      </el-table-column>
    </el-table>

    <ArticleEditorDialog
      v-model="dialogVisible"
      :article="currentArticle"
      :editable="isEditMode"
      :initial-edit="isEditMode"
      :dialog-title="isEditMode ? '编辑文章' : '文章预览'"
      @saved="onArticleSaved"
    >
      <template #footer>
        <template v-if="isEditMode">
          <!-- Edit mode: use internal save/cancel — just a placeholder for clarity -->
        </template>
        <template v-else>
          <el-button @click="dialogVisible = false">关闭</el-button>
          <el-button type="primary" @click="copyFromPreview">复制全文</el-button>
        </template>
      </template>
    </ArticleEditorDialog>

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
import { api, type Article } from "@/api/client";
import { formatDateTime } from "@/utils/format";
import PageHeader from "@/components/PageHeader.vue";
import ArticleEditorDialog from "@/components/ArticleEditorDialog.vue";

const list = ref<Article[]>([]);
const loading = ref(false);
const page = ref(1);
const pageSize = ref(20);
const total = ref(0);
const dialogVisible = ref(false);
const currentArticle = ref<Article | null>(null);
const isEditMode = ref(false);

function onArticleSaved() {
  load();
}

async function load() {
  loading.value = true;
  try {
    const res = await api.getArticles({ status: "approved", page: page.value, page_size: pageSize.value });
    const payload = res.data as { data: Article[]; total: number };
    list.value = payload.data;
    total.value = payload.total;
  } catch (e) {
    ElMessage.error("加载失败");
  } finally {
    loading.value = false;
  }
}

function previewArticle(row: Article) {
  currentArticle.value = row;
  isEditMode.value = false;
  dialogVisible.value = true;
}

function editArticle(row: Article) {
  currentArticle.value = row;
  isEditMode.value = true;
  dialogVisible.value = true;
}

async function copyFromPreview() {
  if (!currentArticle.value) return;
  await copyContent(currentArticle.value);
  dialogVisible.value = false;
}

async function copyContent(row: Article) {
  try {
    await navigator.clipboard.writeText(row.content);
    ElMessage.success("已复制到剪贴板");
  } catch (e) {
    ElMessage.error("复制失败，请手动选择复制");
  }
}

async function markPublished(row: Article) {
  try {
    await api.updateArticleStatus(row.id, "published");
    ElMessage.success("已标记为已发布");
    load();
  } catch (e) {
    ElMessage.error("操作失败");
  }
}

onMounted(load);
</script>

<style scoped>
.page { padding: 0; }
.el-pagination { margin-top: 16px; }
</style>
