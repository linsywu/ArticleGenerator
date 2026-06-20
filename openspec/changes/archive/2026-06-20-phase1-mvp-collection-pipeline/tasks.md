## 1. Database Migrations

- [x] 1.1 Create migration 008 for tracks table (id, name, description, keywords JSON, forbidden_keywords JSON, status, created_at, updated_at)
- [x] 1.2 Create migration 008 for sub_tracks table (id, track_id FK, name, description, created_at) with CASCADE delete
- [x] 1.3 Create migration 009 for mp_accounts table (id, name, alias, fakeid, biz, avatar, description, track_ids JSON, article_count, last_collect_time, status, timestamps)
- [x] 1.4 Create migration 010 for mp_credentials table (id, name, token, cookie, status, check_time, created_at)
- [x] 1.5 Create migration 011 for collect_tasks table with FK to mp_credentials (id, name, credential_id FK, track_ids JSON, account_ids JSON, collect_mode, date_start, date_end, schedule_type, cron, interval_hours, status, timestamps)
- [x] 1.6 Create migration 012 for mp_materials table (id, account_id FK, title, author, original_url UNIQUE, cover_url, summary, raw_html LONGTEXT, content_markdown LONGTEXT, content_hash, word_count, is_original, published_at, collected_at) with indexes
- [x] 1.7 Create migration 013 for collect_logs table (id, task_id FK, account_id, start_time, end_time, total_count, success_count, fail_count, error_message JSON, created_at)

## 2. Track Management Backend

- [x] 2.1 Add Track and SubTrack SQLAlchemy models to ArticleGeneratorService/app/models.py
- [x] 2.2 Add Track and SubTrack Pydantic schemas to ArticleGeneratorService/app/schemas.py
- [x] 2.3 Create API module ArticleGeneratorService/app/api/tracks.py with CRUD endpoints (list, create, get with sub-tracks, update, toggle status, delete)
- [x] 2.4 Create SubTrack endpoints (create under track, update, delete)
- [x] 2.5 Register tracks router in ArticleGeneratorService/app/main.py

## 3. Track Management Frontend

- [x] 3.1 Create API module ArticleGeneratorAdm/src/api/modules/tracks.ts (types + client functions)
- [x] 3.2 Create TracksView.vue with table list, search, status filter, add/edit modal, toggle status, delete confirmation
- [x] 3.3 Add inline sub-track management to TracksView (expand row → list sub-tracks → add/edit/delete)
- [x] 3.4 Add /tracks route to router and navigation item to LayoutView sidebar

## 4. MP Account Management Backend

- [x] 4.1 Add MpAccount SQLAlchemy model to models.py
- [x] 4.2 Add MpAccount Pydantic schemas to schemas.py
- [x] 4.3 Create API module ArticleGeneratorService/app/api/mp_accounts.py with CRUD endpoints
- [x] 4.4 Implement POST /api/mp-accounts/import-by-name endpoint (accept names[], call searchbiz via MpClient)
- [x] 4.5 Implement POST /api/mp-accounts/import-by-url endpoint (accept urls[], extract biz parameter)
- [x] 4.6 Register mp_accounts router in main.py

## 5. MP Account Management Frontend

- [x] 5.1 Create API module ArticleGeneratorAdm/src/api/modules/mpAccounts.ts
- [x] 5.2 Create MpAccountsView.vue with table list, track filter, status filter, search, add/edit, toggle, delete
- [x] 5.3 Create import modal with two tabs (名称导入 and 链接导入), textarea input, submit button
- [x] 5.4 Add /mp-accounts route to router and navigation item

## 6. Collection Credential Backend

- [x] 6.1 Add MpCredential SQLAlchemy model to models.py
- [x] 6.2 Add MpCredential Pydantic schemas to schemas.py
- [x] 6.3 Create API module ArticleGeneratorService/app/api/credentials.py with CRUD endpoints
- [x] 6.4 Implement POST /api/credentials/{id}/check endpoint (test credential with searchbiz call)
- [x] 6.5 Create Celery Beat periodic task for automated credential health check (every 6 hours)
- [x] 6.6 Register credentials router in main.py

## 7. Collection Credential Frontend

- [x] 7.1 Create API module ArticleGeneratorAdm/src/api/modules/credentials.ts
- [x] 7.2 Create CredentialsView.vue with card list showing name, status badge, check_time, add/edit/delete
- [x] 7.3 Add manual "检测" button per credential that triggers health check
- [x] 7.4 Add /credentials route to router and navigation item

## 8. Collection Task Backend

