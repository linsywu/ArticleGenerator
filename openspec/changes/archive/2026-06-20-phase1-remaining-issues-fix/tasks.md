## 1. Fix CredentialsView handleCheck bug

- [ ] 1.1 Remove nested/duplicated try-catch block in `handleCheck` function (lines 170-176 referencing undefined `row`)
- [ ] 1.2 Ensure `fetchCredentials()` is called after `checkCredential(id)` to refresh the list
- [ ] 1.3 Verify the "检测" button works: click → API call → status updates → list refreshes

## 2. Fix CollectTasksView execute feedback

- [ ] 2.1 Replace `ElMessage.info("功能开发中")` (line 416) with `ElMessage.success("采集任务已提交执行")`
- [ ] 2.2 Add `await fetchCollectTasks()` after successful execute to refresh the list

## 3. Fix CollectTasksView tree selector state sync

- [ ] 3.1 In `openEditDialog`: parse `row.track_ids` and `row.account_ids` (JSON strings) to restore `selectedTrackIds` and `selectedAccountIds`
- [ ] 3.2 In `handleSave`: serialize `selectedTrackIds` / `selectedAccountIds` to JSON strings in `payload.track_ids` / `payload.account_ids`
- [ ] 3.3 Verify: edit an existing task → tree selector shows previously selected tracks/accounts
- [ ] 3.4 Verify: save edited task → `track_ids` and `account_ids` correctly serialized in payload

## 4. Add MpMaterial and CollectLog Pydantic schemas

- [ ] 4.1 Add `MpMaterialResponse` and `MpMaterialList` schemas to `app/schemas.py` following existing Pydantic v2 patterns
- [ ] 4.2 Add `CollectLogResponse` and `CollectLogList` schemas to `app/schemas.py`
- [ ] 4.3 Update `app/api/materials.py`: use `response_model` for list and detail endpoints
- [ ] 4.4 Update `app/api/collect_logs.py`: use `response_model` for list endpoint
- [ ] 4.5 Verify imports pass and `/api/docs` shows correct response models

## 5. Fix hardcoded credential_id in MpAccountsView imports

- [ ] 5.1 Add `fetchCredentials()` call in `onMounted` to populate credentials list
- [ ] 5.2 In `handleImportByName` and `handleImportByUrl`: use first available credential with `status === "normal"` instead of hardcoded `1`
- [ ] 5.3 Show `ElMessage.warning("请先添加采集凭证")` if no normal credential available
- [ ] 5.4 Verify: import by name and import by URL work with dynamic credential selection

## 6. Backend import verification

- [ ] 6.1 Run backend dev server and verify all imports succeed (collector, schemas, API modules)
- [ ] 6.2 Run frontend dev server and verify no TypeScript compilation errors
- [ ] 6.3 Manual smoke test: visit CredentialsView → click "检测", CollectTasksView → click "执行", MpAccountsView → open import dialog
