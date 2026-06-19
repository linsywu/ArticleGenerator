const { chromium } = require("playwright");

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();
  const errors = [];

  page.on("console", (msg) => {
    if (msg.type() === "error") errors.push(msg.text());
  });
  page.on("pageerror", (err) => errors.push(err.message));

  // 1. Visit root without token → should redirect to /login
  await page.goto("http://localhost:5174/", { waitUntil: "networkidle", timeout: 15000 });
  await page.waitForTimeout(1000);
  const url1 = page.url();
  console.log("Step 1 - Root redirect:", url1.includes("/login") ? "✅ Redirected to /login" : "❌ URL: " + url1);

  // 2. Check login page renders (standalone — no sidebar, login panel visible)
  const loginPanel = await page.$(".login-panel");
  const sidebar = await page.$(".sidebar");
  console.log("Step 2 - Login panel:", loginPanel ? "✅ Found" : "❌ Missing");
  console.log("Step 2 - No sidebar:", !sidebar ? "✅ Standalone (no sidebar)" : "❌ Sidebar present");

  // 3. Check brand elements
  const brandMark = await page.textContent(".brand-mark");
  console.log("Step 3 - Brand mark:", brandMark === "墨" ? "✅ 墨" : "❌ " + brandMark);

  // 4. Login
  await page.fill('input[placeholder="用户名"]', "admin");
  await page.fill('input[placeholder="密码"]', "admin123");
  await page.click(".login-btn");
  await page.waitForTimeout(2000);

  const urlAfterLogin = page.url();
  console.log("Step 4 - After login:", urlAfterLogin.includes("/create") ? "✅ Redirected to /create" : "❌ URL: " + urlAfterLogin);

  // 5. After login, sidebar should be visible
  const sidebarAfter = await page.$(".sidebar");
  console.log("Step 5 - Sidebar:", sidebarAfter ? "✅ Present" : "❌ Missing");

  // 6. Navigate to /review via sidebar
  await page.click('a[href="/review"]');
  await page.waitForTimeout(500);
  console.log("Step 6 - Review page:", page.url().includes("/review") ? "✅" : "❌ URL: " + page.url());

  // Summary
  console.log("");
  console.log("Console errors:", errors.length > 0 ? errors.join("; ") : "None ✅");

  await browser.close();
})().catch((e) => {
  console.error("FATAL:", e.message);
  process.exit(1);
});
