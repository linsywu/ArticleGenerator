/**
 * E2E 测试工具函数
 *
 * 提供 Celery 异步任务等待、API 调用、服务健康检查等辅助功能。
 * 所有 API 调用通过 localStorage 中的 access_token 认证。
 */
import type { Page, APIRequestContext } from "@playwright/test";

/**
 * 从 browser page 的 localStorage 获取 access_token，
 * 用于 API 请求认证。
 */
export async function getAuthToken(page: Page): Promise<string> {
  return await page.evaluate(() =>
    localStorage.getItem("access_token")
  ) as string;
}

/**
 * 轮询 Celery 任务状态直到完成或失败。
 *
 * @param api - Playwright APIRequestContext（通过 page.request 或直接创建）
 * @param taskId - Celery 任务 ID
 * @param backendUrl - 后端地址，默认 http://localhost:8000
 * @param timeoutMs - 最大等待时间（毫秒）
 * @param pollIntervalMs - 轮询间隔（毫秒）
 * @returns 任务最终状态 ("success" | "failed" | "cancelled" | "timeout")
 */
export async function waitForCeleryTask(
  api: APIRequestContext,
  taskId: string,
  backendUrl = "http://localhost:8000",
  timeoutMs = 120000,
  pollIntervalMs = 3000
): Promise<"success" | "failed" | "cancelled" | "timeout"> {
  const start = Date.now();

  while (Date.now() - start < timeoutMs) {
    try {
      const resp = await api.get(
        `${backendUrl}/api/generate/tasks/${taskId}`
      );
      if (resp.ok()) {
        const data = await resp.json();
        const status = data.status;
        if (status === "success") return "success";
        if (status === "failed") return "failed";
        if (status === "cancelled") return "cancelled";
      }
    } catch {
      // API 不可用，忽略继续重试
    }
    await new Promise((r) => setTimeout(r, pollIntervalMs));
  }

  return "timeout";
}

/**
 * 检查后端服务是否就绪。
 * 返回 true 表示 API 响应正常。
 */
export async function isBackendReady(
  api: APIRequestContext,
  backendUrl = "http://localhost:8000"
): Promise<boolean> {
  try {
    const resp = await api.get(`${backendUrl}/`);
    return resp.ok();
  } catch {
    return false;
  }
}

/**
 * 等待后端就绪，超时抛出错误。
 */
export async function waitForBackend(
  api: APIRequestContext,
  backendUrl = "http://localhost:8000",
  timeoutMs = 30000
): Promise<void> {
  const start = Date.now();
  while (Date.now() - start < timeoutMs) {
    if (await isBackendReady(api, backendUrl)) return;
    await new Promise((r) => setTimeout(r, 2000));
  }
  throw new Error(`Backend not ready after ${timeoutMs}ms`);
}

/**
 * 通过后端 API 获取一个 style_profile_status=ready 的账号 ID。
 * 用于确保测试有可用的蒸馏完成账号。
 */
export async function getReadyAccountId(
  api: APIRequestContext,
  backendUrl = "http://localhost:8000"
): Promise<number | null> {
  try {
    const resp = await api.get(`${backendUrl}/api/accounts`);
    if (!resp.ok()) return null;
    const accounts = await resp.json();
    const ready = accounts.find(
      (a: any) => a.style_profile_status === "ready"
    );
    return ready?.id ?? null;
  } catch {
    return null;
  }
}
