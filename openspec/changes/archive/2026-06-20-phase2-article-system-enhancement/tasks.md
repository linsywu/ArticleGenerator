## 1. DB Migrations (foundation)

- [ ] 1.1 Backup the SQLite database (`cp article_generator.db article_generator.db.bak`)
- [ ] 1.2 Apply migration 007 (`ALTER TABLE articles ADD COLUMN title VARCHAR(200)`) to the actual SQLite DB
- [ ] 1.3 Create and apply new migration for `ALTER TABLE scenario_configs ADD COLUMN description TEXT` and `ADD COLUMN sort_order INTEGER DEFAULT 0`
- [ ] 1.4 Verify columns exist in DB: `PRAGMA table_info(articles)` shows `title`, `PRAGMA table_info(scenario_configs)` shows `description` and `sort_order`

## 2. P0: Seed missing scenario configs (humanize + extras)

- [ ] 2.1 Update `scripts/seed_providers.py` to add `humanize` scenario config with `description` and `sort_order`
- [ ] 2.2 Add `direction`, `outline`, `title` scenario configs with proper descriptions and sort_orders
- [ ] 2.3 Update existing 5 scenario configs to include `description` and `sort_order` fields
- [ ] 2.4 Make seed script idempotent (UPDATE existing rows by scenario name, INSERT if not found)
- [ ] 2.5 Run seed script and verify all 9 scenario configs exist in DB

## 3. Backend schema updates (Pydantic)

- [ ] 3.1 Add `title: Optional[str] = None` to `ArticleBase` in `ArticleGeneratorService/app/schemas.py`
- [ ] 3.2 Add `description: Optional[str] = None` and `sort_order: Optional[int] = None` to `ScenarioConfigBase`
- [ ] 3.3 Verify imports: `python -c "from app.schemas import ArticleBase, ScenarioConfigBase"` works from ArticleGeneratorService

## 4. Frontend type updates (TypeScript)

- [ ] 4.1 Add `title?: string` to `Article` interface in `src/api/types.ts`
- [ ] 4.2 Add `description?: string` and `sort_order?: number` to `ScenarioConfig` interface
- [ ] 4.3 Add `task_type: string`, `target: string`, `account_name?: string`, `extra_info?: string` to `UnifiedTaskItem` interface
- [ ] 4.4 Run `npx vue-tsc --noEmit` (or `npm run build`) in ArticleGeneratorAdm to check for type errors

## 5. Unified task center extension (backend + frontend)

- [ ] 5.1 Extend `GET /api/tasks/unified` in `app/api/tasks.py` to query Celery result backend for non-DB task types (humanize, distill, direction, outline, title, quality_review, compliance_review)
- [ ] 5.2 Add Celery result query as fallback with try/except wrapping
- [ ] 5.3 Add emoji icons and Chinese labels in `TaskCenterView.vue` for all 9 task types
- [ ] 5.4 Verify task center shows all task types by checking the page at `/tasks-center`

## 6. CreateView title generation step (frontend)

- [ ] 6.1 Add title generation API call to `src/api/modules/tasks.ts` (or use existing `generateDirections`/`generateOutline` pattern)
- [ ] 6.2 Insert title step between outline confirmation and full generation in `CreateView.vue`
- [ ] 6.3 Update step indicator from 5 steps to 6 steps (选择账号 → 输入想法 → 选择方向 → 确认大纲 → 生成标题 → 生成全文)
- [ ] 6.4 Display 3-5 candidate titles as selectable cards with editable input
- [ ] 6.5 Pass selected title to full-text generation call
- [ ] 6.6 Update all step number references (e.g., "步骤 3/5" → "步骤 3/6")

## 7. Scenario config seed data enhancement

- [ ] 7.1 Update existing 5 scenario configs in seed script with the correct `description` and `sort_order` values per the plan:
  - distill: sort_order=1, generate: sort_order=2, humanize: sort_order=3, quality_review: sort_order=4, compliance_review: sort_order=5, refine: sort_order=6, direction: sort_order=7, outline: sort_order=8, title: sort_order=4 (adjust to avoid conflicts — use: distill=1, direction=2, outline=3, title=4, generate=5, humanize=6, quality_review=7, compliance_review=8, refine=9)
- [ ] 7.2 Re-run seed script to update existing rows with description/sort_order values

## 8. Verification

- [ ] 8.1 Start backend: `cd ArticleGeneratorService && uvicorn app.main:app --host 0.0.0.0 --port 8000`
- [ ] 8.2 Verify `GET /api/scenario-configs` returns all 9 configs with `description` and `sort_order` fields
- [ ] 8.3 Verify `GET /api/articles` returns `title` field in response
- [ ] 8.4 Verify `GET /api/tasks/unified` returns extended task types
- [ ] 8.5 Start frontend: `cd ArticleGeneratorAdm && npm run dev`
- [ ] 8.6 Open ScenarioConfigsView in browser — confirm description, sort_order, prompt preview columns render
- [ ] 8.7 Open TaskCenterView — confirm all task type icons/labels display
- [ ] 8.8 Open CreateView — walk through 6-step wizard including title generation step
- [ ] 8.9 Check browser console for errors across all affected pages
- [ ] 8.10 Run `npx vitest run` and `npx playwright test` if available
