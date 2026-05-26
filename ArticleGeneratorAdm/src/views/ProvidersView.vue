<template>
  <div class="providers-view">
    <div class="page-header">
      <h2>API 供应商管理</h2>
      <el-button type="primary" @click="openCreate">新增供应商</el-button>
    </div>

    <el-table :data="providers" stripe>
      <el-table-column prop="name" label="名称" />
      <el-table-column prop="base_url" label="API 地址" />
      <el-table-column label="API Key">
        <template #default="{ row }">
          <span v-if="showKey[row.id]">{{ row.api_key }}</span>
          <span v-else>****{{ row.api_key?.slice(-4) }}</span>
          <el-button size="small" text @click="showKey[row.id] = !showKey[row.id]">
            {{ showKey[row.id] ? '隐藏' : '显示' }}
          </el-button>
        </template>
      </el-table-column>
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

    <el-dialog v-model="dialogVisible" :title="isEdit ? '编辑供应商' : '新增供应商'" width="560px">
      <el-form :model="form" label-width="100px">
        <el-form-item label="名称" required>
          <el-input v-model="form.name" placeholder="Anthropic / DeepSeek / OpenAI" />
        </el-form-item>
        <el-form-item label="API 地址" required>
          <el-input v-model="form.base_url" placeholder="https://api.anthropic.com" />
        </el-form-item>
        <el-form-item label="API Key" required>
          <el-input v-model="form.api_key" type="password" show-password placeholder="sk-..." />
        </el-form-item>
        <el-form-item label="模型列表">
          <el-input v-model="form.models" type="textarea" :rows="3" placeholder='[{"name":"claude-opus-4-7","max_tokens":200000}]' />
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
import { api, Provider } from "@/api/client";

const providers = ref<Provider[]>([]);
const showKey = reactive<Record<number, boolean>>({});
const dialogVisible = ref(false);
const isEdit = ref(false);
const saving = ref(false);
const editId = ref<number | null>(null);

const form = reactive({
  name: "",
  base_url: "",
  api_key: "",
  models: "",
  enabled: true,
});

function resetForm() {
  form.name = "";
  form.base_url = "";
  form.api_key = "";
  form.models = "";
  form.enabled = true;
  editId.value = null;
}

async function load() {
  const { data } = await api.getProviders();
  providers.value = data;
}

function openCreate() {
  resetForm();
  isEdit.value = false;
  dialogVisible.value = true;
}

function openEdit(row: Provider) {
  resetForm();
  isEdit.value = true;
  editId.value = row.id;
  form.name = row.name;
  form.base_url = row.base_url;
  form.api_key = row.api_key;
  form.models = row.models || "";
  form.enabled = row.enabled;
  dialogVisible.value = true;
}

async function handleSave() {
  saving.value = true;
  try {
    if (isEdit.value && editId.value) {
      await api.updateProvider(editId.value, { ...form });
      ElMessage.success("已更新");
    } else {
      await api.createProvider({ ...form });
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

async function handleDelete(row: Provider) {
  try {
    await ElMessageBox.confirm(`确定删除供应商「${row.name}」？`, "确认删除", { type: "warning" });
    await api.deleteProvider(row.id);
    ElMessage.success("已删除");
    await load();
  } catch { /* cancelled */ }
}

onMounted(load);
</script>

<style scoped>
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}
</style>
