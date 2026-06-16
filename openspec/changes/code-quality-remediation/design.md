## Context

ArticleGenerator 经过多轮功能迭代（热点抓取、任务编排、场景配置、任务中心）后，后端 `tasks.py` 膨胀至 688 行，Router 内存在同步阻塞 Celery 调用，无鉴权机制，Provider API Key 明文响应。前端存在孤儿页面、死代码步骤、API 层单体文件等问题。`.cursor/rules/backend-development.mdc` 和 `frontend-development.mdc` 已定义架构约束，但现有代码多处偏离规范。2026-06 全局审查将问题分为 P0（安全/正确性）、P1（架构/性能）、P2（一致性/测试/DB）、P3（优化/文档）四个优先级。

当前技术栈：FastAPI + SQLAlchemy + Celery（后端），Vue 3 + Element Plus + Vite（前端），Redis + SQLite（开发）/ MySQL（生产）。

## Goals / Non-Goals

**Goals:**
- 建立 JWT 登录鉴权（替代无防护状态），所有管理类 API 受保护
- Provider API Key 响应脱敏，LLMService 内部仍可取完整 key
- 统一数据库 Engine（消除 tasks.py 独立 create_engine）
- 消除前端死代码和孤儿页面
- 修复 CORS 安全配置
- Router 异步化（Celery delay 替代同步 get）
- 建立 Service 层分离路由与业务逻辑
- 拆分大文件（tasks 688 行 → 模块；schemas 319 行 → 包；models 183 行 → 包）
- 前端 API 按域拆分，抽取共享组件/hooks，启用 Pinia
- 补全测试覆盖（后端 + LLM + 前端 typecheck）
- 魔法字符串集中、print 替换为 logging

**Non-Goals:**
- 不支持用户注册（P0 阶段手动种子管理员）
- 不引入 RBAC/权限粒度（所有已登录用户等价）
- 不做 MySQL 迁移（T14 仅集成 migration 脚本执行，不改变已部署实例）
- 不做产品功能新增

## Decisions

### D1: JWT over API Key for auth (T01)
- **选择**：用户名+密码 → JWT（24h 过期），前端 LoginView + router 守卫
- **替代方案**：静态 API Key（`X-API-Key` header）。放弃原因：拿到地址即可用，无法区分用户；原计划虽为 API Key，但增加登录页面只需少量额外工作
- **实现**：`python-jose` + `passlib[bcrypt]`；种子用户通过 `.env` 创建；`/api/health` 白名单免鉴权

### D2: User table + seed, no registration UI (T01)
- **选择**：数据库 `users` 表 + 启动种子脚本。无注册端点、无用户管理 UI
- **理由**：B 方案（多用户可扩展）的 DB 成本极低（一张表），且为未来扩展留空间；不做 UI 保持 P0 范围可控

### D3: Service layer extraction pattern (T08)
- **选择**：`services/generate_service.py` 持有编排逻辑；`api/generate.py` 仅校验 + 调用 + 返回
- **替代方案**：直接瘦身 router。放弃原因：无独立 service 层则逻辑分散在 api/ 和 tasks/ 间，测试困难
- **约束**：Router 函数目标 ≤30 行；Service 不直接操作 HTTP（由 Router 处理）

### D4: Frontend API split order (T10)
- **选择**：`api/client.ts` 仅 axios + 拦截器（含 JWT token）；域文件（hotspots/articles/accounts/tasks/providers）独立，`api/index.ts` 聚合导出
- **理由**：现有 `client.ts` 247 行单体 `api` 对象导出，改为具名导入；保持向后兼容

### D5: openspec structure — one capability per task cluster
- **选择**：24 个 capability 映射到 27 个任务（部分任务合并为一个 capability）
- **理由**：每个 capability 可独立验证；spec 场景直接对应验收测试

## Risks / Trade-offs

| Risk | Mitigation |
|------|-----------|
| T01 后所有 API 需 Bearer token，HotspotCrawler 内部调用被阻断 | 爬虫端点或 `/api/hotspots/batch` 保留 shared secret（白名单） |
| T03 改 SQLite 绝对路径后，开发者本地路径不同 | `config.py` 中 `DATABASE_URL` 可 override |
| T07 移除 `task.get(timeout=120)` 后前端未及时适配轮询 | `CreateView.vue` 已有 TaskCenterView 可复用；逐步迁移 |
| T08 Service 层引入后测试可能因 import 变化而失败 | 每步跑 `pytest tests/ -v`，即时修复 |
| T05 删除 GenerateView/DistillView 可能有隐藏引用 | grep 全项目扫描 + `npm run build` 验证 |
| T09 Celery 任务拆分后任务名变化 | 保持原任务名或文档化 migration；当前无外部调度依赖 |

## Migration Plan

1. **开发阶段**：所有 27 个任务在 feature 分支上顺序完成，每任务独立 commit
2. **测试**：每完成一个 P0/P1 任务跑全量测试；P2/P3 任务增加对应新测试
3. **部署**：P0 T01（JWT 鉴权）为 BREAKING 变更，需配合前端 LoginView 一起上线
4. **回滚**：每个任务独立 commit，可单独 revert；T01 回滚需同时 revert 后端中间件 + 前端 router 守卫
5. **数据库**：T01 新增 users 表通过 migration 脚本或 `create_all` 自动创建；T14 之后走迁移脚本

## Open Questions

- T23（任务 API 统一入口）：保留 `/api/generate/tasks/*` 还是 `/api/tasks/unified`？待实现时评估前端调用量后决定
- T03 绝对路径：是否需要支持环境变量 `SQLITE_PATH` 独立于 `DATABASE_URL`？待实现时根据开发者反馈决定
