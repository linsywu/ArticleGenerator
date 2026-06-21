## Why

5 个用户体验改进，基于实际使用反馈：

1. 执行按钮无反馈 — 点击后数据不刷新，无法看到状态变化
2. 任务生命周期不透明 — 只能看最近结果摘要，没有实时进度
3. 素材中心分页器信息不足 — 只有上/下页，无总数和每页数量
4. 素材中心缺失关键字段 — `is_original` 和 `published_at` 未展示，且 `published_at` 解析未生效
5. 采集日志缺少详情查看 — 只能看列表，无法钻取看单次执行完整过程

## What Changes

- **采集任务执行后自动刷新** — `handleExecute` 成功后立即 `fetchCollectTasks()` + 轮询直到 `running` 结束
- **任务日志抽屉 (Drawer)** — 点击"日志"展开右侧 drawer，轮询 CollectLog 数据实时展示执行进度
- **素材中心分页增强** — `el-pagination` 添加 `total`、`page-size`、`sizes` 显示
- **素材中心原创/发布时间** — 表格增加 `is_original` 和 `published_at` 列；修复 worker 中 `published_at` 解析
- **采集日志详情抽屉** — 点击日志行展开 drawer 展示单次执行的完整详情

## Impact

- **后端**: `worker.py` — 修复 `published_at` 解析传递
- **前端**: `CollectTasksView.vue`、`CollectLogsView.vue`、`MaterialsView.vue`、`api/modules/collectLogs.ts`
