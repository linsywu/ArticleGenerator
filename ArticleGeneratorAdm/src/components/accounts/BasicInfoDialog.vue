<template>
  <el-dialog v-model="visible" title="编辑基本信息" width="480px">
    <el-form :model="form" label-width="80px">
      <el-form-item label="平台">
        <el-input v-model="form.platform" placeholder="公众号 / 小红书 / 知乎" />
      </el-form-item>
      <el-form-item label="账号名">
        <el-input v-model="form.account_name" placeholder="账号名称" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="visible = false">取消</el-button>
      <el-button type="primary" :loading="saving" @click="handleSave">保存</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, reactive, watch } from "vue";
import { ElMessage } from "element-plus";
import { api } from "@/api/client";
import type { Account } from "@/api/types";

const props = defineProps<{ modelValue: boolean; account: Account | null }>();
const emit = defineEmits<{ (e: "update:modelValue", v: boolean): void; (e: "saved"): void }>();

const visible = ref(props.modelValue);
watch(() => props.modelValue, (v) => { visible.value = v; });
watch(visible, (v) => { emit("update:modelValue", v); });

const saving = ref(false);
const form = reactive({ platform: "", account_name: "" });

watch(() => props.account, (acc) => {
  if (acc) { form.platform = acc.platform; form.account_name = acc.account_name; }
}, { immediate: true });

async function handleSave() {
  if (!props.account?.id) return;
  saving.value = true;
  try {
    await api.updateAccount(props.account.id, { platform: form.platform, account_name: form.account_name });
    ElMessage.success("已更新");
    visible.value = false;
    emit("saved");
  } catch (e: any) { ElMessage.error(e?.response?.data?.detail || "保存失败"); }
  finally { saving.value = false; }
}
</script>
