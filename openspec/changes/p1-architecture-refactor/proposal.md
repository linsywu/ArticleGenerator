## Why

P0 建立了安全基础（JWT 鉴权、脱敏、CORS），但核心架构问题未解决：Router 内 `task.get(timeout=120)` 同步阻塞 Celery、业务逻辑堆积在 `api/*.py`、`tasks.py` 688 行单体文件、前端组件散落各处无复用。P1 聚焦后端分层解耦和前端组件化，提升可维护性和性能。

## What Changes

- **T07**：移除 `api/generate.py` 中三处 `task.get(timeout=120)` 同步阻塞，改为 `delay()` 异步返回 task_id
- **T08**：新建 `app/services/generate_service.py` + `article_service.py`，将业务逻辑从 Router 移入 Service 层。Router 函数目标 ≤30 行
- **T09**：拆分 `tasks.py`（688 行）为 `app/celery_app.py` + `app/tasks/generate.py` + `tasks/review.py` + `tasks/distill.py`。提取重复 JSON 解析到 `utils/json_parse.py`
- **T11**：抽取 `ArticleEditorDialog.vue`（合并 Review/Publish/CreateView 三处文章对话框）、`PageHeader.vue`、`usePaginatedList`、`useActiveTasks` hooks。`App.vue` 目标 <250 行（已通过 LayoutView 拆分接近完成）
- **T12**：新建 `store/accounts.ts` + `store/tasks.ts`（Pinia），账号列表和运行中任务跨页面共享，消除重复请求
- **T13**：生成触发时校验全部 hotspot_id，缺失则 400 + `{invalid_ids: [...]}`

T10（前端 API 层重构）已在 P0 T01 中随 JWT 鉴权一并完成。

## Capabilities

### New Capabilities
- `service-layer`: 后端 app/services/ 业务逻辑层，Router 仅做参数校验和调用委托
- `celery-module-split`: 拆分 Celery tasks 为模块化 tasks/ 包
- `async-generate-api`: 移除 Router 内 Celery 同步阻塞，全部异步化
- `shared-frontend-components`: 抽取 ArticleEditorDialog、PageHeader、usePaginatedList、useActiveTasks
- `pinia-state-management`: 跨页面共享账号列表和任务状态
- `input-validation`: 触发生成时校验 hotspot_id 有效性

### Modified Capabilities
- 无：P1 为全新架构重构，不修改已有 openspec spec

## Impact

- **后端**：`api/generate.py` 瘦身 + `api/articles.py` 瘦身 + 新建 `services/` + 拆分 `tasks.py` → `tasks/` 包
- **前端**：新建 `components/ArticleEditorDialog.vue`、`PageHeader.vue`、`hooks/`、`store/`；修改 ReviewView、PublishView、CreateView、App.vue
- **依赖**：Pinia（前端，可能已安装）
- **BREAKING**：T07 移除同步等待后，依赖 `task.get()` 返回结果的调用方需改为轮询 task_id
