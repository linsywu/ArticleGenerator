<template>
  <div class="page">
    <PageHeader title="评审队列" subtitle="查看文章质量评分，通过或拒绝，或触发微调循环" />

    <el-empty v-if="!loading && list.length === 0" description="暂无待评审文章" />
    <el-table v-else :data="list" v-loading="loading" style="width: 100%">
      <el-table-column prop="id" label="ID" width="70" />
      <el-table-column label="文章标题" min-width="200">
        <template #default="{ row }">{{ row.title || row.hotspot?.title || "-" }}</template>
      </el-table-column>
      <el-table-column label="账号" width="120">
        <template #default="{ row }">{{ row.account?.account_name || "-" }}</template>
      </el-table-column>
      <el-table-column label="生成时间" width="180">
        <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
      </el-table-column>
      <el-table-column label="质量" width="80">
        <template #default="{ row }">
          <el-tag v-if="row.quality_score != null" :type="scoreType(row.quality_score)" size="small">
            {{ row.quality_score }}
          </el-tag>
          <span v-else style="color:#999">-</span>
        </template>
      </el-table-column>
      <el-table-column label="合规" width="90">
        <template #default="{ row }">
          <el-tag v-if="row.compliance_score === 100" type="success" size="small">安全</el-tag>
          <el-tag v-else-if="row.compliance_score != null && row.compliance_score >= 60" type="warning" size="small">低风险</el-tag>
          <el-tag v-else-if="row.compliance_score != null" type="danger" size="small">高风险</el-tag>
          <span v-else style="color:#999">-</span>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="280" fixed="right">
        <template #default="{ row }">
          <el-button size="small" @click="viewArticle(row)">查看</el-button>
          <el-button size="small" type="success" @click="approve(row)">通过</el-button>
          <el-button size="small" type="danger" @click="reject(row)">拒绝</el-button>
          <el-button size="small" @click="openRefine(row)">微调</el-button>
        </template>
      </el-table-column>
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

    <ArticleEditorDialog
      ref="articleEditorRef"
      v-model="detailVisible"
      :article="currentArticle"
      editable
      @saved="onArticleSaved"
    >
      <template #footer>
        <el-button @click="detailVisible = false">关闭</el-button>
        <el-button @click="articleEditorRef?.startEditing()">编辑</el-button>
        <el-button type="success" @click="approve(currentArticle!)">通过</el-button>
        <el-button type="danger" @click="reject(currentArticle!)">拒绝</el-button>
        <el-button @click="openRefine(currentArticle!)">微调</el-button>
      </template>
    </ArticleEditorDialog>

    <el-dialog v-model="refineVisible" title="微调" width="500px">
      <el-input
        v-model="refineKeywords"
        type="textarea"
        rows="3"
        placeholder="输入修改关键词，如：增加幽默感、缩短到500字"
      />
      <p class="refine-tip">微调完成后将自动刷新列表，您也可点击「刷新」按钮手动刷新。</p>
      <template #footer>
        <el-button @click="refineVisible = false">取消</el-button>
        <el-button type="primary" :loading="refining" @click="doRefine">确认微调</el-button>
      </template>
    </el-dialog>
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
const detailVisible = ref(false);
const currentArticle = ref<Article | null>(null);
const refineVisible = ref(false);
const refineKeywords = ref("");
const refining = ref(false);

const articleEditorRef = ref<InstanceType<typeof ArticleEditorDialog> | null>(null);

function onArticleSaved() {
  load();
}

async function load() {
  loading.value = true;
  try {
    const res = await api.getArticles({ status: "pending_review", page: page.value, page_size: pageSize.value });
    const payload = res.data as { data: Article[]; total: number };
    list.value = payload.data;
    total.value = payload.total;
  } catch (e) {
    ElMessage.error("加载失败");
  } finally {
    loading.value = false;
  }
}

function scoreType(s: number) {
  if (s >= 80) return "success";
  if (s >= 60) return "warning";
  return "danger";
}

function viewArticle(row: Article) {
  currentArticle.value = row;
  detailVisible.value = true;
}

async function approve(row: Article) {
  try {
    await api.updateArticleStatus(row.id, "approved");
    ElMessage.success("已通过");
    detailVisible.value = false;
    load();
  } catch (e) {
    ElMessage.error("操作失败");
  }
}

async function reject(row: Article) {
  try {
    await api.updateArticleStatus(row.id, "rejected");
    ElMessage.success("已拒绝");
    detailVisible.value = false;
    load();
  } catch (e) {
    ElMessage.error("操作失败");
  }
}

function openRefine(row: Article) {
  currentArticle.value = row;
  refineKeywords.value = "";
  refineVisible.value = true;
}

async function doRefine() {
  if (!currentArticle.value || !refineKeywords.value.trim()) return;
  refining.value = true;
  try {
    await api.triggerRefine(currentArticle.value.id, refineKeywords.value.trim());
    refineVisible.value = false;
    ElMessage.success("微调任务已加入任务中心");
  } catch (e) {
    ElMessage.error("提交失败");
  } finally {
    refining.value = false;
  }
}

onMounted(load);
</script>

<style scoped>
.page { padding: 0; }
.refine-tip { margin-top: 12px; font-size: 12px; color: var(--text-muted); }
.el-pagination { margin-top: 16px; }
</style>
