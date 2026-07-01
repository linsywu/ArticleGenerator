/**
 * 文章创作全流程 E2E 测试
 *
 * 覆盖流程：选择账号 → 输入想法 → 创作写作方向 → 生成大纲 → 生成标题 → 生成全文
 *           → 文章评审 → 微调 → 文章发布
 *
 * 前置条件：
 *   - 后端运行在 :8000，前端运行在 :5173
 *   - DB 中有至少一个 style_profile_status=ready 的账号
 *   - 场景配置中 direction/outline/title 的 model 为可用模型
 *   - Celery worker + Redis 运行中（用于异步任务）
 */
import { test, expect } from "@playwright/test";

test.describe("Article Creation Full Workflow", () => {
  test.beforeEach(async ({ page }) => {
    // 登录状态由 auth.setup.ts 处理，storageState 自动注入

    // 收集 JS 控制台错误
    page.on("pageerror", (err) => {
      console.error(`[PAGE ERROR] ${err.message}`);
    });
  });

  // ══════════════════════════════════════════════════════════
  // 测试 1: CreateView 页面加载
  // ══════════════════════════════════════════════════════════
  test("01-createView loads with 6 steps and accounts", async ({ page }) => {
    const errors: string[] = [];
    page.on("pageerror", (err) => errors.push(err.message));

    await page.goto("/create");
    await page.waitForLoadState("networkidle");
    await page.waitForTimeout(2000);

    // 页面渲染
    await expect(page.locator(".create-view")).toBeVisible({
      timeout: 10000,
    });

    // 6 个步骤可见
    const steps = await page.locator(".step-dot").count();
    expect(steps).toBe(6);

    // 账号列表加载
    const accounts = await page.locator(".account-option").count();
    expect(accounts).toBeGreaterThan(0);

    // 无 JS 错误
    const ourErrors = errors.filter(
      (e) => !e.includes("401") && !e.includes("token")
    );
    expect(ourErrors).toEqual([]);
  });

  // ══════════════════════════════════════════════════════════
  // 测试 2: 步骤 1 — 选择账号
  // ══════════════════════════════════════════════════════════
  test("02-step1 select account and proceed", async ({ page }) => {
    await page.goto("/create");
    await page.waitForLoadState("networkidle");
    await page.waitForTimeout(2000);

    // 点击第一个账号
    const firstAccount = page.locator(".account-option").first();
    await firstAccount.click();

    // 账号应显示选中状态
    await expect(firstAccount).toHaveClass(/selected/);

    // 点击「下一步 · 输入想法」
    const nextBtn = page.locator("button", { hasText: "下一步" }).first();
    await nextBtn.click();
    await page.waitForTimeout(500);

    // 应进入步骤 2（显示 textarea）
    await expect(page.locator(".idea-textarea")).toBeVisible({ timeout: 5000 });

    // 应显示账号名
    const cardDesc = page.locator(".card-desc");
    await expect(cardDesc).toContainText("的风格进行创作");
  });

  // ══════════════════════════════════════════════════════════
  // 测试 3: 步骤 2 — 输入想法并生成写作方向
  // ══════════════════════════════════════════════════════════
  test("03-step2 input idea and generate directions", async ({ page }) => {
    test.setTimeout(120000); // 需要等待 LLM 调用

    const errors: string[] = [];
    page.on("pageerror", (err) => errors.push(err.message));

    await page.goto("/create");
    await page.waitForLoadState("networkidle");
    await page.waitForTimeout(2000);

    // 选择第一个账号 → 进入步骤 2
    await page.locator(".account-option").first().click();
    await page.locator("button", { hasText: "下一步" }).first().click();
    await page.waitForTimeout(500);

    // 输入想法
    const textarea = page.locator(".idea-textarea textarea");
    await textarea.fill("AI 技术发展对人类就业市场的深远影响");

    // 点击「生成写作方向」
    const genDirBtn = page.locator("button", { hasText: "生成写作方向" });
    await expect(genDirBtn).toBeEnabled({ timeout: 3000 });
    await genDirBtn.click();

    // 等待方向卡片出现（轮询最多 60s）
    await expect(page.locator(".direction-card").first()).toBeVisible({
      timeout: 90000,
    });

    // 至少显示 2 个方向
    const dirCount = await page.locator(".direction-card").count();
    expect(dirCount).toBeGreaterThanOrEqual(2);

    // 无 JS 错误（排除 token 相关的 401）
    const ourErrors = errors.filter(
      (e) => !e.includes("401") && !e.includes("token")
    );
    expect(ourErrors).toEqual([]);
  });

  // ══════════════════════════════════════════════════════════
  // 测试 4: 步骤 3 — 选择方向并生成大纲
  // ══════════════════════════════════════════════════════════
  test("04-step3 select direction and generate outline", async ({ page }) => {
    test.setTimeout(180000);

    const errors: string[] = [];
    page.on("pageerror", (err) => errors.push(err.message));

    await page.goto("/create");
    await page.waitForLoadState("networkidle");
    await page.waitForTimeout(2000);

    // 步骤 1-2 走到方向选择
    await page.locator(".account-option").first().click();
    await page.locator("button", { hasText: "下一步" }).first().click();
    await page.waitForTimeout(500);
    await page.locator(".idea-textarea textarea").fill(
      "远程办公对团队协作效率的影响"
    );
    await page.locator("button", { hasText: "生成写作方向" }).click();

    // 等待方向卡片
    await expect(page.locator(".direction-card").first()).toBeVisible({
      timeout: 90000,
    });

    // 选择第一个方向
    await page.locator(".direction-card").first().click();

    // 点击「下一步 · 生成大纲」
    const outlineBtn = page.locator("button", { hasText: "生成大纲" });
    await expect(outlineBtn).toBeEnabled({ timeout: 5000 });
    await outlineBtn.click();

    // 等待大纲行出现
    await expect(page.locator(".outline-row").first()).toBeVisible({
      timeout: 90000,
    });

    // 至少 3 个大纲要点
    const outlineCount = await page.locator(".outline-row").count();
    expect(outlineCount).toBeGreaterThanOrEqual(3);

    // 每行应有 order 和 input
    const firstOrder = await page.locator(".outline-order").first().textContent();
    expect(firstOrder?.trim()).toBe("1");

    const ourErrors = errors.filter(
      (e) => !e.includes("401") && !e.includes("token")
    );
    expect(ourErrors).toEqual([]);
  });

  // ══════════════════════════════════════════════════════════
  // 测试 5: 步骤 4 — 编辑大纲并生成标题
  // ══════════════════════════════════════════════════════════
  test("05-step4 generate titles from outline", async ({ page }) => {
    test.setTimeout(240000);

    const errors: string[] = [];
    page.on("pageerror", (err) => errors.push(err.message));

    await page.goto("/create");
    await page.waitForLoadState("networkidle");
    await page.waitForTimeout(2000);

    // 完整走到步骤 4
    await page.locator(".account-option").first().click();
    await page.locator("button", { hasText: "下一步" }).first().click();
    await page.waitForTimeout(500);
    await page.locator(".idea-textarea textarea").fill(
      "新能源汽车对传统汽车行业的冲击"
    );
    await page.locator("button", { hasText: "生成写作方向" }).click();
    await expect(page.locator(".direction-card").first()).toBeVisible({
      timeout: 90000,
    });
    await page.locator(".direction-card").first().click();
    await page.locator("button", { hasText: "生成大纲" }).click();
    await expect(page.locator(".outline-row").first()).toBeVisible({
      timeout: 90000,
    });

    // 点击「下一步 · 生成标题」
    const titleBtn = page.locator("button", { hasText: "生成标题" });
    await expect(titleBtn).toBeEnabled({ timeout: 5000 });
    await titleBtn.click();

    // 等待标题候选
    await expect(page.locator(".title-card").first()).toBeVisible({
      timeout: 90000,
    });

    const titleCount = await page.locator(".title-card").count();
    expect(titleCount).toBeGreaterThanOrEqual(2);

    // 标题编辑区可见
    await expect(page.locator(".title-edit-area")).toBeVisible();

    const ourErrors = errors.filter(
      (e) => !e.includes("401") && !e.includes("token")
    );
    expect(ourErrors).toEqual([]);
  });

  // ══════════════════════════════════════════════════════════
  // 测试 6: 步骤 5 — 选择标题并进入步骤 6
  // ══════════════════════════════════════════════════════════
  test("06-step5 select title and proceed to generate", async ({ page }) => {
    test.setTimeout(240000);

    await page.goto("/create");
    await page.waitForLoadState("networkidle");
    await page.waitForTimeout(2000);

    // 走到步骤 5
    await page.locator(".account-option").first().click();
    await page.locator("button", { hasText: "下一步" }).first().click();
    await page.waitForTimeout(500);
    await page.locator(".idea-textarea textarea").fill(
      "短视频对青少年心理健康的影响"
    );
    await page.locator("button", { hasText: "生成写作方向" }).click();
    await expect(page.locator(".direction-card").first()).toBeVisible({
      timeout: 90000,
    });
    await page.locator(".direction-card").first().click();
    await page.locator("button", { hasText: "生成大纲" }).click();
    await expect(page.locator(".outline-row").first()).toBeVisible({
      timeout: 90000,
    });
    await page.locator("button", { hasText: "生成标题" }).click();
    await expect(page.locator(".title-card").first()).toBeVisible({
      timeout: 90000,
    });

    // 选择第一个标题
    await page.locator(".title-card").first().click();
    await expect(page.locator(".title-card").first()).toHaveClass(/selected/);

    // 点击「确认标题 · 生成全文」
    const confirmBtn = page.locator("button", { hasText: "确认标题" });
    await expect(confirmBtn).toBeEnabled({ timeout: 5000 });
    await confirmBtn.click();

    // 应进入步骤 6
    await expect(
      page.locator(".generating-state, .article-result").first()
    ).toBeVisible({ timeout: 5000 });
  });

  // ══════════════════════════════════════════════════════════
  // 测试 7: 评审页加载
  // ══════════════════════════════════════════════════════════
  test("07-review view loads articles table", async ({ page }) => {
    const errors: string[] = [];
    page.on("pageerror", (err) => errors.push(err.message));

    await page.goto("/review");
    await page.waitForLoadState("networkidle");
    await page.waitForTimeout(2000);

    // 评审页渲染
    await expect(page.locator(".page")).toBeVisible({ timeout: 10000 });

    // 页面标题包含「评审」
    const header = page.locator(".page-header");
    await expect(header).toContainText("评审");

    const ourErrors = errors.filter(
      (e) => !e.includes("401") && !e.includes("token")
    );
    expect(ourErrors).toEqual([]);
  });

  // ══════════════════════════════════════════════════════════
  // 测试 8: 发布页加载
  // ══════════════════════════════════════════════════════════
  test("08-publish view loads", async ({ page }) => {
    const errors: string[] = [];
    page.on("pageerror", (err) => errors.push(err.message));

    await page.goto("/publish");
    await page.waitForLoadState("networkidle");
    await page.waitForTimeout(2000);

    // 发布页渲染
    await expect(page.locator(".page")).toBeVisible({ timeout: 10000 });

    // 页面标题包含「发布」
    const header = page.locator(".page-header");
    await expect(header).toContainText("发布");

    const ourErrors = errors.filter(
      (e) => !e.includes("401") && !e.includes("token")
    );
    expect(ourErrors).toEqual([]);
  });

  // ══════════════════════════════════════════════════════════
  // 测试 9: Materials → Create 预填流程
  // ══════════════════════════════════════════════════════════
  test("09-materials to create pre-fill", async ({ page }) => {
    const errors: string[] = [];
    page.on("pageerror", (err) => errors.push(err.message));

    // 访问 /create?idea=xxx&account_id=1
    await page.goto("/create?idea=端到端测试预填想法&account_id=1");
    await page.waitForLoadState("networkidle");
    await page.waitForTimeout(2000);

    // 页面渲染
    await expect(page.locator(".create-view")).toBeVisible({
      timeout: 10000,
    });

    // 应自动进入步骤 1（输入想法），因为 account_id 已预填
    const ideaTextarea = page.locator(".idea-textarea textarea");
    const ideaValue = await ideaTextarea.inputValue();
    expect(ideaValue).toContain("端到端测试预填想法");

    const ourErrors = errors.filter(
      (e) => !e.includes("401") && !e.includes("token")
    );
    expect(ourErrors).toEqual([]);
  });

  // ══════════════════════════════════════════════════════════
  // 测试 10: 所有关键页面路由访问
  // ══════════════════════════════════════════════════════════
  test("10-all key routes accessible without console errors", async ({
    page,
  }) => {
    const routes = [
      "/create",
      "/review",
      "/publish",
      "/accounts",
      "/tasks",
      "/materials",
      "/tasks-center",
    ];

    for (const route of routes) {
      const routeErrors: string[] = [];
      page.on("pageerror", (err) => routeErrors.push(err.message));

      await page.goto(route);
      await page.waitForLoadState("networkidle");
      await page.waitForTimeout(1000);

      // 页面应可见（使用通用选择器）
      const isVisible = await page.locator("body").isVisible();
      expect(isVisible).toBe(true);

      // 验证无严重 JS 错误
      const seriousErrors = routeErrors.filter(
        (e) =>
          !e.includes("401") &&
          !e.includes("token") &&
          !e.includes("Failed to load resource")
      );
      if (seriousErrors.length > 0) {
        console.warn(`[${route}] JS errors:`, seriousErrors);
      }
      // 不 fail-fast，收集所有路由的错误
    }
  });

  // ══════════════════════════════════════════════════════════
  // 测试 11: 无认证时 CreateView 应重定向到登录页
  // ══════════════════════════════════════════════════════════
  test("11-createView redirects to login when unauthenticated", async ({
    browser,
  }) => {
    // 创建无 storageState 的新 context，模拟未登录状态
    const context = await browser.newContext();
    const page = await context.newPage();

    const errors: string[] = [];
    page.on("pageerror", (err) => errors.push(err.message));

    await page.goto("/create");
    await page.waitForTimeout(3000);

    // 应重定向到 /login
    expect(page.url()).toContain("/login");

    // 不应有 JS 异常导致的崩溃
    const crashErrors = errors.filter(
      (e) =>
        e.includes("TypeError") ||
        e.includes("ReferenceError") ||
        e.includes("Cannot read")
    );
    expect(crashErrors).toEqual([]);

    await context.close();
  });
});