- [x] 8.1 Add CollectTask SQLAlchemy model to models.py
- [x] 8.2 Add CollectTask Pydantic schemas to schemas.py
- [x] 8.3 Create API module ArticleGeneratorService/app/api/collect_tasks.py with CRUD endpoints
- [x] 8.4 Implement POST /api/collect-tasks/{id}/execute endpoint (trigger Celery worker)
- [x] 8.5 Implement POST /api/collect-tasks/{id}/pause and /resume endpoints
- [x] 8.6 Register collect_tasks router in main.py

## 9. Collection Task Frontend

- [x] 9.1 Create API module ArticleGeneratorAdm/src/api/modules/collectTasks.ts
- [x] 9.2 Create CollectTasksView.vue with table list, status column, add/edit/delete/execute/pause/resume
- [x] 9.3 Implement multi-level selector component: track checkbox → expand → account checkboxes (checked by default when track selected)
- [x] 9.4 Implement collect mode dropdown (history_50/100/200, date_range, incremental) with conditional date range inputs
- [x] 9.5 Implement schedule type selector (manual/interval/cron) with conditional cron/interval inputs
- [x] 9.6 Add /collect-tasks route to router and navigation item

## 10. Collection Engine (MpClient)

- [x] 10.1 Create ArticleGeneratorService/app/collector/ package directory with __init__.py
- [x] 10.2 Create mp_client.py: MpClient class with fetch_article_list(fakeid, credential, mode) using appmsg API
- [x] 10.3 Create mp_client.py: search_account(name, credential) using searchbiz API
- [x] 10.4 Create mp_client.py: fetch_article_html(url) to get raw HTML from article page
- [x] 10.5 Create mp_client.py: extract_metadata(html) to parse title, author, published_at from HTML meta tags
- [x] 10.6 Add request rate limiter helper (global interval ≥15s + random jitter, same-domain ≥20-30s)
- [x] 10.7 Add credential pre-check logic to mp_client

## 11. Collection Engine (Worker & Scheduler)

- [x] 11.1 Create collector/worker.py: Celery task execute_collect_task(task_id) implementing the full collection flow
- [x] 11.2 Implement article dedup logic in worker (URL unique index check + SHA256 content hash check)
- [x] 11.3 Implement retry logic (10min → 30min → 60min, max 3 retries per article)
- [x] 11.4 Implement collect_log writing (start, per-account counts, errors, end)
- [x] 11.5 Create collector/scheduler.py: Celery Beat schedule configuration for cron/interval tasks
- [x] 11.6 Register Celery Beat schedule in tasks.py or celery config
- [x] 11.7 Add word count estimation during collection (from raw_html text length)

## 12. Materials Backend

- [x] 12.1 Add MpMaterial SQLAlchemy model to models.py
- [x] 12.2 Add MpMaterial Pydantic schemas to schemas.py
- [x] 12.3 Create API module ArticleGeneratorService/app/api/materials.py with list endpoint (filters: track_id, account_id, date_start, date_end, search, pagination)
- [x] 12.4 Implement GET /api/materials/{id} detail endpoint with raw_html and content_markdown
- [x] 12.5 Implement POST /api/materials/{id}/parse endpoint (HTML → Markdown via Turndown, save to content_markdown)
- [x] 12.6 Register materials router in main.py

## 13. Collect Logs Backend

- [x] 13.1 Add CollectLog SQLAlchemy model to models.py
- [x] 13.2 Create API module ArticleGeneratorService/app/api/collect_logs.py with list and detail endpoints
- [x] 13.3 Register collect_logs router in main.py

## 14. Materials Frontend

- [x] 14.1 Create API module ArticleGeneratorAdm/src/api/modules/materials.ts
- [x] 14.2 Create MaterialsView.vue with table list, filters (track, account, date range, search), pagination
- [x] 14.3 Create material detail view with tabs: raw HTML preview and Markdown preview
- [x] 14.4 Implement lazy parse trigger when switching to Markdown tab (call /api/materials/{id}/parse if content_markdown is null)
- [x] 14.5 Add "💡 创作方向" button placeholder on each material row (UI only, backend in Phase 3)
- [x] 14.6 Add /materials route to router and navigation item

## 15. Integration & Verification

- [x] 15.1 Run all migrations against dev database and verify tables created
- [x] 15.2 Start backend dev server and verify all new API endpoints return correct responses via /docs
- [x] 15.3 Start frontend dev server and manually verify each new page loads and CRUD operations work
- [x] 15.4 Test collection flow end-to-end: create credential → create task → execute → verify materials appear
- [x] 15.5 Test credential health check (manual + scheduled)
- [x] 15.6 Test dedup: run same collection task twice, verify no duplicate materials
- [x] 15.7 Test retry: simulate article fetch failure, verify retry behavior
- [x] 15.8 Verify navigation sidebar shows all new menu items and routes work
