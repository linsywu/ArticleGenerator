<template>
  <el-form :model="form" label-width="80px">
    <el-form-item label="标题" required>
      <el-input v-model="form.title" placeholder="文章标题" />
    </el-form-item>
    <el-form-item label="正文" required>
      <el-input v-model="form.content" type="textarea" :rows="6" placeholder="粘贴文章正文" />
    </el-form-item>
    <el-form-item label="来源链接">
      <el-input v-model="form.source_url" placeholder="https://...（可选）" />
    </el-form-item>
    <el-form-item label="代表篇">
      <el-switch v-model="form.is_benchmark" />
      <span style="margin-left:8px;font-size:12px;color:var(--text-dim)">标记为最具代表性的文章</span>
    </el-form-item>
  </el-form>
</template>

<script setup lang="ts">
import { reactive, watch } from "vue";

const props = defineProps<{
  article?: { title: string; content: string; source_url: string; is_benchmark: boolean } | null;
}>();

const form = reactive({
  title: "",
  content: "",
  source_url: "",
  is_benchmark: false,
});

watch(() => props.article, (a) => {
  if (a) {
    form.title = a.title || "";
    form.content = a.content || "";
    form.source_url = a.source_url || "";
    form.is_benchmark = !!a.is_benchmark;
  }
}, { immediate: true });

function getFormData() {
  return { title: form.title, content: form.content, source_url: form.source_url, is_benchmark: form.is_benchmark };
}

function reset() {
  form.title = "";
  form.content = "";
  form.source_url = "";
  form.is_benchmark = false;
}

defineExpose({ getFormData, reset });
</script>
