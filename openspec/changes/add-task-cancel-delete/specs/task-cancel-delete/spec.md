## Spec: task-cancel-delete

### Requirement: 任务中心取消按钮

TaskCenterView 中 `pending` 和 `running` 状态的任务卡片操作区增加"取消"按钮。

- `task_type === 'generate'` 时：调用 `POST /api/generate/tasks/{task_id}/cancel`
- `task_type === 'refine'` 时：按钮不显示（暂不支持）
- 取消前弹出确认对话框
- 取消成功后刷新任务列表

### Requirement: 任务中心删除按钮

TaskCenterView 中 `success`、`failed`、`cancelled` 状态的任务卡片操作区增加"删除"按钮。

- `task_type === 'generate'` 时：调用 `DELETE /api/generate/tasks/{task_id}`
- `task_type === 'refine'` 时：按钮不显示（暂不支持）
- 删除前弹出确认对话框
- 删除成功后从列表中移除该卡片

### Requirement: 任务记录删除按钮

TasksView 表格操作列的 `success`、`failed`、`cancelled` 状态任务增加"删除"按钮。

- 调用 `DELETE /api/generate/tasks/{task_id}`
- 删除前弹出确认对话框
- 删除后刷新列表

### Requirement: 后端删除端点

新增 `DELETE /api/generate/tasks/{task_id}`：

- 只允许删除 `success`、`failed`、`cancelled` 状态的任务
- `pending`、`running` 返回 400 错误："请先取消任务"
- 删除时同步清理关联的 `generation_logs`
- 返回 `{"message": "已删除"}`
