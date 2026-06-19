## 1. Database Migrations

- [ ] 1.1 Create migration 008 for tracks table (id, name, description, keywords JSON, forbidden_keywords JSON, status, created_at, updated_at)
- [ ] 1.2 Create migration 008 for sub_tracks table (id, track_id FK, name, description, created_at) with CASCADE delete
- [ ] 1.3 Create migration 009 for mp_accounts table (id, name, alias, fakeid, biz, avatar, description, track_ids JSON, article_count, last_collect_time, status, timestamps)
- [ ] 1.4 Create migration 010 for mp_credentials table (id, name, token, cookie, status, check_time, created_at)
- [ ] 1.5 Create migration 011 for collect_tasks table with FK to mp_credentials (id, name, credential_id FK, track_ids JSON, account_ids JSON, collect_mode, date_start, date_end, schedule_type, cron, interval_hours, status, timestamps)
- [ ] 1.6 Create migration 012 for mp_materials table (id, account_id FK, title, author, original_url UNIQUE, cover_url, summary, raw_html LONGTEXT, content_markdown LONGTEXT, content_hash, word_count, is_original, published_at, collected_at) with indexes
- [ ] 1.7 Create migration 013 for collect_logs table (id, task_id FK, account_id, start_time, end_time, total_count, success_count, fail_count, error_message JSON, created_at)

## 2. Track Management Backend

- [ ] 2.1 Add Track and SubTrack SQLAlchemy models to ArticleGeneratorService/app/models.py
- [ ] 2.2 Add Track and SubTrack Pydantic schemas to ArticleGeneratorService/app/schemas.py
- [ ] 2.3 Create API module ArticleGeneratorService/app/api/tracks.py with CRUD endpoints (list, create, get with sub-tracks, update, toggle status, delete)
- [ ] 2.4 Create SubTrack endpoints (create under track, update, delete)
- [ ] 2.5 Register tracks router in ArticleGeneratorService/app/main.py

## 3. Track Management Frontend

- [ ] 3.1 Create API module ArticleGeneratorAdm/src/api/modules/tracks.ts (types + client functions)
- [ ] 3.2 Create TracksView.vue with table list, search, status filter, add/edit modal, toggle status, delete confirmation
- [ ] 3.3 Add inline sub-track management to TracksView (expand row → list sub-tracks → add/edit/delete)
- [ ] 3.4 Add /tracks route to router and navigation item to LayoutView sidebar

## 4. MP Account Management Backend

- [ ] 4.1 Add MpAccount SQLAlchemy model to models.py
- [ ] 4.2 Add MpAccount Pydantic schemas to schemas.py
- [ ] 4.3 Create API module ArticleGeneratorService/app/api/mp_accounts.py with CRUD endpoints
- [ ] 4.4 Implement POST /api/mp-accounts/import-by-name endpoint (accept names[], call searchbiz via MpClient)
- [ ] 4.5 Implement POST /api/mp-accounts/import-by-url endpoint (accept urls[], extract biz parameter)
- [ ] 4.6 Register mp_accounts router in main.py

## 5. MP Account Management Frontend

- [ ] 5.1 Create API module ArticleGeneratorAdm/src/api/modules/mpAccounts.ts
- [ ] 5.2 Create MpAccountsView.vue with table list, track filter, status filter, search, add/edit, toggle, delete
- [ ] 5.3 Create import modal with two tabs (名称导入 and 链接导入), textarea input, submit button
- [ ] 5.4 Add /mp-accounts route to router and navigation item

## 6. Collection Credential Backend

- [ ] 6.1 Add MpCredential SQLAlchemy model to models.py
- [ ] 6.2 Add MpCredential Pydantic schemas to schemas.py
- [ ] 6.3 Create API module ArticleGeneratorService/app/api/credentials.py with CRUD endpoints
- [ ] 6.4 Implement POST /api/credentials/{id}/check endpoint (test credential with searchbiz call)
- [ ] 6.5 Create Celery Beat periodic task for automated credential health check (every 6 hours)
- [ ] 6.6 Register credentials router in main.py

## 7. Collection Credential Frontend

- [ ] 7.1 Create API module ArticleGeneratorAdm/src/api/modules/credentials.ts
- [ ] 7.2 Create CredentialsView.vue with card list showing name, status badge, check_time, add/edit/delete
- [ ] 7.3 Add manual "检测" button per credential that triggers health check
- [ ] 7.4 Add /credentials route to router and navigation item

## 8. Collection Task Backend

