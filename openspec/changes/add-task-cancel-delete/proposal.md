## Why

任务中心 (`/task-center`) 和任务记录 (`/tasks`) 两个页面目前缺乏完整的任务生命周期管理：任务中心缺少取消按钮，两个页面都缺少删除功能。用户无法清理失败/已取消的任务记录，也无法在任务中心直接停止运行中的任务。

## What Changes

- **任务中心新增取消按钮**：运行中/排队中的任务卡片增加"取消"操作，调用已有 `POST /generate/tasks/{task_id}/cancel` 端点
- **两个页面新增删除按钮**：已完成/已失败/已取消的任务支持删除
- **后端新增删除端点**：`DELETE /generate/tasks/{task_id}`，删除 GenerationTask 记录（不删除关联文章）
- **统一任务 API 支持取消/删除**：`/tasks/unified` 返回 `task_type` 区分任务来源，前端根据类型调用对应取消/删除接口

## Capabilities

### New Capabilities
- `task-cancel-delete`: 任务中心卡片增加取消按钮；两个页面的任务列表增加删除按钮；后端新增删除端点

### Modified Capabilities
<!-- None — existing spec behavior unchanged -->

## Impact

| 受影响的代码 | 变更 |
|-------------|------|
| `app/api/generate.py` | 新增 `DELETE /generate/tasks/{task_id}` |
| `TaskCenterView.vue` | 运行/等待任务卡片加"取消"；已完成任务卡片加"删除" |
| `TasksView.vue` | 表格操作列加"删除"按钮 |
| `GenerationLogDialog.vue` | 删除任务前清理关联日志（可选） |
