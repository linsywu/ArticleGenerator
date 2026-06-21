<template>
  <el-dialog v-model="visible" title="字数配置" width="520px">
    <el-form label-width="100px">
      <el-form-item label="字数选项">
        <div v-for="(opt, i) in options" :key="i" style="display:flex;gap:8px;margin-bottom:6px">
          <el-input v-model="options[i]" placeholder="例如：800" size="small" />
          <el-button size="small" text type="danger" @click="options.splice(i, 1)">×</el-button>
        </div>
        <el-button size="small" @click="options.push('')">＋ 添加选项</el-button>
      </el-form-item>
      <el-form-item label="默认字数">
        <el-select v-model="defaultWordCount" placeholder="选择默认字数" style="width:200px">
          <el-option v-for="opt in options.filter(Boolean)" :key="opt" :label="opt" :value="Number(opt)" />
        </el-select>
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="visible = false">取消</el-button>
      <el-button type="primary" :loading="saving" @click="handleSave">保存</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, watch } from "vue";
import { ElMessage } from "element-plus";
import { api } from "@/api/client";
import type { Account } from "@/api/types";

const props = defineProps<{ modelValue: boolean; account: Account | null }>();
const emit = defineEmits<{ (e: "update:modelValue", v: boolean): void; (e: "saved"): void }>();

const visible = ref(props.modelValue);
watch(() => props.modelValue, (v) => { visible.value = v; });
watch(visible, (v) => { emit("update:modelValue", v); });

const saving = ref(false);
const options = ref<string[]>([]);
const defaultWordCount = ref<number | null>(null);

watch(() => props.account, (acc) => {
  if (!acc) return;
  try { options.value = acc.word_count_options ? JSON.parse(acc.word_count_options) : []; }
  catch { options.value = []; }
  defaultWordCount.value = acc.word_count || null;
}, { immediate: true });

async function handleSave() {
  if (!props.account?.id) return;
  saving.value = true;
  try {
    const valid = options.value.filter(Boolean);
    await api.updateAccount(props.account.id, {
      word_count_options: valid.length ? JSON.stringify(valid) : null,
      word_count: defaultWordCount.value || null,
    });
    ElMessage.success("字数配置已保存");
    visible.value = false;
    emit("saved");
  } catch (e: any) { ElMessage.error(e?.response?.data?.detail || "保存失败"); }
  finally { saving.value = false; }
}
</script>
