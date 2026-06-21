<template>
  <el-dialog v-model="visible" title="新增账号" width="720px" :close-on-click-modal="false" @close="handleClose">
    <el-steps :active="step" align-center style="margin-bottom: 32px;">
      <el-step title="基本信息" />
      <el-step title="参考文章" />
      <el-step title="确认并蒸馏" />
    </el-steps>

    <div v-if="step === 0">
      <el-form ref="formRef" :model="basicForm" :rules="rules" label-width="80px">
        <el-form-item label="平台" prop="platform">
          <el-input v-model="basicForm.platform" placeholder="公众号 / 小红书 / B站 / 知乎" />
        </el-form-item>
        <el-form-item label="账号名" prop="account_name">
          <el-input v-model="basicForm.account_name" placeholder="账号名称" />
        </el-form-item>
      </el-form>
      <div style="text-align:right;margin-top:24px;">
        <el-button @click="visible = false">取消</el-button>
        <el-button type="primary" @click="nextStep">下一步 →</el-button>
      </div>
    </div>

    <div v-if="step === 1">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;">
        <span style="font-weight:600;">已添加 {{ wizardArticles.length }} 篇文章</span>
        <el-button size="small" @click="openArticleForm()">＋ 添加文章</el-button>
      </div>
      <div v-if="wizardArticles.length" class="article-list">
        <div v-for="(a, i) in wizardArticles" :key="i" class="article-row">
          <div class="article-info">
            <span class="article-title">{{ a.title }}</span>
            <span v-if="a.is_benchmark" class="tag-benchmark">代表篇</span>
          </div>
          <div>
            <el-button size="small" text @click="openArticleForm(i)">编辑</el-button>
            <el-button size="small" text type="danger" @click="wizardArticles.splice(i, 1)">删除</el-button>
          </div>
        </div>
      </div>
      <div v-else class="empty-hint">请添加至少一篇参考文章。建议 3~5 篇最具代表性的文章。</div>
      <div style="text-align:right;margin-top:24px;display:flex;justify-content:space-between;">
        <el-button @click="step = 0">← 上一步</el-button>
        <el-button type="primary" :disabled="!wizardArticles.length" @click="nextStep">下一步：确认并蒸馏 →</el-button>
      </div>
    </div>

    <div v-if="step === 2">
      <div class="confirm-card">
        <h4 style="margin-bottom:12px;">确认信息</h4>
        <table style="width:100%;font-size:14px;">
          <tr><td style="padding:4px 0;color:var(--text-dim);">平台</td><td>{{ basicForm.platform }}</td></tr>
          <tr><td style="padding:4px 0;color:var(--text-dim);">账号</td><td>{{ basicForm.account_name }}</td></tr>
          <tr><td style="padding:4px 0;color:var(--text-dim);">参考文章</td><td>{{ wizardArticles.length }} 篇</td></tr>
        </table>
      </div>
      <p style="margin:16px 0;font-size:13px;color:var(--text-dim);">
        点击"开始蒸馏"后，系统将分析参考文章，提取 7 个维度的写作风格特征。预计耗时 30~60 秒。
      </p>
      <div style="text-align:right;display:flex;justify-content:space-between;">
        <el-button @click="step = 1">← 上一步</el-button>
        <el-button type="primary" :loading="submitting" size="large" @click="handleSubmit">🔥 开始蒸馏</el-button>
      </div>
    </div>

    <el-dialog v-model="articleFormVisible" :title="editingIdx >= 0 ? '编辑文章' : '添加文章'" width="720px" append-to-body>
      <ReferenceArticleForm ref="articleFormRef" :article="editingArticle" />
      <template #footer>
        <el-button @click="articleFormVisible = false">取消</el-button>
        <el-button type="primary" @click="saveArticleForm">{{ editingIdx >= 0 ? '保存' : '添加' }}</el-button>
      </template>
    </el-dialog>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, computed } from "vue";
import type { FormInstance } from "element-plus";
import { ElMessage } from "element-plus";
import { api } from "@/api/client";
import ReferenceArticleForm from "./ReferenceArticleForm.vue";

const emit = defineEmits<{ (e: "created"): void }>();

const visible = ref(false);
const step = ref(0);
const submitting = ref(false);

const basicForm = ref({ platform: "", account_name: "" });
const rules = {
  platform: [{ required: true, message: "请选择平台", trigger: "blur" }],
  account_name: [{ required: true, message: "请输入账号名称", trigger: "blur" }],
};
const formRef = ref<FormInstance>();

const wizardArticles = ref<Array<{ title: string; content: string; source_url: string; is_benchmark: boolean }>>([]);

const articleFormVisible = ref(false);
const editingIdx = ref(-1);
const articleFormRef = ref<InstanceType<typeof ReferenceArticleForm>>();

const editingArticle = computed(() => {
  if (editingIdx.value >= 0 && wizardArticles.value[editingIdx.value]) {
    return wizardArticles.value[editingIdx.value];
  }
  return null;
});

function show() {
  basicForm.value = { platform: "", account_name: "" };
  wizardArticles.value = [];
  step.value = 0;
  visible.value = true;
}

function nextStep() {
  if (step.value < 2) step.value++;
}

function openArticleForm(idx?: number) {
  editingIdx.value = idx ?? -1;
  articleFormVisible.value = true;
}

function saveArticleForm() {
  const data = articleFormRef.value?.getFormData();
  if (!data || !data.title || !data.content) {
    ElMessage.warning("标题和正文不能为空");
    return;
  }
  if (editingIdx.value >= 0) {
    wizardArticles.value[editingIdx.value] = { ...data };
  } else {
    wizardArticles.value.push({ ...data });
  }
  articleFormVisible.value = false;
  articleFormRef.value?.reset();
}

async function handleSubmit() {
  submitting.value = true;
  try {
    const { data: account } = await api.createAccount({
      platform: basicForm.value.platform,
      account_name: basicForm.value.account_name,
    });
    const accountId = account.id;

    for (const a of wizardArticles.value) {
      await api.createReferenceArticle(accountId, {
        account_id: accountId,
        title: a.title,
        content: a.content,
        source_url: a.source_url || undefined,
        is_benchmark: a.is_benchmark,
      } as any);
    }

    await api.triggerDistill(accountId);
    ElMessage.success("账号创建完成，蒸馏任务已开始");
    visible.value = false;
    emit("created");
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || "创建失败");
  } finally {
    submitting.value = false;
  }
}

function handleClose() {
  basicForm.value = { platform: "", account_name: "" };
  wizardArticles.value = [];
  step.value = 0;
}

defineExpose({ show });
</script>

<style scoped>
.confirm-card { background: var(--ink-surface); padding: 16px; border-radius: 8px; }
.article-list { display: flex; flex-direction: column; gap: 6px; }
.article-row {
  display: flex; align-items: center; justify-content: space-between;
  padding: 10px 14px; background: var(--ink-surface); border-radius: var(--radius-md);
}
.article-info { display: flex; align-items: center; gap: 8px; }
.article-title { font-size: 14px; color: var(--text-on-dark); font-weight: 500; }
.tag-benchmark {
  font-size: 10px; padding: 2px 8px; border-radius: 10px;
  background: var(--amber-glow); color: var(--amber-light); font-weight: 600;
}
.empty-hint { text-align: center; padding: 32px; color: var(--text-dim); font-size: 14px; }
</style>