- [ ] 8.1 Add CollectTask SQLAlchemy model to models.py
- [ ] 8.2 Add CollectTask Pydantic schemas to schemas.py
- [ ] 8.3 Create API module ArticleGeneratorService/app/api/collect_tasks.py with CRUD endpoints
- [ ] 8.4 Implement POST /api/collect-tasks/{id}/execute endpoint (trigger Celery worker)
- [ ] 8.5 Implement POST /api/collect-tasks/{id}/pause and /resume endpoints
- [ ] 8.6 Register collect_tasks router in main.py

## 9. Collection Task Frontend

- [ ] 9.1 Create API module ArticleGeneratorAdm/src/api/modules/collectTasks.ts
- [ ] 9.2 Create CollectTasksView.vue with table list, status column, add/edit/delete/execute/pause/resume
- [ ] 9.3 Implement multi-level selector component: track checkbox → expand → account checkboxes (checked by default when track selected)
- [ ] 9.4 Implement collect mode dropdown (history_50/100/200, date_range, incremental) with conditional date range inputs
- [ ] 9.5 Implement schedule type selector (manual/interval/cron) with conditional cron/interval inputs
- [ ] 9.6 Add /collect-tasks route to router and navigation item

## 10. Collection Engine (MpClient)

- [ ] 10.1 Create ArticleGeneratorService/app/collector/ package directory with __init__.py
- [ ] 10.2 Create mp_client.py: MpClient class with fetch_article_list(fakeid, credential, mode) using appmsg API
- [ ] 10.3 Create mp_client.py: search_account(name, credential) using searchbiz API
- [ ] 10.4 Create mp_client.py: fetch_article_html(url) to get raw HTML from article page
- [ ] 10.5 Create mp_client.py: extract_metadata(html) to parse title, author, published_at from HTML meta tags
- [ ] 10.6 Add request rate limiter helper (global interval ≥15s + random jitter, same-domain ≥20-30s)
- [ ] 10.7 Add credential pre-check logic to mp_client

## 11. Collection Engine (Worker & Scheduler)

- [ ] 11.1 Create collector/worker.py: Celery task execute_collect_task(task_id) implementing the full collection flow
- [ ] 11.2 Implement article dedup logic in worker (URL unique index check + SHA256 content hash check)
- [ ] 11.3 Implement retry logic (10min → 30min → 60min, max 3 retries per article)
- [ ] 11.4 Implement collect_log writing (start, per-account counts, errors, end)
- [ ] 11.5 Create collector/scheduler.py: Celery Beat schedule configuration for cron/interval tasks
- [ ] 11.6 Register Celery Beat schedule in tasks.py or celery config
- [ ] 11.7 Add word count estimation during collection (from raw_html text length)

## 12. Materials Backend

- [ ] 12.1 Add MpMaterial SQLAlchemy model to models.py
- [ ] 12.2 Add MpMaterial Pydantic schemas to schemas.py
- [ ] 12.3 Create API module ArticleGeneratorService/app/api/materials.py with list endpoint (filters: track_id, account_id, date_start, date_end, search, pagination)
- [ ] 12.4 Implement GET /api/materials/{id} detail endpoint with raw_html and content_markdown
- [ ] 12.5 Implement POST /api/materials/{id}/parse endpoint (HTML → Markdown via Turndown, save to content_markdown)
- [ ] 12.6 Register materials router in main.py

## 13. Collect Logs Backend

- [ ] 13.1 Add CollectLog SQLAlchemy model to models.py
- [ ] 13.2 Create API module ArticleGeneratorService/app/api/collect_logs.py with list and detail endpoints
- [ ] 13.3 Register collect_logs router in main.py

## 14. Materials Frontend

- [ ] 14.1 Create API module ArticleGeneratorAdm/src/api/modules/materials.ts
- [ ] 14.2 Create MaterialsView.vue with table list, filters (track, account, date range, search), pagination
- [ ] 14.3 Create material detail view with tabs: raw HTML preview and Markdown preview
- [ ] 14.4 Implement lazy parse trigger when switching to Markdown tab (call /api/materials/{id}/parse if content_markdown is null)
- [ ] 14.5 Add "💡 创作方向" button placeholder on each material row (UI only, backend in Phase 3)
- [ ] 14.6 Add /materials route to router and navigation item

## 15. Integration & Verification

- [ ] 15.1 Run all migrations against dev database and verify tables created
- [ ] 15.2 Start backend dev server and verify all new API endpoints return correct responses via /docs
- [ ] 15.3 Start frontend dev server and manually verify each new page loads and CRUD operations work
- [ ] 15.4 Test collection flow end-to-end: create credential → create task → execute → verify materials appear
- [ ] 15.5 Test credential health check (manual + scheduled)
- [ ] 15.6 Test dedup: run same collection task twice, verify no duplicate materials
- [ ] 15.7 Test retry: simulate article fetch failure, verify retry behavior
- [ ] 15.8 Verify navigation sidebar shows all new menu items and routes work
