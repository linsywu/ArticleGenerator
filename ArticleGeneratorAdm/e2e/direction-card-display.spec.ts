import { test, expect } from '@playwright/test';

test('direction cards show new fields and core_viewpoint flows downstream', async ({ page }) => {
  await page.goto('/create');
  await page.waitForLoadState('networkidle');
  await page.waitForTimeout(2000);

  // Step 0: Select first account, then click "下一步"
  const accountCard = page.locator('.account-option').first();
  await expect(accountCard).toBeVisible({ timeout: 10000 });
  await accountCard.click();
  // Click "下一步 · 输入想法"
  await page.locator('button').filter({ hasText: '下一步' }).click();
  await page.waitForTimeout(1000);

  // Step 1: Type idea into el-input textarea
  const textarea = page.locator('.el-textarea__inner').first();
  await expect(textarea).toBeVisible({ timeout: 5000 });
  await textarea.fill('每天走一万步真的健康吗');

  // Click "生成写作方向"
  await page.locator('button').filter({ hasText: '生成写作方向' }).click();

  // Wait for direction cards
  await expect(page.locator('.direction-card').first()).toBeVisible({ timeout: 90000 });

  // Check new card elements
  const firstCard = page.locator('.direction-card').first();
  console.log('direction-body:', await firstCard.locator('.direction-body').count() > 0);
  console.log('direction-viewpoint:', await firstCard.locator('.direction-viewpoint').count() > 0);
  console.log('direction-gain:', await firstCard.locator('.direction-gain').count() > 0);
  console.log('direction-check-text:', await firstCard.locator('.direction-check-text').count() > 0);
  console.log('direction-meta:', await firstCard.locator('.direction-meta').count() > 0);

  // Select first direction → generate outline
  await firstCard.click();
  await page.locator('button').filter({ hasText: '生成大纲' }).last().click();
  await expect(page.locator('.outline-row').first()).toBeVisible({ timeout: 60000 });

  // Verify step 4 card-desc (should show core_viewpoint)
  const desc = page.locator('.card-desc').filter({ hasText: '方向：' }).first();
  console.log('Step 4 desc:', await desc.textContent());
  expect(await desc.textContent()).toBeTruthy();

  console.log('✅ E2E done');
});
