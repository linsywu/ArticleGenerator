## Implementation Tasks

### Backend

- [ ] **Task 1**: 新增 `DELETE /api/generate/tasks/{task_id}` 端点
  - 文件: `app/api/generate.py`
  - 校验任务状态（pending/running → 400）
  - 删除关联 generation_logs
  - 删除 GenerationTask 记录
  - 编写测试

### Frontend — TasksView

- [ ] **Task 2**: 表格操作列新增"删除"按钮
  - 文件: `views/TasksView.vue`
  - 仅 `success/failed/cancelled` 状态显示
  - 二次确认 + 刷新列表

### Frontend — TaskCenterView

- [ ] **Task 3**: 任务卡片新增"取消"按钮（pending/running）
  - 文件: `views/TaskCenterView.vue`
  - 仅 `task_type === 'generate'` 显示
  - 二次确认 + 刷新

- [ ] **Task 4**: 任务卡片新增"删除"按钮（success/failed/cancelled）
  - 同文件
  - 仅 `task_type === 'generate'` 显示
  - 二次确认 + 从本地列表移除

### Verification

- [ ] **Task 5**: 后端测试 + 前端构建 + 浏览器验证
  - pytest: 删除端点测试
  - vite build
  - 浏览器点击测试取消/删除流程
