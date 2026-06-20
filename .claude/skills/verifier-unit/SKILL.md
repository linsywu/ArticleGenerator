---
name: verifier-unit
description: Run project unit tests (pytest + vitest). Use as part of the devflow verify stage. Self-gating: skips if no test directories found.
---

# Verifier: Unit Tests

Runs project unit test suites and reports results. Part of the `verifier-*` family — automatically discovered by devflow.

## Gate

Before running, check if test infrastructure exists:

```bash
# Python project check
ls tests/ 2>/dev/null && echo "pytest"

# Node.js project check  
ls vitest.config.* 2>/dev/null && echo "vitest"
```

- **No test directories found** → Report `SKIP: no test infrastructure detected` and exit cleanly
- **Test dirs found** → Proceed

## Action

Run each detected test framework:

```bash
# Python
python -m pytest tests/ -v --tb=short -q 2>&1 | tail -20

# Node.js
npx vitest run 2>&1 | tail -20
```

## Output

After running, report structured results:

```
┌──────────────────────────────────────┐
│  verifier-unit Results               │
├──────────────────────────────────────┤
│  pytest: 36 passed, 0 failed         │
│  vitest: 12 passed, 0 failed         │
├──────────────────────────────────────┤
│  Status: PASS                        │
└──────────────────────────────────────┘
```

If failures found:
- List each failing test: file name + line + error message
- Status: FAIL
- Do NOT attempt to fix test files — they are pre-written and should not be modified

## Rules

- **Read-only**: Never modify test files. Report failures for manual fix or code fix.
- **Pre-existing failures**: Note them as pre-existing if they also fail on a clean checkout. Don't block on pre-existing issues.
- **Timeouts**: Use reasonable timeouts (pytest: 60s, vitest: 60s). Report timeout as FAIL.
