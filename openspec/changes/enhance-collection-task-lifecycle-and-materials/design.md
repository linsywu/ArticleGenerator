## 1. 执行后自动刷新 + 状态轮询

`CollectTasksView.vue` `handleExecute` 改为：
1. 调用 `executeTask(id)` 
2. `fetchCollectTasks()` 刷新列表
3. `setInterval` 轮询 `getCollectTask(id)` 直到 `status !== "running"`，过程中更新该行状态

## 2. 任务日志抽屉

`CollectTasksView.vue` 现有"日志"按钮改为打开右侧 `el-drawer`：
- 轮询 `GET /collect-logs?task_id=X` 每 2 秒
- 展示：公众号名、开始/结束时间、成功/失败/总计、进度条
- 任务完成时停止轮询并高亮显示最终结果

## 3. 素材中心分页增强

`MaterialsView.vue` `el-pagination` 改为：
```html
<el-pagination layout="total, sizes, prev, pager, next" :page-sizes="[10,20,50]" ... />
```

## 4. 素材中心原创/发布时间

- `MaterialsView.vue` 表格增加 `is_original`（原创/转载 tag）和 `published_at` 列
- `worker.py` `_collect_from_account` 检查 `published_at` 是否正确传入 `MpMaterial`（当前 `meta["published_at"]` 可能为 None）

## 5. 采集日志详情抽屉

`CollectLogsView.vue` 表格行点击 → 展开 `el-drawer`：
- 显示该日志的完整信息：任务名、公众号、开始/结束时间、成功/失败/总计、完整错误信息
- 如果是最近执行的日志，显示关联的其他账号日志（同一批次）
