import { test as setup, expect } from '@playwright/test';

const authFile = 'e2e/.auth/user.json';

setup('authenticate via real login', async ({ page }) => {
  // 收集控制台错误用于调试
  const errors: string[] = [];
  page.on('pageerror', (err) => errors.push(err.message));

  // 1. 访问登录页
  await page.goto('/login');
  await expect(page.locator('input[placeholder*="用户名"]')).toBeVisible({ timeout: 10000 });

  // 2. 填写用户名密码
  await page.fill('input[placeholder*="用户名"]', 'admin');
  await page.fill('input[placeholder*="密码"]', 'admin123');

  // 3. 点击登录（el-button 渲染为 type="button"，通过文本定位）
  await page.click('button:has-text("登 录")');

  // 4. 等待跳转到 /create（登录成功后路由重定向）
  await page.waitForURL('**/create', { timeout: 15000 });

  // 5. 确认 token 已保存到 localStorage
  const token = await page.evaluate(() => localStorage.getItem('access_token'));
  expect(token).toBeTruthy();
  expect(token!.length).toBeGreaterThan(50);

  // 6. 持久化登录状态（cookies + localStorage）
  await page.context().storageState({ path: authFile });

  // 7. 不应有 JS 崩溃
  const crashErrors = errors.filter(
    (e) => e.includes('TypeError') || e.includes('ReferenceError') || e.includes('Cannot read')
  );
  expect(crashErrors).toEqual([]);
});
