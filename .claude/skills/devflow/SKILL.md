---
name: devflow
description: Use when the user types "/devflow", "devflow", "start dev flow", "启动开发流程", or wants to initiate a structured development workflow. Also triggered by "/devflow init" for one-time dependency setup. Do NOT auto-trigger on development requests — this skill requires explicit manual invocation.
---

# DevFlow Router

Development workflow router. Presents 5 complexity-based tracks on `/devflow`, orchestrates them stage-by-stage with checkpoints. Run `/devflow init` once after installation.

## `/devflow init` — One-Time Setup

Run once after installing devflow. Scans dependencies once, writes result to `.claude/skills/devflow/.initialized`.

### Detection

| Dependency | Check Method |
|------------|-------------|
| `superpowers:*` (7 skills) | Available skill list in system prompt |
| `openspec-propose` | `.claude/skills/openspec-propose/SKILL.md` exists |
| `openspec-archive-change` | `.claude/skills/openspec-archive-change/SKILL.md` exists |
| `openspec-explore` | `.claude/skills/openspec-explore/SKILL.md` exists |
| `grill-with-docs` | `.claude/skills/grill-with-docs/SKILL.md` exists |
| `claude-memory:extract-learnings` | Available skill list in system prompt |
| `verifier-*` skills | Scan `.claude/skills/` for skills matching `verifier-*` |
| `verify` | Built-in, always available |
| `visual-design` (Pencil MCP) | Optional, skip if not configured |

### Steps

1. Announce "Scanning DevFlow dependencies..."
2. Check each dependency. Present results:

```
┌─────────────────────────────────────────┐
│           DevFlow Dependency Scan        │
├─────────────────────────────────────────┤
│  ✅ superpowers (7 skills)              │
│  ✅ openspec-propose                    │
│  ✅ openspec-archive-change             │
│  ✅ openspec-explore                    │
│  ✅ grill-with-docs                     │
│  ✅ claude-memory:extract-learnings     │
│  ✅ verify (built-in)                   │
│  ⚠️  visual-design: not configured      │
├─────────────────────────────────────────┤
│  Status: All required deps ready. ✓     │
└─────────────────────────────────────────┘
```

3. If **required** dependencies missing, show install commands and offer [Install Missing] or [Skip]. Skipped deps → affected tracks greyed out in router.

4. On success, write `.claude/skills/devflow/.initialized`:

```json
{
  "initialized_at": "<ISO timestamp>",
  "dependencies": {
    "superpowers": "ok",
    "openspec-propose": "ok",
    "openspec-archive-change": "ok",
    "openspec-explore": "ok",
    "grill-with-docs": "ok",
    "claude-memory": "ok",
    "verify": "ok",
    "visual-design": "skipped"
  },
  "verifier_skills": ["verifier-unit", "verifier-e2e"],
  "available_tracks": ["full-flow","plan-grill-dev","plan-dev","quick-fix","explore-only"]
}
```

5. Announce "DevFlow initialized. Use `/devflow` to start."

## `/devflow` — Router Menu

### Gate

If `.initialized` missing → "DevFlow not initialized. Run `/devflow init` first." Stop.

If `.initialized` present → read `available_tracks`, show menu. Unavailable tracks greyed out.

### Menu

Use **AskUserQuestion** to present:

```
🔄 Full Flow (13 steps)
   大需求：多模块、架构变更、需求模糊

📋 Plan → Grill → Dev (10 steps)
   需求大致清晰但需要文档对照验证

📝 Plan → Dev (8 steps)
   需求明确，直接计划并执行

🔧 Quick Fix (4 steps)
   Bug 修复、小改动、单文件变更

🔍 Explore Only (1 step)
   只调研理解代码，不写代码
```

## Track Definitions

### 🔄 Full Flow

