/**
 * useActiveTasks — 全局单例的活跃任务轮询 composable
 *
 * 替换 LayoutView.vue 与 TaskCenterView.vue 中重复的轮询逻辑。
 * 模块级单例确保多个组件同时挂载时只启动一个轮询定时器，
 * 在所有使用者卸载后才停止。
 *
 * @example
 * ```ts
 * const { activeTasks, runningCount, totalActive, startPolling, stopPolling } = useActiveTasks()
 * onMounted(startPolling)
 * onUnmounted(stopPolling)
 * ```
 */
import { ref, computed } from "vue";
import { api, type UnifiedTaskItem } from "@/api/client";

// ── 模块级单例状态 ──

const activeTasks = ref<UnifiedTaskItem[]>([]);
const runningCount = ref(0);
const pendingCount = ref(0);

const totalActive = computed(() => runningCount.value + pendingCount.value);

let pollTimer: ReturnType<typeof setInterval> | null = null;
let subscriberCount = 0;

async function fetchActiveTasks() {
  try {
    const { data } = await api.getUnifiedTasks({ status: "running,pending", limit: 5 });
    activeTasks.value = data.tasks || [];
    runningCount.value = data.running_count ?? 0;
    pendingCount.value = data.pending_count ?? 0;
  } catch {
    // 静默失败 — 下次轮询会重试
  }
}

// ── 导出 composable ──

export function useActiveTasks() {
  function startPolling(interval = 5000) {
    subscriberCount++;
    if (pollTimer) return; // 已有定时器，仅递增计数
    fetchActiveTasks();
    pollTimer = setInterval(fetchActiveTasks, interval);
  }

  function stopPolling() {
    subscriberCount = Math.max(0, subscriberCount - 1);
    if (subscriberCount === 0 && pollTimer) {
      clearInterval(pollTimer);
      pollTimer = null;
    }
  }

  return {
    /** 当前活跃任务列表（最多 5 条） */
    activeTasks,
    /** 运行中任务数 */
    runningCount,
    /** 排队中任务数 */
    pendingCount,
    /** 活跃任务总数 */
    totalActive,
    /** 开始轮询（引用计数安全，可被多个组件同时调用） */
    startPolling,
    /** 停止轮询（仅在所有调用者都停止后才真正清除定时器） */
    stopPolling,
    /** 立即手动刷新 */
    fetchActiveTasks,
  };
}
