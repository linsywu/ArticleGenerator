## Why

采集任务触发后，用户无法查看进度和状态——任务执行完成回到 `idle` 状态，与"从未执行"无法区分。采集日志功能在需求规划中，后端（模型、API、Schema、路由）已全部实现，但前端页面缺失。

## What Changes

- **后端**：成功完成时 status 从 `idle` 改为 `completed`；CollectTaskResponse 加 `last_result` 聚合字段；collect_logs API 补全嵌套 account 对象
- **前端**：新建 CollectLogsView（列表+筛选+分页）；CollectTasksView 增强：completed 状态、running 动效、最近结果列、日志跳转；注册 /collect-logs 路由和导航

## Capabilities

### New Capabilities
- 采集日志浏览 — 按任务筛选的执行记录，含成功/失败计数和时间

### Modified Capabilities
- 采集任务状态 — `completed` 可区分已完成与未执行；`last_result` 展示最近执行结果

## Impact

- **受影响文件（后端）**: `app/collector/worker.py`（状态变更）、`app/api/collect_tasks.py`（last_result）、`app/api/collect_logs.py`（account 对象）、`app/schemas.py`（last_result 字段）
- **受影响文件（前端）**: `src/api/types.ts`、`src/api/modules/collectLogs.ts`（新建）、`src/api/index.ts`、`src/views/CollectLogsView.vue`（新建）、`src/views/CollectTasksView.vue`、`src/router/index.ts`、`src/views/LayoutView.vue`
- **不涉及**: 数据库迁移、新增依赖
