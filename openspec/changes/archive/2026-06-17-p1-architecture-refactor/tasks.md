# Implementation Tasks

## 1. 后端分层

- [ ] 1.1 T08 — 抽取 Service 层：新建 services/generate_service.py + article_service.py + 瘦身 api/generate.py 和 api/articles.py
- [ ] 1.2 T07 — 移除 Celery 同步阻塞：api/generate.py 中三处 task.get(timeout=120) 改为 delay() + 前端轮询适配
- [ ] 1.3 T09 — 拆分 Celery tasks：app/celery_app.py + app/tasks/generate.py + tasks/review.py + tasks/distill.py + utils/json_parse.py

## 2. 前端组件化

- [ ] 2.1 T11 — 抽取 ArticleEditorDialog + PageHeader + usePaginatedList + useActiveTasks
- [ ] 2.2 T12 — 启用 Pinia Store：store/accounts.ts + store/tasks.ts + 逐 View 迁移

## 3. 输入校验

- [ ] 3.1 T13 — 无效 hotspot_id 显式错误：400 + invalid_ids 明细 + 测试用例
