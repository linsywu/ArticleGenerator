<template>
  <div class="scenario-configs-view">
    <div class="page-header">
      <h2>场景路由配置</h2>
      <el-button type="primary" @click="openCreate">新增配置</el-button>
    </div>

    <el-table :data="configs" stripe>
      <el-table-column prop="sort_order" label="顺序" width="60" />
      <el-table-column label="场景" width="110">
        <template #default="{ row }">
          <el-tag :type="scenarioTag(row.scenario)" size="small">{{ scenarioLabel(row.scenario) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="description" label="说明" width="230" />
      <el-table-column label="提示词预览" show-overflow-tooltip>
        <template #default="{ row }">{{row.system_prompt_template || ''}}</template>
      </el-table-column>
      <el-table-column prop="model" label="模型" width="140" />
      <el-table-column label="状态" width="70">
        <template #default="{ row }">
          <el-tag :type="row.enabled ? 'success' : 'info'" size="small">{{ row.enabled ? '启用' : '禁用' }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="200" fixed="right">
        <template #default="{ row }">
          <el-button size="small" @click="openEdit(row)">编辑</el-button>
          <el-button v-if="!row.enabled" size="small" type="success" @click="handleActivate(row)">激活</el-button>
          <el-button size="small" type="danger" @click="handleDelete(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="dialogVisible" :title="isEdit ? '编辑配置' : '新增配置'" width="1024px">
      <el-form :model="form" label-width="110px">
        <el-form-item label="场景" required>
          <el-select v-model="form.scenario" :disabled="isEdit">
            <el-option v-for="s in scenarioOptions" :key="s.value" :label="s.label" :value="s.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="供应商" required>
          <el-select v-model="form.provider_id" placeholder="选择供应商">
            <el-option v-for="p in providers" :key="p.id" :label="p.name" :value="p.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="模型" required>
          <el-input v-model="form.model" placeholder="claude-opus-4-7" />
        </el-form-item>
        <el-form-item label="System Prompt">
          <div v-if="currentScenarioVars.length" class="var-hints">
            <span class="var-hints-label">可用变量：</span>
            <el-tooltip
              v-for="v in currentScenarioVars"
              :key="v.name"
              :content="v.description"
              placement="top"
            >
              <el-tag
                size="small"
                type="info"
                class="var-tag"
                @click="insertVar(v.name)"
              >{{ varLabel(v.name) }}</el-tag>
            </el-tooltip>
          </div>
          <el-input v-model="form.system_prompt_template" type="textarea" :rows="9" placeholder="支持 {{变量}} 占位" />
        </el-form-item>
        <el-form-item label="参数">
          <el-input v-model="form.params" type="textarea" :rows="2" placeholder='{"temperature": 0.7, "max_tokens": 4096}' />
        </el-form-item>
        <el-form-item label="说明">
          <el-input v-model="form.description" placeholder="如：⑤ 文章生成：根据主题+风格画像生成全文" />
        </el-form-item>
        <el-form-item label="排序">
          <el-input-number v-model="form.sort_order" :min="0" :max="99" />
        </el-form-item>
        <el-form-item label="优先级">
          <el-input-number v-model="form.priority" :min="0" :max="99" />
        </el-form-item>
        <el-form-item label="启用">
          <el-switch v-model="form.enabled" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSave" :loading="saving">{{ isEdit ? '保存' : '创建' }}</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { api, ScenarioConfig, Provider } from "@/api/client";

const configs = ref<ScenarioConfig[]>([]);
const providers = ref<Provider[]>([]);
const dialogVisible = ref(false);
const isEdit = ref(false);
const saving = ref(false);
const editId = ref<number | null>(null);

const form = reactive({
  scenario: "generate",
  provider_id: 0,
  model: "",
  system_prompt_template: "",
  params: "",
  priority: 0,
  description: "",
  sort_order: 0,
  enabled: true,
});

const scenarioOptions = [
  {value:"distill-extract",label:"a 特征清单提取"},
  {value:"distill-synthesize",label:"b 写作风格生成"},
  { value: "material-summary", label: "⓪ 素材摘要" },
  { value: "distill", label: "① 蒸馏" },
  { value: "direction", label: "② 方向生成" },
  { value: "outline", label: "③ 大纲生成" },
  { value: "title", label: "④ 标题生成" },
  { value: "generate", label: "⑤ 文章生成" },
  { value: "humanize", label: "⑥ 去AI味" },
  { value: "quality_review", label: "⑦ 质量评审" },
  { value: "compliance_review", label: "⑧ 合规评审" },
  { value: "refine", label: "⑨ 微调" },
];

const scenarioMap: Record<string, string> = Object.fromEntries(scenarioOptions.map(s => [s.value, s.label]));

// 各场景可用变量定义（hover 显示说明，点击插入到光标位置）
const scenarioVariables: Record<string, { name: string; description: string }[]> = {
  generate: [
    { name: 'topic', description: '文章主题（用户确认的标题 + 原始想法，或热点标题）' },
    { name: 'style_profile', description: '账号风格画像文本（来自风格蒸馏）' },
    { name: 'style_instructions', description: '结构化风格要求（句式/用词/禁忌/留白）；无结构化画像时为空字符串' },
    { name: 'outline_section', description: '写作大纲整段（含 ## 标题和约束语）；用户跳过或无大纲时为空字符串' },
    { name: 'word_count_instruction', description: '字数要求，如「字数1500左右。」' },
  ],
  humanize: [
    { name: 'article_content', description: 'generate 步骤生成的原始文章全文' },
    { name: 'outline_section', description: '写作大纲整段（含标题和约束语）；无大纲时为空字符串' },
  ],
  title: [
    { name: 'style_profile', description: '账号风格画像文本' },
    { name: 'idea', description: '用户输入的原始想法' },
    { name: 'direction', description: '用户选择的写作方向' },
    { name: 'outline', description: '大纲要点列表（字符串数组的文本表示）' },
  ],
  outline: [
    { name: 'style_profile', description: '账号风格画像文本' },
    { name: 'idea', description: '用户输入的原始想法' },
    { name: 'direction', description: '用户选择的写作方向' },
  ],
  direction: [
    { name: 'style_profile', description: '账号风格画像文本' },
    { name: 'idea', description: '用户输入的原始想法' },
  ],
  quality_review: [
    { name: 'article_content', description: 'humanize 之后的文章全文' },
  ],
  compliance_review: [
    { name: 'article_content', description: 'humanize 之后的文章全文' },
  ],
  refine: [
    { name: 'article_content', description: '待微调的文章全文' },
    { name: 'keywords', description: '用户输入的修改关键词' },
  ],
  distill: [
    { name: 'articles_content', description: '多篇参考文章合并后的全文（含序号分隔）' },
  ],
  "material-summary": [
    { name: 'title', description: '素材文章标题' },
    { name: 'content', description: '素材文章全文内容' },
  ],
};

function varLabel(name: string) { return `{{${name}}}`; }

const currentScenarioVars = computed(() => scenarioVariables[form.scenario] || []);

function insertVar(varName: string) {
  const placeholder = `{{${varName}}}`;
  // 如果已有值，追加到末尾；否则直接设置
  if (form.system_prompt_template) {
    form.system_prompt_template += placeholder;
  } else {
    form.system_prompt_template = placeholder;
  }
}

function scenarioLabel(s: string) { return scenarioMap[s] || s; }
function scenarioTag(s: string): string {
  const t: Record<string, string> = { "material-summary": "info", distill: "warning", generate: "", quality_review: "success", compliance_review: "danger", refine: "info" };
  return t[s] || "";
}

function resetForm() {
  form.scenario = "generate";
  form.provider_id = 0;
  form.model = "";
  form.system_prompt_template = "";
  form.params = "";
  form.priority = 0;
  form.description = "";
  form.sort_order = 0;
  form.enabled = true;
  editId.value = null;
}

async function load() {
  const [c, p] = await Promise.all([api.getScenarioConfigs(), api.getProviders()]);
  configs.value = c.data;
  providers.value = p.data;
}

function openCreate() {
  resetForm();
  isEdit.value = false;
  dialogVisible.value = true;
}

function openEdit(row: ScenarioConfig) {
  resetForm();
  isEdit.value = true;
  editId.value = row.id;
  form.scenario = row.scenario;
  form.provider_id = row.provider_id;
  form.model = row.model;
  form.system_prompt_template = row.system_prompt_template || "";
  form.params = row.params || "";
  form.priority = row.priority;
  form.description = row.description || "";
  form.sort_order = row.sort_order || 0;
  form.enabled = row.enabled;
  dialogVisible.value = true;
}

async function handleSave() {
  saving.value = true;
  try {
    if (isEdit.value && editId.value) {
      await api.updateScenarioConfig(editId.value, { ...form });
      ElMessage.success("已更新");
    } else {
      await api.createScenarioConfig({ ...form });
      ElMessage.success("已创建");
    }
    dialogVisible.value = false;
    await load();
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || "操作失败");
  } finally {
    saving.value = false;
  }
}

async function handleActivate(row: ScenarioConfig) {
  try {
    await api.activateScenarioConfig(row.id);
    ElMessage.success(`已激活 ${scenarioLabel(row.scenario)} 配置`);
    await load();
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || "操作失败");
  }
}

async function handleDelete(row: ScenarioConfig) {
  try {
    await ElMessageBox.confirm(`确定删除场景「${scenarioLabel(row.scenario)}」的配置？`, "确认", { type: "warning" });
    await api.deleteScenarioConfig(row.id);
    ElMessage.success("已删除");
    await load();
  } catch { /* cancelled */ }
}

onMounted(load);
</script>

<style scoped>
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }

.var-hints {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
  margin-bottom: 8px;
  padding: 8px 12px;
  background: var(--el-fill-color-light);
  border-radius: 6px;
  border: 1px solid var(--el-border-color-lighter);
}
.var-hints-label {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  margin-right: 2px;
}
.var-tag {
  cursor: pointer;
  font-family: monospace;
  font-size: 11px;
  transition: all 0.2s;
}
.var-tag:hover {
  transform: translateY(-1px);
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.1);
}
</style>
