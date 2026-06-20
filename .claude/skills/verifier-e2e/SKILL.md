---
name: verifier-e2e
description: Run API + DB integration tests (Python requests + sqlite3 verification). Use as part of devflow verify stage. Self-gating: skips if no e2e_test.py or e2e/ directory.
---

# Verifier: API + DB Integration Tests

Runs pre-written E2E test scripts that verify API endpoints return correct responses AND data is correctly persisted to the database. Part of the `verifier-*` family.

## Gate

Check for test files:

```bash
ls e2e_test.py 2>/dev/null && echo "found"
ls e2e/*.py 2>/dev/null && echo "found_dir"
```

- **No test files found** → Report `SKIP: no E2E test scripts found` and exit cleanly
- **Test files found** → Proceed

## Action

Start backend server, run tests, verify DB:

```bash
# 1. Start backend (if not running)
python -m uvicorn app.main:app --host 127.0.0.1 --port 8001 &
sleep 4

# 2. Run E2E test script
python3 e2e_test.py

# 3. Each test in the script must:
#    - Call an API endpoint (requests.get/post/put/delete)
#    - Verify HTTP status code
#    - Verify response body structure
#    - Query database directly (sqlite3) to verify data was written correctly
```

## Output Format

After running, report:

```
┌──────────────────────────────────────┐
│  verifier-e2e Results                │
├──────────────────────────────────────┤
│  Track CRUD: 12/12 passed            │
│  MP Account CRUD: 6/6 passed         │
│  Credential CRUD: 6/6 passed         │
│  Collection Task CRUD: 6/6 passed    │
│  Materials + Logs: 6/6 passed        │
│  Input Validation: 5/5 passed        │
│  Cross-Module: 3/3 passed            │
│  DB Verification: 17/17 passed       │
├──────────────────────────────────────┤
│  Total: 77/77 passed                 │
│  Status: PASS                        │
└──────────────────────────────────────┘
```

## If Failures Found

- List each failing test: test name + assertion error
- Do NOT modify the test script — it was pre-written during writing-plans
- Fix the business code, then re-run
- Loop until all pass or failures are acknowledged as pre-existing

## Rules

- **Test scripts are immutable**: Generated during writing-plans, executed during verify. Never modified.
- **DB verification is mandatory**: Every write operation must have a corresponding DB read check
- **Expected skips are OK**: Tests requiring external services (Celery/Redis) can be marked `skip` if documented why
- **Full coverage required**: All API modules listed in the plan must have corresponding E2E tests
