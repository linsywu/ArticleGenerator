# Tasks: Collect Logs Frontend + Task Progress Visibility

## 1. Backend — Add "completed" status

- [ ] Change `task.status = "idle"` → `task.status = "completed"` in `app/collector/worker.py:62`

## 2. Backend — Add last_result to CollectTaskResponse

- [ ] Add `last_result: Optional[dict] = None` to `CollectTaskResponse` in `app/schemas.py`
- [ ] Update `list_collect_tasks` in `app/api/collect_tasks.py` to compute last_result from CollectLog
- [ ] Update `get_collect_task` to also return last_result

## 3. Backend — Add account object to collect_logs API

- [ ] Add `MpAccount` query + nested account dict in `app/api/collect_logs.py` response

## 4. Frontend — Types + API module

- [ ] Add `CollectLog` interface to `src/api/types.ts`
- [ ] Add `last_result` to `CollectTask` interface
- [ ] Create `src/api/modules/collectLogs.ts`
- [ ] Register in `src/api/index.ts`

## 5. Frontend — CollectLogsView.vue

- [ ] Create `src/views/CollectLogsView.vue` with table, task filter, pagination, `?task_id=` query support

## 6. Frontend — Route + navigation

- [ ] Add `/collect-logs` route in `src/router/index.ts`
- [ ] Add nav item in `src/views/LayoutView.vue` sidebar

## 7. Frontend — CollectTasksView enhancements

- [ ] Add `completed` status handling (type/label/filter)
- [ ] Add CSS pulse animation for `running` status
- [ ] Add "最近结果" column showing last_result
- [ ] Add "日志" button linking to `/collect-logs?task_id=`

## 8. End-to-end verification

- [ ] Start servers, execute a task, verify completed status + last_result
- [ ] Navigate to collect logs, verify data
- [ ] Run verifier-unit + verifier-e2e
