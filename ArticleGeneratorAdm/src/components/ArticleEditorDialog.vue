<template>
  <el-dialog
    :model-value="modelValue"
    :title="internalTitle"
    width="800px"
    @update:model-value="$emit('update:modelValue', $event)"
    @open="initEdit"
  >
    <!-- 文章标题 -->
    <h3 class="article-title">{{ article?.title || article?.hotspot?.title || "未知文章" }}</h3>

    <!-- 质量 & 合规评分 -->
    <div v-if="article && (article.quality_score != null || article.compliance_score != null)" class="score-bar">
      <el-tag v-if="article.quality_score != null" :type="scoreType(article.quality_score)" size="small" class="score-tag">
        质量: {{ article.quality_score }}
      </el-tag>
      <el-tag v-if="article.compliance_score != null" :type="complianceType(article.compliance_score)" size="small" class="score-tag">
        合规: {{ article.compliance_score }}
      </el-tag>
    </div>

    <!-- 编辑模式：文本域 -->
    <template v-if="editable && isEditing">
      <el-input
        v-model="editContent"
        type="textarea"
        :rows="16"
        placeholder="文章内容"
      />
    </template>

    <!-- 查看模式：预格式化文本 -->
    <template v-else>
      <div class="article-content-bg">
        <div class="article-content">{{ article?.content || "(无内容)" }}</div>
      </div>
      <div class="article-meta-row">
        <span class="word-count">字数：{{ article?.content?.length || 0 }}</span>
      </div>

      <!-- 评审记录 -->
      <div v-if="article?.review_notes" class="review-section">
        <div class="review-section-title">AI 评审记录：</div>
        <pre class="review-notes-text">{{ article.review_notes }}</pre>
      </div>
    </template>

    <!-- 底部按钮 -->
    <template #footer>
      <!-- 编辑模式：固定 save/cancel -->
      <template v-if="editable && isEditing">
        <el-button @click="cancelEdit">取消</el-button>
        <el-button type="primary" :loading="saving" @click="save">保存</el-button>
      </template>
      <!-- 查看模式：可覆写 -->
      <template v-else>
        <slot name="footer">
          <el-button @click="close">关闭</el-button>
          <el-button v-if="editable" @click="isEditing = true">编辑</el-button>
        </slot>
      </template>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, computed } from "vue";
import { ElMessage } from "element-plus";
import { api, type Article } from "@/api/client";

const props = defineProps<{
  modelValue: boolean;
  article: (Article & { title?: string }) | null;
  editable?: boolean;
  /** 覆盖对话框标题，默认为 "文章详情" */
  dialogTitle?: string;
  /** 打开时直接进入编辑模式（仅在 editable=true 时有效） */
  initialEdit?: boolean;
}>();

const emit = defineEmits<{
  (e: "update:modelValue", val: boolean): void;
  /** 保存成功后触发，携带 article id 与当前 content */
  (e: "saved", payload: { id: number; content: string }): void;
}>();

const internalTitle = computed(() => props.dialogTitle || "文章详情");

const isEditing = ref(false);
const editContent = ref("");
const saving = ref(false);

function initEdit() {
  if (props.initialEdit && props.editable) {
    isEditing.value = true;
    editContent.value = props.article?.content || "";
  } else {
    isEditing.value = false;
    editContent.value = "";
  }
}

function close() {
  emit("update:modelValue", false);
}

function cancelEdit() {
  isEditing.value = false;
  editContent.value = "";
}

async function save() {
  if (!props.article?.id) return;
  saving.value = true;
  try {
    await api.updateArticle(props.article.id, { content: editContent.value });
    ElMessage.success("已保存");
    emit("saved", { id: props.article.id, content: editContent.value });
    isEditing.value = false;
    close();
  } catch {
    ElMessage.error("保存失败");
  } finally {
    saving.value = false;
  }
}

function startEditing() {
  if (props.editable) {
    isEditing.value = true;
    editContent.value = props.article?.content || "";
  }
}

defineExpose({ startEditing });

function scoreType(s: number) {
  if (s >= 80) return "success";
  if (s >= 60) return "warning";
  return "danger";
}

function complianceType(s: number) {
  if (s === 100) return "success";
  if (s >= 60) return "warning";
  return "danger";
}
</script>

<style scoped>
.article-title {
  font-family: var(--font-serif);
  font-size: 18px;
  font-weight: 700;
  color: var(--text-on-dark);
  margin-bottom: var(--space-sm);
  line-height: 1.4;
}

.score-bar {
  display: flex;
  gap: 8px;
  margin-bottom: var(--space-md);
}
.score-tag {
  flex-shrink: 0;
}

.article-content-bg {
  background: var(--ink-surface);
  padding: var(--space-xl);
  border-radius: var(--radius-lg);
}

.article-content {
  white-space: pre-wrap;
  max-height: 400px;
  overflow-y: auto;
  line-height: 1.6;
  color: var(--text-on-dark);
}

.article-meta-row {
  display: flex;
  justify-content: flex-end;
  align-items: center;
  margin-top: var(--space-sm);
}
.word-count {
  font-size: 12px;
  color: var(--text-muted);
}

.review-section {
  background: var(--ink-surface);
  padding: var(--space-md);
  border-radius: var(--radius-lg);
  margin-top: var(--space-md);
}
.review-section-title {
  font-size: 14px;
  color: var(--text-on-dark);
  font-weight: 500;
  margin-bottom: var(--space-sm);
}
.review-notes-text {
  white-space: pre-wrap;
  font-size: 13px;
  color: var(--text-muted);
  margin-top: 4px;
  font-family: inherit;
}
</style>
