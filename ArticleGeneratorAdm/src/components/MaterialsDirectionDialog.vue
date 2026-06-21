<template>
  <el-dialog
    :model-value="modelValue"
    @update:model-value="$emit('update:modelValue', $event)"
    :title="dialogTitle"
    width="600px"
    :close-on-click-modal="false"
    @open="onOpen"
    @close="onClose"
  >
    <!-- Loading state -->
    <div v-if="loading" class="direction-loading">
      <div class="direction-spinner"></div>
      <p>正在生成创作方向...</p>
    </div>

    <!-- Error state -->
    <div v-else-if="errorMsg" class="direction-error">
      <p>{{ errorMsg }}</p>
      <el-button type="primary" @click="startGeneration">重试</el-button>
    </div>

    <!-- Directions grid -->
    <div v-else-if="directions.length" class="directions-grid">
      <div
        v-for="d in directions"
        :key="d.id"
        class="direction-card"
        :class="{ selected: selectedDirection?.id === d.id }"
        @click="selectedDirection = d"
      >
        <span class="direction-id">{{ d.id }}</span>
        <span class="direction-title">{{ d.title }}</span>
        <span v-if="selectedDirection?.id === d.id" class="direction-check">✓</span>
      </div>
    </div>

    <template #footer>
      <el-button @click="$emit('update:modelValue', false)">取消</el-button>
      <el-button
        type="primary"
        :disabled="!selectedDirection"
        @click="goCreate"
      >
        去创作
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, computed } from "vue";
import { useRouter } from "vue-router";
import { api } from "@/api/client";
import type { DirectionItem, MpMaterial } from "@/api/types";

const props = defineProps<{
  modelValue: boolean;
  material: MpMaterial | null;
}>();

const emit = defineEmits<{
  "update:modelValue": [value: boolean];
}>();

const router = useRouter();

const directions = ref<DirectionItem[]>([]);
const selectedDirection = ref<DirectionItem | null>(null);
const loading = ref(false);
const errorMsg = ref("");
let generationCancelled = false;

const dialogTitle = computed(() => {
  return props.material?.title
    ? `创作方向 - ${props.material.title.slice(0, 30)}${props.material.title.length > 30 ? "..." : ""}`
    : "创作方向";
});

function onOpen() {
  if (props.material?.title) {
    startGeneration();
  }
}

function onClose() {
  generationCancelled = true;
  directions.value = [];
  selectedDirection.value = null;
  errorMsg.value = "";
  loading.value = false;
}

async function startGeneration() {
  if (!props.material?.title) {
    errorMsg.value = "素材信息不完整（缺少标题）";
    return;
  }

  generationCancelled = false;
  loading.value = true;
  errorMsg.value = "";
  directions.value = [];
  selectedDirection.value = null;

  try {
    const { data } = await api.generateDirections(
      0,
      props.material.title
    );
    const taskId = (data as any).task_id;
    if (!taskId) throw new Error("未获取到任务 ID");

    // Poll for result (same pattern as CreateView)
    let attempts = 0;
    const maxAttempts = 30;
    while (attempts < maxAttempts) {
      await new Promise((r) => setTimeout(r, 2000));
      if (generationCancelled) return;
      const { data: taskData } = await api.getTaskResult(taskId);
      if (generationCancelled) return;
      if (taskData.status === "success") {
        const result = (taskData as any).result;
        directions.value = result?.directions || [];
        if (directions.value.length) {
          selectedDirection.value = directions.value[0];
        }
        return;
      }
      if (taskData.status === "failed") {
        throw new Error(
          (taskData as any).error_message || "方向生成失败"
        );
      }
      attempts++;
    }
    throw new Error("方向生成超时，请重试");
  } catch (e: any) {
    errorMsg.value =
      e?.response?.data?.detail || e?.message || "方向生成失败";
  } finally {
    loading.value = false;
  }
}

function goCreate() {
  if (!selectedDirection.value || !props.material) return;

  const query: Record<string, string> = {
    idea: props.material.title || "",
  };

  emit("update:modelValue", false);
  router.push({ path: "/create", query });
}
</script>

<style scoped>
.direction-loading {
  text-align: center;
  padding: 40px;
  color: var(--text-muted);
}
.direction-loading p {
  margin-top: 16px;
  font-size: 14px;
}

.direction-spinner {
  width: 40px;
  height: 40px;
  border: 3px solid var(--ink-border, #e0e0e0);
  border-top-color: var(--amber, #c8843c);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  margin: 0 auto;
}
@keyframes spin {
  to { transform: rotate(360deg); }
}

.direction-error {
  text-align: center;
  padding: 40px;
}
.direction-error p {
  color: var(--text-muted);
  margin-bottom: 16px;
}

.directions-grid {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.direction-card {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 14px 18px;
  background: var(--ink-surface, #f5f5f5);
  border: 1px solid var(--ink-border, #e0e0e0);
  border-radius: 8px;
  cursor: pointer;
  transition: border-color 0.2s, background-color 0.2s;
}
.direction-card:hover {
  border-color: var(--text-dim, #999);
}
.direction-card.selected {
  border-color: var(--amber, #c8843c);
  background: rgba(200, 132, 60, 0.06);
}

.direction-id {
  font-size: 20px;
  font-weight: 700;
  color: var(--amber, #c8843c);
  width: 32px;
  flex-shrink: 0;
}

.direction-title {
  flex: 1;
  font-size: 15px;
  color: var(--text-on-dark, #333);
}

.direction-check {
  color: var(--amber, #c8843c);
  font-weight: 700;
}
</style>
