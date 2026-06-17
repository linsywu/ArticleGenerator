/**
 * tasks store — 活跃任务轮询，跨页共享
 */
import { defineStore } from "pinia";
import { ref, computed } from "vue";
import { api, type UnifiedTaskItem } from "@/api/client";

export const useTasksStore = defineStore("tasks", () => {
  const activeTasks = ref<UnifiedTaskItem[]>([]);
  const runningCount = ref(0);
  const pendingCount = ref(0);

  const totalActive = computed(() => runningCount.value + pendingCount.value);

  let timer: ReturnType<typeof setInterval> | null = null;

  async function fetch() {
    try {
      const { data } = await api.getUnifiedTasks({ status: "running,pending", limit: 50 });
      activeTasks.value = data.tasks;
      runningCount.value = data.running_count;
      pendingCount.value = data.pending_count;
    } catch {
      /* ignore */
    }
  }

  function startPolling(intervalMs = 5000) {
    fetch();
    if (!timer) timer = setInterval(fetch, intervalMs);
  }

  function stopPolling() {
    if (timer) {
      clearInterval(timer);
      timer = null;
    }
  }

  return {
    activeTasks,
    runningCount,
    pendingCount,
    totalActive,
    fetch,
    startPolling,
    stopPolling,
  };
});
