<template>
  <div class="scenario-configs-view">
    <div class="page-header">
      <h2>场景路由配置</h2>
      <el-button type="primary" @click="openCreate">新增配置</el-button>
    </div>

    <el-table :data="configs" stripe>
      <el-table-column prop="scenario" label="场景" width="140">
        <template #default="{ row }">
          <el-tag :type="scenarioTag(row.scenario)">{{ scenarioLabel(row.scenario) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="供应商" width="120">
        <template #default="{ row }">{{ row.provider?.name || '-' }}</template>
      </el-table-column>
      <el-table-column prop="model" label="模型" />
      <el-table-column label="优先级" width="80" prop="priority" />
      <el-table-column label="状态" width="80">
        <template #default="{ row }">
          <el-tag :type="row.enabled ? 'success' : 'info'">{{ row.enabled ? '启用' : '禁用' }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="160">
        <template #default="{ row }">
          <el-button size="small" @click="openEdit(row)">编辑</el-button>
          <el-button size="small" type="danger" @click="handleDelete(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="dialogVisible" :title="isEdit ? '编辑配置' : '新增配置'" width="640px">
      <el-form :model="form" label-width="110px">
        <el-form-item label="场景" required>
          <el-select v-model="form.scenario" :disabled="isEdit">
            <el-option label="蒸馏" value="distill" />
            <el-option label="生成" value="generate" />
            <el-option label="质量评审" value="quality_review" />
            <el-option label="合规评审" value="compliance_review" />
            <el-option label="微调" value="refine" />
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
          <el-input v-model="form.system_prompt_template" type="textarea" :rows="5" placeholder="支持 {{变量}} 占位" />
        </el-form-item>
        <el-form-item label="参数">
          <el-input v-model="form.params" type="textarea" :rows="2" placeholder='{"temperature": 0.7, "max_tokens": 4096}' />
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
import { ref, reactive, onMounted } from "vue";
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
  enabled: true,
});

const scenarioMap: Record<string, string> = {
  distill: "蒸馏", generate: "生成", quality_review: "质量评审",
  compliance_review: "合规评审", refine: "微调",
};

function scenarioLabel(s: string) { return scenarioMap[s] || s; }
function scenarioTag(s: string): string {
  const t: Record<string, string> = { distill: "warning", generate: "", quality_review: "success", compliance_review: "danger", refine: "info" };
  return t[s] || "";
}

function resetForm() {
  form.scenario = "generate";
  form.provider_id = 0;
  form.model = "";
  form.system_prompt_template = "";
  form.params = "";
  form.priority = 0;
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
</style>
