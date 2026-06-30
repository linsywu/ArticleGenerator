<template>
  <div class="page">
    <PageHeader title="任务记录" subtitle="查看文章生成、微调等任务的执行记录" />

    <div class="toolbar">
      <el-select v-model="statusFilter" placeholder="任务状态" clearable style="width: 140px; margin-right: 12px">
        <el-option label="全部" value="" />
        <el-option label="生成中" value="generating" />
        <el-option label="已生成" value="success" />
        <el-option label="生成失败" value="failed" />
        <el-option label="已取消" value="cancelled" />
      </el-select>
      <el-button type="primary" @click="load">查询</el-button>
      <el-button @click="load">刷新</el-button>
    </div>

    <el-empty v-if="!loading && list.length === 0" description="暂无任务">
      <template #description>
        <p>在热点列表选择热点并批量生成后，任务将在此展示</p>
      </template>
    </el-empty>
    <el-table v-else :data="list" v-loading="loading" style="width: 100%">
      <el-table-column prop="id" label="ID" width="70" />
      <el-table-column label="文章标题" min-width="200">
        <template #default="{ row }">{{ row.title || row.hotspot?.title || "-" }}</template>
      </el-table-column>
      <el-table-column label="账号" width="120">
        <template #default="{ row }">{{ row.account?.account_name || "-" }}</template>
      </el-table-column>
      <el-table-column label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="taskStatusType[row.status]">{{ taskStatusText[row.status] || row.status }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="失败原因" min-width="150" show-overflow-tooltip>
        <template #default="{ row }">{{ row.error_message || "-" }}</template>
      </el-table-column>
      <el-table-column label="创建时间" width="180">
        <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
      </el-table-column>
      <el-table-column label="操作" width="320" fixed="right">
        <template #default="{ row }">
          <el-button
            v-if="row.status === 'pending' || row.status === 'running'"
            size="small"
            type="danger"
            @click="cancelTask(row)"
          >
            取消
          </el-button>
          <el-button
            v-if="row.status === 'success' || row.status === 'failed' || row.status === 'cancelled'"
            size="small"
            type="danger"
            @click="deleteTask(row)"
            text
          >
            删除
          </el-button>
          <template v-if="row.status === 'success' && row.article_id">
            <el-button size="small" @click="viewArticle(row)">查看文章</el-button>
            <el-button size="small" type="primary" @click="goToReview">去评审</el-button>
          </template>
        </template>
      </el-table-column>
    </el-table>

    <ArticleEditorDialog
      ref="articleEditorRef"
      v-model="articleVisible"
      :article="currentArticleData"
      :dialog-title="editingArticle ? '编辑文章' : '文章详情'"
      editable
      @saved="onArticleSaved"
    >
      <template #footer>
        <el-button @click="articleVisible = false">关闭</el-button>
        <el-button @click="articleEditorRef?.startEditing()">编辑</el-button>
        <el-button type="primary" @click="goToReview">去评审</el-button>
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
import { ElMessage, ElMessageBox } from "element-plus";
import { useRouter } from "vue-router";
import { api, type Article } from "@/api/client";
import { formatDateTime } from "@/utils/format";
import PageHeader from "@/components/PageHeader.vue";
import ArticleEditorDialog from "@/components/ArticleEditorDialog.vue";

interface TaskItem {
  id: number;
  task_id: string;
  hotspot_id: number;
  account_id: number;
  article_id?: number;
  title?: string;
  status: string;
  error_message?: string;
  created_at: string;
  hotspot?: { id: number; title: string; source: string };
  account?: { id: number; account_name: string; platform: string };
}

const list = ref<TaskItem[]>([]);
const loading = ref(false);
const statusFilter = ref("");
const page = ref(1);
const pageSize = ref(20);
const total = ref(0);
const router = useRouter();
const articleVisible = ref(false);
const editingArticle = ref(false);
const currentArticleId = ref<number | null>(null);
const currentArticleData = ref<Article | null>(null);

const articleEditorRef = ref<InstanceType<typeof ArticleEditorDialog> | null>(null);

const taskStatusType: Record<string, string> = {
  pending: "warning",
  running: "warning",
  success: "success",
  failed: "danger",
  cancelled: "info",
};
const taskStatusText: Record<string, string> = {
  pending: "生成中",
  running: "生成中",
  success: "已生成",
  failed: "生成失败",
  cancelled: "已取消",
};

function onArticleSaved() {
  load();
}

async function load() {
  loading.value = true;
  try {
    const params: Record<string, unknown> = { page: page.value, page_size: pageSize.value };
    if (statusFilter.value) params.status = statusFilter.value;
    const res = await api.getTaskList(params);
    const payload = res.data as { data: TaskItem[]; total: number };
    list.value = payload.data;
    total.value = payload.total;
  } catch (e) {
    ElMessage.error("加载失败");
  } finally {
    loading.value = false;
  }
}

async function viewArticle(row: TaskItem) {
  currentArticleId.value = row.article_id || null;
  editingArticle.value = false;
  try {
    const res = await api.getArticle(row.article_id!);
    currentArticleData.value = res.data as Article;
    articleVisible.value = true;
  } catch {
    ElMessage.error("获取文章失败");
  }
}

async function cancelTask(row: TaskItem) {
  try {
    await ElMessageBox.confirm(`确定取消任务「${row.hotspot?.title || row.task_id}」？`, "提示");
    await api.cancelTask(row.task_id);
    ElMessage.success("已取消");
    load();
  } catch (e) {
    if (e !== "cancel") ElMessage.error("取消失败");
  }
}

async function deleteTask(row: TaskItem) {
  try {
    await ElMessageBox.confirm(`确定删除任务「${row.hotspot?.title || row.task_id}」？删除后不可恢复。`, "提示");
    await api.deleteGenerationTask(row.task_id);
    ElMessage.success("已删除");
    load();
  } catch (e) {
    if (e !== "cancel") ElMessage.error("删除失败");
  }
}

function goToReview() {
  articleVisible.value = false;
  router.push("/review");
}

onMounted(load);
</script>

<style scoped>
.page {
  background: transparent;
  padding: 0;
}
.toolbar {
  margin-bottom: 16px;
}
.el-pagination {
  margin-top: 16px;
}
</style>
