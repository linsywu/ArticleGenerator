# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: task-logs.spec.ts >> 任务日志功能 >> /task-center 页面 — 查看日志按钮存在
- Location: e2e/task-logs.spec.ts:110:3

# Error details

```
Error: expect(received).toBeGreaterThan(expected)

Expected: > 100
Received:   15
```

# Test source

```ts
  30  |     await page.waitForTimeout(2000);
  31  |   }
  32  | }
  33  | 
  34  | test.describe("任务日志功能", () => {
  35  |   test.beforeEach(async ({ page }) => {
  36  |     test.setTimeout(60000);
  37  |     await login(page);
  38  |   });
  39  | 
  40  |   test("/tasks 页面 — 日志按钮存在并可点击", async ({ page }) => {
  41  |     await page.goto(`${BASE}/tasks`);
  42  | 
  43  |     // 等待页面加载
  44  |     await page.waitForLoadState("networkidle");
  45  |     await page.waitForTimeout(1000);
  46  | 
  47  |     // 检查页面标题
  48  |     await expect(page.locator(".page-title").first()).toBeVisible();
  49  | 
  50  |     // 检查控制台无报错
  51  |     const errors: string[] = [];
  52  |     page.on("console", (msg) => {
  53  |       if (msg.type() === "error") errors.push(msg.text());
  54  |     });
  55  | 
  56  |     // 如果有任务行，点击日志按钮
  57  |     const logButtons = page.locator("button:has-text('日志')");
  58  |     const count = await logButtons.count();
  59  | 
  60  |     if (count > 0) {
  61  |       // 点击第一个日志按钮
  62  |       await logButtons.first().click();
  63  |       await page.waitForTimeout(500);
  64  | 
  65  |       // 验证弹窗出现
  66  |       const dialog = page.locator(".el-dialog");
  67  |       const dialogVisible = await dialog.isVisible().catch(() => false);
  68  |       expect(dialogVisible).toBeTruthy();
  69  | 
  70  |       // 验证弹窗标题包含"任务日志"
  71  |       const title = await page.locator(".el-dialog__title").textContent().catch(() => "");
  72  |       expect(title).toContain("任务日志");
  73  |     }
  74  | 
  75  |     // 确认无控制台报错
  76  |     expect(errors.filter(e => !e.includes("favicon"))).toHaveLength(0);
  77  |   });
  78  | 
  79  |   test("/tasks 页面 — 弹窗中展开提示词", async ({ page }) => {
  80  |     await page.goto(`${BASE}/tasks`);
  81  |     await page.waitForLoadState("networkidle");
  82  |     await page.waitForTimeout(1000);
  83  | 
  84  |     const logButtons = page.locator("button:has-text('日志')");
  85  |     const count = await logButtons.count();
  86  | 
  87  |     if (count > 0) {
  88  |       await logButtons.first().click();
  89  |       await page.waitForTimeout(500);
  90  | 
  91  |       // 点击"查看提示词"按钮展开
  92  |       const promptBtn = page.locator("button:has-text('查看提示词')").first();
  93  |       const promptCount = await promptBtn.count();
  94  | 
  95  |       if (promptCount > 0) {
  96  |         await promptBtn.click();
  97  |         await page.waitForTimeout(300);
  98  | 
  99  |         // 验证提示词内容区域可见
  100 |         const promptContent = page.locator(".prompt-content").first();
  101 |         await expect(promptContent).toBeVisible({ timeout: 3000 });
  102 |       }
  103 | 
  104 |       // 关闭弹窗
  105 |       await page.click(".el-dialog .el-button:has-text('关闭')");
  106 |       await page.waitForTimeout(300);
  107 |     }
  108 |   });
  109 | 
  110 |   test("/task-center 页面 — 查看日志按钮存在", async ({ page }) => {
  111 |     // 直接用 API 验证 task-center 涉及的端点
  112 |     const resp = await page.request.get(`${API}/tasks/unified`, {
  113 |       headers: { Authorization: `Bearer ${await getToken(page)}` }
  114 |     });
  115 |     expect(resp.status()).toBe(200);
  116 | 
  117 |     // 访问页面
  118 |     await page.goto(`${BASE}/task-center`);
  119 |     await page.waitForLoadState("networkidle");
  120 |     await page.waitForTimeout(2000);
  121 | 
  122 |     // 收集控制台错误
  123 |     const errors: string[] = [];
  124 |     page.on("console", (msg) => {
  125 |       if (msg.type() === "error") errors.push(msg.text());
  126 |     });
  127 | 
  128 |     // 页面应该有内容渲染（不是空白页）
  129 |     const bodyText = await page.locator("body").textContent().catch(() => "");
> 130 |     expect(bodyText.length).toBeGreaterThan(100);
      |                             ^ Error: expect(received).toBeGreaterThan(expected)
  131 | 
  132 |     await page.waitForTimeout(500);
  133 |     expect(errors.filter(e => !e.includes("favicon"))).toHaveLength(0);
  134 |   });
  135 | 
  136 |   test("场景配置页 — 页面正常渲染", async ({ page }) => {
  137 |     await page.goto(`${BASE}/scenario-configs`);
  138 |     await page.waitForLoadState("networkidle");
  139 |     await page.waitForTimeout(2000);
  140 | 
  141 |     const errors: string[] = [];
  142 |     page.on("console", (msg) => {
  143 |       if (msg.type() === "error") errors.push(msg.text());
  144 |     });
  145 | 
  146 |     // 页面应该有内容渲染
  147 |     const bodyText = await page.locator("body").textContent().catch(() => "");
  148 |     expect(bodyText.length).toBeGreaterThan(100);
  149 | 
  150 |     await page.waitForTimeout(500);
  151 |     expect(errors.filter(e => !e.includes("favicon"))).toHaveLength(0);
  152 |   });
  153 | });
  154 | 
```