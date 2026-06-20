---
name: verifier-coverage
description: Check that every API endpoint and frontend page has at least one E2E test. Self-gating: reads writing-plans output to determine expected coverage.
---

# Verifier: Test Coverage Checker

Ensures every API endpoint and frontend page defined in the implementation plan has corresponding E2E tests. Part of the `verifier-*` family.

## Gate

Check for plan and test files:

```bash
ls docs/superpowers/plans/*.md 2>/dev/null && echo "plan_found"
ls e2e_test.py 2>/dev/null && echo "e2e_found"
```

- No plan file → `SKIP: no implementation plan to check coverage against`
- Plan found → Proceed

## Action

### 1. Extract expected coverage from plan

Read the most recent plan file in `docs/superpowers/plans/`. Extract:
- All API endpoint paths (GET /api/tracks, POST /api/tracks, etc.)
- All frontend page routes (/tracks, /mp-accounts, etc.)

### 2. Check API test coverage

Scan `e2e_test.py` for each expected endpoint:
```bash
grep -c "/api/tracks" e2e_test.py
```

### 3. Check frontend test coverage

Scan `e2e/*.spec.ts` files for each expected page route.

### 4. Report gaps

List any endpoint or page WITHOUT a corresponding test.

## Output

```
┌──────────────────────────────────────┐
│  verifier-coverage Results           │
├──────────────────────────────────────┤
│  API endpoints:  18 expected          │
│  API tested:     18/18 (100%)         │
│  Frontend pages: 5 expected           │
│  Frontend tested: 3/5 (60%)           │
│                                       │
│  ⚠️  Gaps:                             │
│     - /materials (no E2E spec)        │
│     - /collect-logs (no E2E spec)     │
├──────────────────────────────────────┤
│  Status: WARNING (frontend gaps)      │
└──────────────────────────────────────┘
```

## Rules
- Coverage < 80% → WARNING (advisory, not blocking)
- Coverage < 50% → FAIL (blocking — must add tests)
- Each endpoint needs at least 1 test (happy path minimum)
- Each page needs at least 1 test (load + no console error)
