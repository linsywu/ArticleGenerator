# Verification Plan

Project-specific verification scope for the devflow `verify` stage.

## Pre-requisites

- Backend dev server on port 5173 (or 8001 for API tests)
- SQLite dev database initialized
- Admin user seeded (admin / admin123)

## Verifier Skills

| Skill | Status | Notes |
|-------|--------|-------|
| verifier-unit | Active | pytest (36 tests) + vitest |
| verifier-e2e | Active | `ArticleGeneratorService/e2e_test.py` (77 tests) |
| verifier-playwright | Active | `ArticleGeneratorAdm/e2e/*.spec.ts` |

## E2E Test Files

### Backend (API + DB)
- `ArticleGeneratorService/e2e_test.py` — Full API endpoint coverage with sqlite3 DB verification
- Run: `python3 ArticleGeneratorService/e2e_test.py`
- Covers: Tracks, MP Accounts, Credentials, Collection Tasks, Materials, Collect Logs

### Frontend (Playwright)
- `ArticleGeneratorAdm/e2e/*.spec.ts` — Page interaction tests
- Run: `cd ArticleGeneratorAdm && npx playwright test`
- Covers: Login flow, page rendering, form submissions, console errors

## Verification Standards

- All API endpoints must return expected status codes
- Every write operation must verify DB persistence
- Playwright console must have 0 errors
- Tests are immutable during verify — fix code, not tests
