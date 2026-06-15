<template>
  <div class="page">
    <header class="page-header">
      <div>
        <h1 class="page-title">文章发布</h1>
        <p class="page-subtitle">评审通过的终稿，复制全文发布到各平台，标记发布状态</p>
      </div>
    </header>
    <el-empty v-if="!loading && list.length === 0" description="暂无待发布文章" />
    <el-table v-else :data="list" v-loading="loading" style="width: 100%">
      <el-table-column prop="id" label="ID" width="70" />
      <el-table-column label="文章标题" min-width="200">
        <template #default="{ row }">{{ row.title || row.hotspot?.title || "-" }}</template>
      </el-table-column>
      <el-table-column label="账号" width="120">
        <template #default="{ row }">{{ row.account?.account_name || "-" }}</template>
      </el-table-column>
      <el-table-column prop="created_at" label="时间" width="180" />
      <el-table-column label="操作" width="280" fixed="right">
        <template #default="{ row }">
          <el-button size="small" @click="previewArticle(row)">预览</el-button>
          <el-button size="small" @click="editArticle(row)">编辑</el-button>
          <el-button size="small" type="primary" @click="copyContent(row)">复制全文</el-button>
          <el-button size="small" type="success" @click="markPublished(row)">标记已发布</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="previewVisible" title="文章预览" width="700px">
      <div class="preview-content">{{ previewArticleContent }}</div>
      <template #footer>
        <el-button @click="previewVisible = false">关闭</el-button>
        <el-button type="primary" @click="copyFromPreview">复制全文</el-button>
      </template>
    </el-dialog>

    <!-- 编辑对话框 -->
    <el-dialog v-model="editVisible" title="编辑文章" width="800px">
      <el-input v-model="editContent" type="textarea" :rows="16" placeholder="文章内容" />
      <template #footer>
        <el-button @click="editVisible = false">取消</el-button>
        <el-button type="primary" :loading="savingEdit" @click="saveEdit">保存</el-button>
      </template>
    </el-dialog>

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

const list = ref<Article[]>([]);
const loading = ref(false);
const page = ref(1);
const pageSize = ref(20);
const total = ref(0);
const previewVisible = ref(false);
const previewArticleContent = ref("");
const previewArticleRow = ref<Article | null>(null);
const editVisible = ref(false);
const editingArticleRow = ref<Article | null>(null);
const editContent = ref("");
const savingEdit = ref(false);

function editArticle(row: Article) {
  editingArticleRow.value = row;
  editContent.value = row.content;
  editVisible.value = true;
}

async function saveEdit() {
  if (!editingArticleRow.value) return;
  savingEdit.value = true;
  try {
    await api.updateArticle(editingArticleRow.value.id, { content: editContent.value });
    editingArticleRow.value.content = editContent.value;
    ElMessage.success("已保存");
    editVisible.value = false;
    load();
  } catch {
    ElMessage.error("保存失败");
  } finally { savingEdit.value = false; }
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
  previewArticleRow.value = row;
  previewArticleContent.value = row.content;
  previewVisible.value = true;
}

async function copyFromPreview() {
  if (!previewArticleRow.value) return;
  await copyContent(previewArticleRow.value);
  previewVisible.value = false;
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
.page-header { margin-bottom: var(--space-xl); }
.page-title { font-family: var(--font-serif); font-size: 28px; font-weight: 900; color: var(--text-on-dark); letter-spacing: 1px; margin-bottom: 4px; }
.page-subtitle { font-size: 14px; color: var(--text-muted); }
.el-pagination { margin-top: 16px; }
.preview-content { white-space: pre-wrap; max-height: 400px; overflow-y: auto; line-height: 1.6; color: var(--text-on-dark); }
</style>
