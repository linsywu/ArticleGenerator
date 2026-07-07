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

    <el-dialog v-model="refineVisible" title="微调" width="550px">
      <!-- 评审建议 -->
      <div v-if="refineSuggestions.length" class="refine-suggestions">
        <div class="refine-suggestions-title">📋 质量评审发现的问题（将优先修复）：</div>
        <div v-for="(wp, i) in refineSuggestions" :key="i" class="refine-suggestion-item">
          <el-tag :type="wp.severity === 'high' ? 'danger' : 'warning'" size="small">段落 {{ wp.index }}</el-tag>
          <span class="refine-suggestion-issue">{{ wp.issue }}</span>
          <span class="refine-suggestion-tip">💡 {{ wp.suggestion }}</span>
        </div>
      </div>
      <div v-else-if="currentArticle?.quality_review_detail" class="refine-no-issues">
        ✅ 评审未发现明显问题段落，可自由输入修改方向
      </div>
      <el-input
        v-model="refineKeywords"
        type="textarea"
        rows="3"
        placeholder="补充修改方向（选填），如：语气更温和"
      />
      <p class="refine-tip">提交后将自动改写问题段落，其他内容保持不变。可在任务中心查看进度。</p>
      <template #footer>
        <el-button @click="refineVisible = false">取消</el-button>
        <el-button type="primary" :loading="refining" @click="doRefine">确认微调</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from "vue";
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

const refineSuggestions = computed(() => {
  if (!currentArticle.value?.quality_review_detail) return [];
  try {
    const detail = JSON.parse(currentArticle.value.quality_review_detail);
    return detail.weak_paragraphs || [];
  } catch {
    return [];
  }
});

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
  if (!currentArticle.value) return;
  refining.value = true;
  try {
    await api.triggerRefine(currentArticle.value.id, refineKeywords.value.trim() || "优化文章质量");
    refineVisible.value = false;
    ElMessage.success({ message: "微调任务已提交，仅改写问题段落，其他内容保持不变。请在任务中心查看进度。", duration: 5000 });
    // 延迟刷新，给微调处理时间
    setTimeout(() => load(), 3000);
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
.refine-suggestions {
  background: var(--el-fill-color-light);
  padding: 12px;
  border-radius: 6px;
  margin-bottom: 12px;
}
.refine-suggestions-title {
  font-size: 13px;
  font-weight: 500;
  margin-bottom: 8px;
  color: var(--el-text-color-primary);
}
.refine-suggestion-item {
  display: flex;
  align-items: flex-start;
  gap: 6px;
  margin-bottom: 6px;
  font-size: 12px;
  line-height: 1.5;
}
.refine-suggestion-issue {
  color: var(--el-text-color-regular);
}
.refine-suggestion-tip {
  color: var(--el-color-success);
}
.refine-no-issues {
  font-size: 13px;
  color: var(--el-color-success);
  margin-bottom: 12px;
}
.refine-tip { margin-top: 12px; font-size: 12px; color: var(--text-muted); }
.el-pagination { margin-top: 16px; }
</style>
