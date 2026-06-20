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

### If spec files exist in e2e/

```bash
npx playwright install chromium 2>/dev/null
npx playwright test --reporter=line 2>&1
```

### If NO spec files exist — Smoke Test Fallback

When `e2e/` has no `*.spec.ts` files, run a minimal smoke test:

```bash
# 1. Start dev server
npm run dev &
sleep 3

# 2. Login via curl to get auth token
TOKEN=$(curl -s -X POST http://localhost:8001/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

# 3. Check backend health
curl -s http://localhost:8001/api/health | python3 -c "import sys,json; assert json.load(sys.stdin)['status']=='ok'"

# 4. Check all frontend routes return 200 (not error page)
for route in / /login /create /review /publish /accounts /inspiration \
  /tasks /hotspot-sources /providers /scenario-configs /tasks-center \
  /tracks /mp-accounts /credentials /collect-tasks /materials; do
  STATUS=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:5173$route")
  echo "$route → $STATUS"
done

# 5. Check frontend build for type errors
npx vite build 2>&1 | tail -3
```

### Report

```
┌──────────────────────────────────────┐
│  verifier-playwright Results          │
│  Mode: SMOKE TEST (no spec files)    │
│  Routes checked: 17                   │
│  Routes 200:      17/17               │
│  Backend health:  OK                  │
│  Frontend build:  OK (no errors)      │
│  Console errors:  N/A (smoke only)    │
├──────────────────────────────────────┤
│  Status: PASS (smoke)                 │
└──────────────────────────────────────┘
```

Any route returning non-200 → FAIL with details.

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
