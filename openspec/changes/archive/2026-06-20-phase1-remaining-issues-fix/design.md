## Context

Phase 1 MVP 的 15 组实现任务已全部完成且归档。但在集成验证和代码审查中发现了 5 类遗留问题，均为实现层面的缺陷或遗漏，不涉及架构变更。现有技术栈：FastAPI + SQLAlchemy + Pydantic v2（后端），Vue 3 + Element Plus + TypeScript（前端）。

## Goals / Non-Goals

**Goals:**
- 修复 CredentialsView.vue `handleCheck` 函数中可阻断功能的语法错误
- 修复 CollectTasksView.vue 执行反馈和树形选择器状态同步
- 补充 MpMaterial、CollectLog 的 Pydantic schemas，消除 API 裸 dict 返回
- 消除 MpAccountsView 导入功能中硬编码的 credential_id

**Non-Goals:**
- 不新增功能或修改 API 契约
- 不修改数据库模型或迁移
- 不新增前端页面或路由

## Decisions

### 1. CredentialsView handleCheck 修复：内联清理而非重写

**选择:** 在原地修复嵌套 try-catch，移除重复的 `checkCredential(row.id)` 调用（`row` 未定义），保留正确的 API 调用和状态刷新逻辑。

**理由:** 函数其余逻辑正确（调用 API → 刷新列表 → 提示成功）。问题仅在于重复代码块残留。最小改动、最低风险。

### 2. CollectTasksView 执行反馈：改为正确反馈

**选择:** 将 `ElMessage.info("功能开发中")` 替换为 `ElMessage.success("采集任务已提交执行")`，保留 `fetchCollectTasks()` 刷新列表。

**理由:** 后端 `/api/collect-tasks/{id}/execute` 端点已完整实现（dispatch Celery 任务），前端执行后应给出准确反馈。"功能开发中"会误导用户以为整个功能不可用。

### 3. 树形选择器状态同步：双向绑定

**选择:** 
- `openEditDialog`: 从 `row.track_ids` 和 `row.account_ids`（JSON 字符串）解析出 `selectedTrackIds` 和 `selectedAccountIds`
- `handleSave`: 将 `selectedTrackIds` 和 `selectedAccountIds` 序列化为 JSON 字符串写入 `payload.track_ids` / `payload.account_ids`

**理由:** 表单层 store track_ids/account_ids 为 JSON 字符串（与后端 API 一致），树形选择器 UI 需要 number[] 操作。编辑时必须双向同步，否则编辑已有任务时树形选择器显示空白。

### 4. Pydantic Schemas：遵循现有模式

**选择:** 在 schemas.py 中新增 `MpMaterialResponse`、`MpMaterialCreate`、`CollectLogResponse`、`CollectLogCreate`，遵循现有 Pydantic v2 `model_config = {"from_attributes": True}` 模式。materials API 和 collect_logs API 使用 `response_model` 参数。

**理由:** 
- 现有所有 API 端点均使用 Pydantic response models，裸 dict 返回是规范不一致
- Pydantic 提供自动序列化（datetime → ISO string）、验证和 OpenAPI 文档生成
- 不定义 Create schema 因为材料由采集引擎创建（非用户直接创建），但 log 需要创建

### 5. credential_id 硬编码：动态获取

**选择:** 在 `handleImportByName` / `handleImportByUrl` 调用前，通过 `credentialsApi.fetchCredentials()` 获取凭证列表，取第一个 `status === "normal"` 的凭证 ID。若无可用凭证则提示用户。

**理由:** 硬编码 `credential_id: 1` 在凭证被删除或 ID 变化时会失败。动态获取保证健壮性。

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| 树形选择器同步逻辑在复杂赛道结构下可能有边界情况 | 编辑已有任务时以原始 account_ids 为准恢复选择状态，覆盖少选/多选的边界 |
| Pydantic schema 新增字段可能与现有 API 返回不一致 | 严格对照现有 API 手动构造的 dict 字段定义 schema |
| 动态获取 credential 在没有凭证时导入功能不可用 | 给出明确提示（"请先添加采集凭证"），这是正确的产品行为 |
