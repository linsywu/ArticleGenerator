## Context

P0 已建立 JWT 鉴权和基础安全，但后端 `generate.py`(248 行) 和 `tasks.py`(688 行) 严重违反分层规范。Router 内三处 `task.get(timeout=120)` 同步阻塞 Celery，前端组件散落无复用。`.cursor/rules/backend-development.mdc` 要求 `api/ → services/ → models/` 分层，`api/*.py` 禁止堆叠复杂业务。

## Goals / Non-Goals

**Goals:**
- 后端 Service 层：业务逻辑从 Router 移至 `services/generate_service.py` + `article_service.py`
- Router 异步化：`task.get(timeout=120)` → `delay()` 返回 task_id
- Celery 模块化：`tasks.py`(688 行) → `tasks/generate.py` + `review.py` + `distill.py`
- 前端组件化：统一 ArticleEditorDialog、PageHeader、usePaginatedList、useActiveTasks
- Pinia 状态管理：账号列表和任务状态跨页共享

**Non-Goals:**
- 不改 Celery 任务名（保持向后兼容）
- 不改前端 API 层（T10 已在 P0 完成）
- 不引入新的后端依赖

## Decisions

### D1: Service 层抽取顺序
- **选择**：先建 Service 层（T08），再移除非阻塞（T07），最后拆 Celery（T09）
- **理由**：Service 提供统一接口后，Router 和 Celery tasks 都通过 Service 操作，避免 Celery 拆分时重复逻辑

### D2: Router 函数目标 ≤30 行
- **选择**：Router 仅做参数校验、调用 service、返回结果。不需要的事务管理由 service 处理
- **替代方案**：保留部分轻量 Router 内联。放弃原因：rule 明确禁止 Router 内堆叠业务逻辑

### D3: 前端组件抽取优先级
- **选择**：先 ArticleEditorDialog（使用频率最高，三处重复），再 PageHeader + hooks
- **理由**：ArticleEditorDialog 代码量最大、重复最严重，优先封装收益最高

### D4: Pinia store 策略
- **选择**：`store/accounts.ts` 缓存账号列表（stale-while-revalidate）；`store/tasks.ts` 管理运行中任务（全局单例轮询替代 LayoutView + TaskCenterView 双 poll）
- **理由**：消除切换页面时的重复请求

## Risks / Trade-offs

| Risk | Mitigation |
|------|-----------|
| T07 移除同步等待后，CreateView 前端未适配轮询 | CreateView 已有 TaskCenterView 可复用；T01 已建立统一的 /api/tasks/unified |
| T08 Service 层引入后 import 路径变化导致测试失败 | 每步跑 pytest，即时修复 |
| T09 Celery 拆分后任务名变化 | 保持原任务名；仅内部模块重组 |
| Pinia 引入后现有 ref 模式冲突 | 渐进替换：先 store 定义，再逐 View 迁移 |

## Migration Plan

1. T08 → T07 → T09（后端顺序依赖）
2. T11（前端组件，独立）→ T12（Pinia，依赖 T11 的 hooks）
3. T13（校验，独立小改动）
4. 每任务独立 commit，全量 pytest + vitest + npm build + E2E
