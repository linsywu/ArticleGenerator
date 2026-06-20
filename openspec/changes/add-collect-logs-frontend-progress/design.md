## Design

### 1. Task Status Lifecycle

```
idle → running → completed (success)
              → error (failure)
paused → idle (resume)
```

`completed` 替代原来成功时的 `idle`，区分"从未执行"与"已完成"。

### 2. last_result 聚合

`CollectTaskResponse` 新增 `last_result: Optional[dict]` 字段：
- `total_count`: 该次执行所有账号的 article 总数
- `success_count`: 成功入库数
- `fail_count`: 失败数
- `executed_at`: 最近一次执行时间

查询方式：`list_collect_tasks` 对每个 task 查 `CollectLog` 表 `ORDER BY created_at DESC` 取最新一组聚合。

### 3. CollectLogsView

参考 MaterialsView 的列表+筛选+分页模式：
- 工具栏：`el-select` 按 task 筛选
- Table 列：任务名、公众号、开始/结束时间、成功/失败/总计、错误信息
- 分页组件
- 支持 `?task_id=` query 预筛选（从 CollectTasksView 跳转携带）

### 4. CollectTasksView Enhancements

- `completed` 状态：tag 绿色 "已完成"
- `running` 状态：CSS pulse 呼吸灯动效
- 最近结果列：展示 `last_result.success_count/fail_count` + 时间
- "日志"按钮：跳转 `/collect-logs?task_id=row.id`
