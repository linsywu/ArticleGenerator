## Context

ArticleGenerator is a multi-service system (backend FastAPI, frontend Vue 3, SQLite DB). Phase 1 completed the core pipeline: generate → humanize → quality_review → compliance_review → publish. Three scenarios are missing from seed data (humanize, direction, outline, title), two DB migrations are unapplied (articles.title, scenario_configs.description/sort_order), and several Pydantic/frontend types lag behind the actual DB schema. The unified task center exists but only covers generate/refine tasks.

**Current state**: The backend service is at `ArticleGeneratorService/`, frontend at `ArticleGeneratorAdm/`, shared DB at `article_generator.db`. Migrations are raw SQL files in `ArticleGeneratorDatabase/migrations/` (no Alembic). Seed script at `scripts/seed_providers.py`.

## Goals / Non-Goals

**Goals:**
1. Apply missing DB migrations (article title, scenario_config description/sort_order)
2. Seed missing scenario configs (humanize, direction, outline, title) with proper descriptions and sort_order
3. Add `title` to Article Pydantic schemas and frontend TypeScript interface
4. Add `description`/`sort_order` to ScenarioConfig Pydantic schemas
5. Extend unified task endpoint to surface all task types, not just generate/refine
6. Add `task_type`, `target`, `account_name`, `extra_info` to frontend `UnifiedTaskItem` interface
7. Add title generation step to CreateView (backend endpoint already exists)
8. Simplify article title display in views (use `article.title` directly instead of fallback chains)

**Non-Goals:**
- Redesigning the article creation flow beyond adding the title step
- Building a full Celery task DB-persistence layer (use Celery result backend as fallback for non-generate/refine tasks)
- Restructuring the TaskCenter vs TasksView route (keep both for now)
- Changing the LLM gateway or provider configuration
- Fixing the accounts table migration gap (out of scope for this phase)

## Decisions

### D1: Apply migrations manually rather than introducing Alembic

**Choice**: Run existing raw SQL migration files directly against the SQLite database.

**Rationale**: The project already has 13 numbered raw SQL migration files. Introducing Alembic would require retrofitting all existing migrations and changing the dev workflow. For a small team, manual application is simpler and sufficient. The risk is low since we're adding columns with safe defaults (VARCHAR NULL, TEXT NULL, INT DEFAULT 0).

**Alternative considered**: Introduce Alembic. Rejected because it adds complexity disproportionate to the current team size and migration volume.

### D2: Use Celery result backend as fallback for non-DB-tracked task types

**Choice**: For task types that don't have DB records (humanize, distill, direction, outline, title, quality_review, compliance_review), query the Celery `AsyncResult` backend and merge results into the unified response.

**Rationale**: The unified endpoint queries `generation_tasks` and `refine_tasks` UNION. Non-generate/refine tasks are Celery-only (no DB record). Rather than creating new DB tables for each task type, we can query Celery's result backend for recent tasks. This is a lower-effort approach that gives visibility without schema changes.

**Alternative considered**: Create `task_records` table for all async tasks. Rejected for this phase — it's a larger change that should be designed carefully. The Celery fallback is sufficient for Phase 2 observability needs.

### D3: Add `title` to `ArticleBase` Pydantic schema

**Choice**: Add `title: Optional[str] = None` to `ArticleBase` in Pydantic schemas.

**Rationale**: The `title` field is already in the SQLAlchemy model and API responses pass it through. Adding it to `ArticleBase` makes it a declared field in all Article-related response schemas (`ArticleResponse`, `ArticleWithRelations`) via inheritance. This is additive and non-breaking.

### D4: Frontend type updates follow backend reality

**Choice**: Update TypeScript interfaces to match what the backend actually returns, rather than creating separate frontend-specific types.

**Rationale**: The backend already returns `task_type`, `target`, `account_name`, `extra_info` in the unified endpoint. These are accessed in Vue templates but untyped, making TypeScript checking unreliable. Adding them to the interface is purely additive.

### D5: CreateView title step insertion between outline and generation

**Choice**: Insert step 4 (title generation) between the existing outline confirmation (step 3) and full-text generation (step 5). This changes the wizard from 5 steps to 6 steps.

**Rationale**: The backend `POST /generate/titles` endpoint already exists. The title logically comes after the outline is confirmed — you need to know the article's structure to generate good titles. The user picking a title before full generation lets the title influence the generated content.

## Risks / Trade-offs

- **[DB migration failure]** → Backup the SQLite file before running any ALTER TABLE. Verify column existence before attempting.
- **[humanize seed creates duplicate]** → Use INSERT OR IGNORE or check existence before inserting. Scenario configs have no UNIQUE constraint on `scenario`, so check by name.
- **[Celery backend unavailable]** → Wrap Celery result queries in try/except; return only DB-tracked tasks on Celery failure.
- **[CreateView step renumbering]** → The step indicator uses numbers (e.g., "步骤 3/5"). After adding the title step, it becomes "步骤 3/6" etc. Ensure all step indices update correctly.
- **[Frontend types out of sync with backend]** → The backend exploration confirmed what fields are actually returned. Type updates mirror reality, not speculation.

## Migration Plan

1. **Backup**: Copy `article_generator.db` before any ALTER TABLE
2. **Apply migrations**: Run 007 (article title) + new migration for scenario_configs.description/sort_order
3. **Seed data**: Run updated seed_providers.py to insert missing scenarios
4. **Deploy**: Restart backend service after schema changes
5. **Rollback**: Restore from DB backup if any step fails

## Open Questions

1. Should `/tasks` route redirect to `/tasks-center`, or keep both? → Keep both for now; `/tasks` is the table-based legacy view some users may prefer.
2. Should non-generate/refine tasks get their own DB records? → Defer to Phase 3; Celery fallback is sufficient for now.
