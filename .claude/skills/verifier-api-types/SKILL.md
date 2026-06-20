---
name: verifier-api-types
description: Check backend API response types match frontend TypeScript type definitions. Self-gating: requires running backend + frontend types file.
---

# Verifier: API Type Consistency

Compares backend `/openapi.json` response schemas with frontend TypeScript type definitions to catch field mismatches. Part of the `verifier-*` family.

## Gate

```bash
# Check backend has OpenAPI
curl -s http://localhost:8001/openapi.json | python3 -c "import sys,json; json.load(sys.stdin); print('ok')" 2>/dev/null

# Check frontend types exist
ls src/api/types.ts 2>/dev/null
```

- Backend not running → `SKIP: backend not available`
- No types.ts → `SKIP: no frontend type definitions`

## Action

### 1. Fetch backend response schemas

```python
import requests, json
spec = requests.get("http://localhost:8001/openapi.json").json()

# Extract response schemas from /api/ paths
for path, methods in spec["paths"].items():
    if path.startswith("/api/"):
        for method, details in methods.items():
            responses = details.get("responses", {})
            schema_200 = responses.get("200", {}).get("content", {}).get("application/json", {}).get("schema", {})
```

### 2. Parse frontend TypeScript types

Scan `src/api/types.ts` for interfaces that match API response shapes.

### 3. Compare field names

For each API endpoint response schema, check that the corresponding TypeScript interface has matching field names (ignoring case).

## Output

```
┌──────────────────────────────────────┐
│  verifier-api-types Results           │
├──────────────────────────────────────┤
│  Endpoints checked: 18                │
│  Types matched:     15/18 (83%)       │
│                                       │
│  ⚠️  Mismatches:                       │
│     /api/materials response:          │
│       Backend: content_markdown       │
│       Frontend: contentMarkdown ❌     │
│     /api/collect-logs response:       │
│       Backend: task_name              │
│       Frontend: missing ❌            │
├──────────────────────────────────────┤
│  Status: WARNING (3 mismatches)       │
└──────────────────────────────────────┘
```

## Rules
- Exact field name match → PASS for that endpoint
- Case difference → WARNING (JS is case-sensitive)
- Missing field in frontend → WARNING (silently undefined)
- Extra field in frontend → OK (not used yet)
- No types found for endpoint → WARNING
