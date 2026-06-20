---
name: verifier-playwright
description: Run Playwright browser E2E tests with console error detection and auto-fix loop. Self-gating: skips if no playwright.config.* found.
---

# Verifier: Playwright Browser Tests

Runs Playwright E2E tests against the running frontend, capturing browser console errors and verifying UI interactions.

## Gate

```bash
ls playwright.config.* 2>/dev/null && echo "found"
```
No config → `SKIP: no playwright.config.* found`. Not FAIL.

## Action

```bash
npx playwright install chromium 2>/dev/null
npx playwright test --reporter=line 2>&1
```

## Auto-Fix Loop

Console errors or test failures → fix BUSINESS CODE (not tests) → re-run → repeat (max 3 iterations).

## Output

```
┌──────────────────────────────────────┐
│  verifier-playwright Results          │
│  tracks.spec.ts: 5/5 passed           │
│  Console errors: 0                    │
│  Auto-fix iterations: 0               │
│  Status: PASS                         │
└──────────────────────────────────────┘
```

## Rules
- Tests immutable (pre-written during writing-plans)
- Console must be clean (0 errors)
- Auto-fix max 3 iterations before reporting FAIL
- No playwright config → SKIP
