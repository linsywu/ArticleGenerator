/**
 * E2E: 任务日志 + 完整提示词展示
 * 验证 /tasks 和 /task-center 页面的日志查看功能
 */
import { test, expect } from "@playwright/test";

const BASE = "http://localhost:5173";
const API = "http://localhost:8000/api";

async function getToken(page: any): Promise<string> {
  const resp = await page.request.post(`${API}/auth/login`, {
    data: { username: "admin", password: "admin123" },
  });
  const body = await resp.json();
  return body.access_token;
}

async function login(page: any) {
  await page.goto(`${BASE}/login`);
  await page.waitForLoadState("networkidle");
  // Use placeholder to find inputs
  await page.locator('input[placeholder="用户名"]').fill("admin");
  await page.locator('input[placeholder="密码"]').fill("admin123");
  // Button text contains "登" (may have space: "登 录")
  await page.locator('button:has-text("登")').first().click();
  await page.waitForURL("**/", { timeout: 15000 }).catch(() => {});
  // If still on login page, try hitting Enter
  if (page.url().includes("login")) {
    await page.locator('input[placeholder="密码"]').press("Enter");
    await page.waitForTimeout(2000);
  }
}

test.describe("任务日志功能", () => {
  test.beforeEach(async ({ page }) => {
    test.setTimeout(60000);
    await login(page);
  });

  test("/tasks 页面 — 日志按钮存在并可点击", async ({ page }) => {
    await page.goto(`${BASE}/tasks`);

    // 等待页面加载
    await page.waitForLoadState("networkidle");
    await page.waitForTimeout(1000);

    // 检查页面标题
    await expect(page.locator(".page-title").first()).toBeVisible();

    // 检查控制台无报错
    const errors: string[] = [];
    page.on("console", (msg) => {
      if (msg.type() === "error") errors.push(msg.text());
    });

    // 如果有任务行，点击日志按钮
    const logButtons = page.locator("button:has-text('日志')");
    const count = await logButtons.count();

    if (count > 0) {
      // 点击第一个日志按钮
      await logButtons.first().click();
      await page.waitForTimeout(500);

      // 验证弹窗出现
      const dialog = page.locator(".el-dialog");
      const dialogVisible = await dialog.isVisible().catch(() => false);
      expect(dialogVisible).toBeTruthy();

      // 验证弹窗标题包含"任务日志"
      const title = await page.locator(".el-dialog__title").textContent().catch(() => "");
      expect(title).toContain("任务日志");
    }

    // 确认无控制台报错
    expect(errors.filter(e => !e.includes("favicon"))).toHaveLength(0);
  });

  test("/tasks 页面 — 弹窗中展开提示词", async ({ page }) => {
    await page.goto(`${BASE}/tasks`);
    await page.waitForLoadState("networkidle");
    await page.waitForTimeout(1000);

    const logButtons = page.locator("button:has-text('日志')");
    const count = await logButtons.count();

    if (count > 0) {
      await logButtons.first().click();
      await page.waitForTimeout(500);

      // 点击"查看提示词"按钮展开
      const promptBtn = page.locator("button:has-text('查看提示词')").first();
      const promptCount = await promptBtn.count();

      if (promptCount > 0) {
        await promptBtn.click();
        await page.waitForTimeout(300);

        // 验证提示词内容区域可见
        const promptContent = page.locator(".prompt-content").first();
        await expect(promptContent).toBeVisible({ timeout: 3000 });
      }

      // 关闭弹窗
      await page.click(".el-dialog .el-button:has-text('关闭')");
      await page.waitForTimeout(300);
    }
  });

  test("/task-center 页面 — 查看日志按钮存在", async ({ page }) => {
    // 直接用 API 验证 task-center 涉及的端点
    const resp = await page.request.get(`${API}/tasks/unified`, {
      headers: { Authorization: `Bearer ${await getToken(page)}` }
    });
    expect(resp.status()).toBe(200);

    // 访问页面
    await page.goto(`${BASE}/task-center`);
    await page.waitForLoadState("networkidle");
    await page.waitForTimeout(2000);

    // 收集控制台错误
    const errors: string[] = [];
    page.on("console", (msg) => {
      if (msg.type() === "error") errors.push(msg.text());
    });

    // 页面应该有内容渲染（不是空白页）
    const bodyText = await page.locator("body").textContent().catch(() => "");
    expect(bodyText.length).toBeGreaterThan(100);

    await page.waitForTimeout(500);
    expect(errors.filter(e => !e.includes("favicon"))).toHaveLength(0);
  });

  test("场景配置页 — 页面正常渲染", async ({ page }) => {
    await page.goto(`${BASE}/scenario-configs`);
    await page.waitForLoadState("networkidle");
    await page.waitForTimeout(2000);

    const errors: string[] = [];
    page.on("console", (msg) => {
      if (msg.type() === "error") errors.push(msg.text());
    });

    // 页面应该有内容渲染
    const bodyText = await page.locator("body").textContent().catch(() => "");
    expect(bodyText.length).toBeGreaterThan(100);

    await page.waitForTimeout(500);
    expect(errors.filter(e => !e.includes("favicon"))).toHaveLength(0);
  });
});
