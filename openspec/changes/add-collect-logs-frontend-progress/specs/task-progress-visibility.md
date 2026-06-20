# Task Progress Visibility

## Requirement

采集任务执行后必须有明确的状态区分和结果可见性。

## Acceptance Criteria

- [ ] 任务成功完成后 status 为 `completed`（而非 `idle`）
- [ ] `completed` 状态在 CollectTasksView 显示为绿色 tag "已完成"
- [ ] `running` 状态 tag 有 CSS pulse 呼吸灯动效
- [ ] 任务列表显示 `last_result`（最近执行的成功/失败数 + 时间）
- [ ] 任务列表操作列有"日志"按钮，跳转到 `/collect-logs?task_id=X`

## Implementation

**Backend**: worker.py 状态变更；collect_tasks.py 计算 last_result；schemas.py 添加字段
**Frontend**: CollectTasksView.vue 新增列、按钮、动效、状态处理
