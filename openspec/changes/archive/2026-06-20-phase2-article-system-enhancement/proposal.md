## Why

Phase 1 delivered the MVP content pipeline (hotspot → generate → humanize → review → publish). Five gaps remain that cause silent failures, missing data in UIs, and an incomplete creation wizard. Fixing them closes the critical humanize breakage, gives articles proper titles, and makes the task system observable end-to-end.

## What Changes

- **Seed `humanize` scenario config** — the generate→humanize→review chain silently fails because `humanize` scenario has no DB entry. Also seed missing `direction`, `outline`, `title` scenarios.
- **Apply missing DB migrations** — `articles.title` and `scenario_configs.(description|sort_order)` columns exist in SQLAlchemy models and migration SQL files, but were never applied to the actual SQLite database.
- **Add `title` to Pydantic schemas + frontend types** — the field exists in the DB model and API responses but is undeclared in typed schemas, forcing views to use fragile `row.title || row.hotspot?.title` fallback chains.
- **Add `description`/`sort_order` to Pydantic ScenarioConfig schemas** — columns exist in the model but are missing from the API's validated response types.
- **Extend unified task center to cover all task types** — currently only `generate` and `refine` appear; `humanize`, `distill`, `direction`, `outline`, `title`, and review tasks should also be tracked for full observability.
- **Add title generation step to CreateView** — backend task and endpoint already exist; the frontend wizard needs a step between outline confirmation and full-text generation.
- **Clean up frontend TypeScript interfaces** — `Article`, `UnifiedTaskItem`, `ScenarioConfig` types are missing fields that the backend returns and templates use.

## Capabilities

### New Capabilities

- `humanize-seed-fix`: Seed the missing `humanize` scenario config (plus `direction`, `outline`, `title`) with descriptions and sort_order, fixing the silent chain failure in article generation.
- `article-title-field`: Article `title` column migration, Pydantic schema declaration, and frontend type addition so title is a first-class field across the stack.
- `unified-task-tracking`: Extend `/api/tasks/unified` to surface all async task types (humanize, distill, direction, outline, title, quality_review, compliance_review) alongside existing generate/refine, and add missing `UnifiedTaskItem` fields to the frontend TypeScript interface.
- `title-generation-step`: Insert a title generation step (step 4 of 6) into CreateView.vue that calls the existing `POST /generate/titles` endpoint, displays 3-5 candidate titles, and lets the user select or edit before full-text generation.
- `scenario-config-enhancement`: Add `description` and `sort_order` to ScenarioConfig Pydantic schemas and seed data, surfacing fields already present in the DB model and frontend UI.

### Modified Capabilities

<!-- No existing specs to modify -->

## Impact

- **DB**: Apply migration 007 (`articles.title`), create+apply migration for `scenario_configs.description` and `sort_order`
- **Backend**: `app/schemas.py` (Article, ScenarioConfig schemas), `app/api/tasks.py` (unified query extension), `scripts/seed_providers.py` (humanize/direction/outline/title seeds with description/sort_order)
- **Frontend**: `src/api/types.ts` (Article, ScenarioConfig, UnifiedTaskItem interfaces), `src/views/CreateView.vue` (new title step), minor display simplifications in ReviewView/TasksView/PublishView
- **No breaking changes** — all additions are additive; existing API responses gain new fields but don't change existing ones