| # | Stage | Skill |
|---|-------|-------|
| 1 | brainstorming | `superpowers:brainstorming` |
| 2 | opsx:propose | `openspec-propose` |
| 3 | writing-plans | `superpowers:writing-plans` |
| 4* | visual-design | Pencil MCP (ask first: "UI work?" — if no, skip) |
| 5 | grill-with-docs | `grill-with-docs` |
| 6 | using-git-worktrees | `superpowers:using-git-worktrees` |
| 7 | subagent-driven-dev | `superpowers:subagent-driven-development` |
| 8 | requesting-code-review | `superpowers:requesting-code-review` → **auto-pause for human review** |
| 9 | receiving-code-review | `superpowers:receiving-code-review` |
| 10 | verify | `verify` |
| 11 | finish-branch | `superpowers:finishing-a-development-branch` |
| 12 | opsx:archive | `openspec-archive-change` |
| 13 | capture-knowledge | Ask user: "Record learnings?" → if yes, `claude-memory:extract-learnings` |

### 📋 Plan → Grill → Dev

| # | Stage | Skill |
|---|-------|-------|
| 1 | opsx:propose | `openspec-propose` |
| 2 | writing-plans | `superpowers:writing-plans` |
| 3* | visual-design | Pencil MCP (ask: "UI work?" → no = skip) |
| 4 | grill-with-docs | `grill-with-docs` |
| 5 | using-git-worktrees | `superpowers:using-git-worktrees` |
| 6 | subagent-driven-dev | `superpowers:subagent-driven-development` |
| 7 | requesting-code-review | `superpowers:requesting-code-review` → **auto-pause** |
| 8 | receiving-code-review | `superpowers:receiving-code-review` |
| 9 | verify + finish | `verify` → `superpowers:finishing-a-development-branch` |
| 10 | opsx:archive | `openspec-archive-change` |

### 📝 Plan → Dev

| # | Stage | Skill |
|---|-------|-------|
| 1 | opsx:propose | `openspec-propose` |
| 2 | writing-plans | `superpowers:writing-plans` |
| 3* | visual-design | Pencil MCP (ask: "UI work?" → no = skip) |
| 4 | using-git-worktrees | `superpowers:using-git-worktrees` |
| 5 | subagent-driven-dev | `superpowers:subagent-driven-development` |
| 6 | requesting-code-review | `superpowers:requesting-code-review` |
| 7 | verify + finish | `verify` → `superpowers:finishing-a-development-branch` |
| 8 | opsx:archive | `openspec-archive-change` |

### 🔧 Quick Fix

| # | Stage | Skill |
|---|-------|-------|
| 1 | using-git-worktrees | `superpowers:using-git-worktrees` |
| 2 | tdd | `superpowers:test-driven-development` |
| 3 | verify | `verify` |
| 4 | finish-branch | `superpowers:finishing-a-development-branch` |

### 🔍 Explore Only

| # | Stage | Skill |
|---|-------|-------|
| 1 | opsx:explore | `openspec-explore` |

**Guardrails**: Read-only. Never write code. If user asks to implement → "Exit explore mode and pick a different track via `/devflow`."

## Verify Stage Enhancement

When `verify` stage activates, if `.initialized` has `verifier_skills`:

1. For each verifier-* skill in `verifier_skills` (ordered):
   - Invoke `Skill(skill="verifier-<name>")`
   - Collect result: PASS / FAIL / SKIP + details
2. Invoke built-in `verify` for browser/manual verification
3. Show summary:

```
┌──────────────────────────────────────┐
│        Verification Results          │
├──────────────────────────────────────┤
│  ✅ verifier-unit — 36/36 passed     │
│  ✅ verifier-e2e — 77/77 passed      │
│  ✅ verifier-coverage — 100% API     │
│  ⚠️  verifier-api-types — 3 warnings │
│  ⚠️  verifier-playwright — skipped   │
│  ✅ verify (browser) — pages render  │
├──────────────────────────────────────┤
│  Status: VERIFIED ✓                  │
└──────────────────────────────────────┘
```

4. If any FAIL: loop fix → re-run failed verifier → repeat until all PASS
5. If all PASS or SKIP: advance to next stage

**Gate behavior:** Each verifier skill self-gates (no config → SKIP, not FAIL). The verify stage never FAILs because a verifier skips — only if a verifier runs and finds real failures.

