/**
 * usePaginatedList — 通用分页列表 composable
 *
 * 封装了分页状态与加载逻辑，各视图只需传入 fetchFn 即可。
 *
 * @example
 * ```ts
 * const { data, total, page, pageSize, loading, load } = usePaginatedList(
 *   (page, pageSize) => api.getArticles({ status: "pending_review", page, page_size: pageSize })
 * )
 * ```
 */
import { ref } from "vue";

export interface PaginatedState<T> {
  data: T[];
  total: number;
  page: number;
  pageSize: number;
  loading: boolean;
  load: () => Promise<void>;
  reset: () => void;
}

export function usePaginatedList<T>(
  fetchFn: (page: number, pageSize: number) => Promise<{ data: T[]; total: number }>,
  initialPageSize = 20,
): PaginatedState<T> {
  const data = ref<T[]>([]) as ReturnType<typeof ref<T[]>>;
  const total = ref(0);
  const page = ref(1);
  const pageSize = ref(initialPageSize);
  const loading = ref(false);

  async function load() {
    loading.value = true;
    try {
      const result = await fetchFn(page.value, pageSize.value);
      data.value = result.data;
      total.value = result.total;
    } catch {
      // Caller is responsible for user-facing error handling
    } finally {
      loading.value = false;
    }
  }

  function reset() {
    page.value = 1;
    pageSize.value = initialPageSize;
    data.value = [];
    total.value = 0;
    load();
  }

  return { data, total, page, pageSize, loading, load, reset };
}
