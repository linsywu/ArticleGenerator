# Tasks: Enhance Collection Task Lifecycle & Materials

## 1. Fix published_at — use API create_time instead of HTML meta

- [ ] `worker.py`: convert `art["create_time"]` (Unix timestamp) to datetime, use as primary `published_at` source, fall back to `meta["published_at"]`

## 2. Execute button → auto-refresh + polling

- [ ] `CollectTasksView.vue` `handleExecute`: add `pollTask(id)` after initial refresh
- [ ] Poll every 2s via `getCollectTask(id)`, update list row, stop when `status !== "running"`
- [ ] Cleanup timers in `onUnmounted`

## 3. Task lifecycle drawer (log button → el-drawer)

- [ ] Replace `viewLogs` navigation with `el-drawer` containing real-time log table
- [ ] Poll `GET /collect-logs?task_id=X` every 2s until all entries have `end_time`
- [ ] Import `collectLogsApi` and `CollectLog` type

## 4. Materials pagination enhancement

- [ ] `MaterialsView.vue` `el-pagination`: add `total, sizes` to layout, add `page-sizes`

## 5. Materials is_original column + published_at display

- [ ] Table: add `is_original` tag column (原创/转载)
- [ ] `published_at` column already exists — will show real dates after Task 1 fix

## 6. Collect log detail drawer

- [ ] Backend: add `GET /collect-logs/{log_id}` endpoint with sibling batch logs
- [ ] Frontend API: add `getCollectLog` to `collectLogs.ts`
- [ ] Frontend: add `CollectLogResponse.siblings` to schema and types
- [ ] `CollectLogsView.vue`: add row click → drawer with `el-descriptions` + siblings table