**Code-review → Verify linkage:** After `receiving-code-review` completes, the review findings are captured in `.claude/review-risks.md` (high-risk files, critical changes, areas needing extra scrutiny). The verify stage reads this file and ensures those risk areas receive focused test coverage. If a risk area fails verification, the fix loop prioritizes it.

**Writing-plans integration:** The `writing-plans` stage must also produce executable E2E test scripts (not just documentation). These scripts become the input to `verifier-e2e` and `verifier-playwright`. Tests are immutable after writing-plans — verify only executes, never modifies. Coverage requirement: every new API endpoint and frontend page must have at least one corresponding E2E test.

## Checkpoint Behavior

After EACH stage, show progress and ask:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔄 Full Flow  |  3/13 complete
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ brainstorming
✅ opsx:propose
✅ writing-plans
▶ Next: visual-design
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[Continue] [Skip] [Pause]
```

- **Continue**: invoke next skill
- **Skip**: mark stage skipped, advance (use for optional stages or judged-unnecessary)
- **Pause**: "Flow paused at Stage 3/13. Say 'continue devflow' to resume." Resume from context.

### Edge Cases

| Situation | Behavior |
|-----------|----------|
| Last stage complete | Announce "🎉 <Track> complete!" with summary |
| Stage errors out | Pause, report error, offer retry/skip/abort |
| visual-design not configured | Auto-skip with note |
| User interrupts mid-stage | Treat as pause, resume same stage |
| `requesting-code-review` | Auto-pause after skill completes. Wait for user to say "continue" (implies human review done) |

## Skill Reference

Invoke each stage's skill via `Skill(skill="<name>")`. Built-in skills (`verify`) invoked directly.

| Stage | Invocation |
|-------|-----------|
| brainstorming | `Skill(skill="superpowers:brainstorming")` |
| visual-design | Pencil MCP tools (pluggable) |
| opsx:propose | `Skill(skill="openspec-propose")` |
| writing-plans | `Skill(skill="superpowers:writing-plans")` |
| grill-with-docs | `Skill(skill="grill-with-docs")` |
| using-git-worktrees | `Skill(skill="superpowers:using-git-worktrees")` |
| subagent-driven-dev | `Skill(skill="superpowers:subagent-driven-development")` |
| requesting-code-review | `Skill(skill="superpowers:requesting-code-review")` |
| receiving-code-review | `Skill(skill="superpowers:receiving-code-review")` |
| tdd | `Skill(skill="superpowers:test-driven-development")` |
| verify | `Skill(skill="verify")` |
| verifier-unit | `Skill(skill="verifier-unit")` |
| verifier-e2e | `Skill(skill="verifier-e2e")` |
| verifier-playwright | `Skill(skill="verifier-playwright")` |
| verifier-coverage | `Skill(skill="verifier-coverage")` |
| verifier-api-types | `Skill(skill="verifier-api-types")` |
| finish-branch | `Skill(skill="superpowers:finishing-a-development-branch")` |
| opsx:archive | `Skill(skill="openspec-archive-change")` |
| capture-knowledge | `Skill(skill="claude-memory:extract-learnings")` |
| opsx:explore | `Skill(skill="openspec-explore")` |

## Common Mistakes

| Mistake | Reality |
|---------|---------|
| "I'll auto-detect complexity" | Never auto-trigger. `/devflow` is manual only. |
| "Skip init, just run /devflow" | Gate blocks it. Run init first. |
| "visual-design is required" | Always optional. Ask, skip if no UI. |
| "Run Full Flow for a typo fix" | Menu descriptions guide correct track. |
| "code-review stages can run back-to-back" | Requesting always pauses for human review. |
| "verify passed because tests weren't run" | All verifier-* skills must be invoked. No test = no pass. |
| "E2E tests can be modified to pass" | Tests written during writing-plans are immutable. Fix code, not tests. |

## Red Flags — STOP and Re-read This Skill

- User said "build X" and you're about to suggest a track unprompted
- You're about to skip the checkpoint and invoke the next skill
- You forgot to show the progress summary after a stage completed
- You're treating `capture-knowledge` as automatic instead of asking
- The `.initialized` file is missing but you proceed anyway

**All of these mean: Stop. Re-read the relevant section above.**
