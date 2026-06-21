# Collect Logs Frontend

## Requirement

提供采集日志的可视化浏览界面。

## Acceptance Criteria

- [ ] 侧边栏"资源"区域出现"采集日志"导航项（icon: 📋）
- [ ] `/collect-logs` 路由加载 CollectLogsView
- [ ] 页面展示采集日志列表（任务名、公众号、时间、成功/失败/总计、错误信息）
- [ ] 支持按任务筛选
- [ ] 支持分页
- [ ] 支持 `?task_id=` query 参数预筛选
- [ ] 后端 API `/api/collect-logs` 返回嵌套 account 对象

## Implementation

**Backend**: collect_logs.py 补全 account 对象
**Frontend**: types.ts 添加 CollectLog 接口；collectLogs.ts API 模块；CollectLogsView.vue；路由+导航注册
