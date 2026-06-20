## Why

Phase 1 MVP 采集管道的主体功能已全部实现（tasks.md 15 组任务均标记完成），但 code review 和实际使用中发现了 5 类遗留问题：CredentialsView 存在语法/逻辑错误导致检测按钮不可用、CollectTasksView 执行反馈和选择器状态同步缺失、后端 schemas 缺少 MpMaterial/CollectLog 的 Pydantic 模型导致 API 返回裸 dict、导入功能硬编码 credential_id。这些问题影响功能可用性和代码规范一致性。

## What Changes

- **修复** CredentialsView.vue `handleCheck` 函数中的嵌套 try-catch 和未定义变量 `row` 错误
- **修复** CollectTasksView.vue 执行按钮反馈：移除误导性的"功能开发中"提示，改为正确处理执行结果
- **修复** CollectTasksView.vue 树形选择器：编辑时恢复已选的赛道和公众号状态，保存时同步 selectedTrackIds/selectedAccountIds 到 form.track_ids/account_ids
- **新增** MpMaterial 和 CollectLog 的 Pydantic schemas（Create/Response/List），更新 materials API 和 collect_logs API 使用类型化响应模型
- **修复** MpAccountsView.vue 导入功能中硬编码 `credential_id: 1`，改为动态获取第一个可用凭证

## Capabilities

### New Capabilities

<!-- No new capabilities — all changes are fixes to existing phase1 capabilities -->

### Modified Capabilities

<!-- No spec-level requirement changes — implementation fixes only -->

## Impact

- **受影响文件（后端）**: `app/schemas.py`（新增 schemas）、`app/api/materials.py`（使用 response model）、`app/api/collect_logs.py`（使用 response model）
- **受影响文件（前端）**: `src/views/CredentialsView.vue`（修复 handleCheck）、`src/views/CollectTasksView.vue`（修复执行反馈 + 树形选择器同步）、`src/views/MpAccountsView.vue`（修复硬编码 credential_id）
- **不涉及**: 数据库迁移、新增依赖、API 路由变更、现有数据模型
