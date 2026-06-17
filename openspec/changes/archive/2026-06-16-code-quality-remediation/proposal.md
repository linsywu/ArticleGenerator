## Why

ArticleGenerator 经过多轮功能迭代后积累了系统性技术债务：无鉴权机制（安全敞口）、API Key 明文响应、Celery 同步阻塞 Router、688 行单体 tasks.py、前端死代码/孤儿页面、散落的魔法字符串。这些问题在 2026-06 全局代码审查中被识别并分级，现需按 P0→P3 优先级逐项修正，确保系统安全、可维护、可测试。

## What Changes

### P0 — 安全与正确性（6 项）
- **JWT 鉴权框架**：新增 User 模型 + POST /api/auth/login + 前端 LoginView + router 守卫。所有受保护 API 需 Bearer token。**BREAKING**：此前无鉴权的接口将拒绝无 token 请求。
- Provider api_key 脱敏：列表/详情响应掩码（`sk-***abc`），写入支持「留空=不修改」
- 统一数据库 Engine：删除 tasks.py 独立 create_engine，API 与 Celery Worker 共用 database.py
- 前端死代码清理：删除 CreateView 步骤 6 + submitForReview；删除 GenerateView.vue / DistillView.vue
- CORS 修复：生产默认 origin 列表，不再 `["*"]` + `credentials=True`

### P1 — 架构分离（7 项）
- 移除 Router 内 `task.get(timeout=120)` 同步阻塞 → delay() + 返回 task_id
- 新增 app/services/ 层（generate_service / article_service），Router 函数多数 ≤30 行
- Celery tasks.py（688 行）拆分为 tasks/generate.py / review.py / distill.py
- 前端 API 层拆分 5 个域文件（hotspots / articles / accounts / tasks / providers）
- 抽取 ArticleEditorDialog、PageHeader、usePaginatedList、useActiveTasks
- 启用 Pinia store（accounts / tasks 跨页共享）
- 无效 hotspot_id 显式 400 错误

### P2 — 一致性、测试与 DB（9 项）
- 数据库迁移集成（启动脚本执行 migrations）
- models / schemas 拆分包结构
- 后端测试补全（providers / scenario_configs / auth）
- LLMService 测试重写（mock gateway）
- 前端 typecheck + vitest
- 统一 UI 模式（PageHeader + v-loading）
- 合并重复 Adapter + 死代码清理
- 常量与 Enum 集中
- 结构化日志（替换 print）

### P3 — 优化与文档（5 项）
- 任务 API 统一入口
- App 布局样式拆分
- CRUD 页抽象
- 品牌与文档统一
- Celery 重试与评审链健壮性

## Capabilities

### New Capabilities
- `user-auth`: JWT 登录鉴权，User 模型，前端 LoginView + router 守卫
- `provider-api-key-security`: Provider api_key 掩码存储与响应脱敏
- `unified-database-engine`: API 与 Celery Worker 共用 database.py Engine
- `frontend-dead-code-cleanup`: 删除步骤 6 死代码 + GenerateView/DistillView 孤儿页面
- `cors-configuration`: CORS 生产安全配置
- `async-task-orchestration`: 移除 Router 内 Celery 同步阻塞
- `service-layer`: 抽取 app/services/ 业务逻辑层
- `celery-task-split`: 拆分 tasks.py 为模块化 tasks/ 包
- `frontend-api-refactor`: 前端 API 层按域拆分
- `shared-components-hooks`: 抽取可复用组件（ArticleEditorDialog, PageHeader）和 hooks
- `pinia-store`: 跨页面状态管理（accounts, tasks）
- `input-validation`: 无效 hotspot_id 显式 400 错误
- `database-migration-integration`: 启动脚本集成 SQL 迁移执行
- `model-schema-split`: models/ schemas/ 包结构拆分
- `test-coverage`: 后端 + 前端 + LLMService 测试补全及 typecheck
- `consistent-ui-patterns`: 统一列表页 UI 模式（PageHeader + v-loading）
- `code-deduplication`: 合并重复 Adapter + 删除未引用死代码
- `constants-enums`: 魔法字符串集中到 constants.py / enums.py
- `structured-logging`: logging 模块替换 print
- `api-unification`: 任务 API 双入口统一
- `layout-extraction`: App.vue 布局拆分为 components/layout/
- `crud-abstraction`: CRUD 页面通用逻辑抽取
- `brand-consistency`: 统一品牌命名与文档
- `celery-resilience`: Celery 自动重试与失败策略

### Modified Capabilities
- 无：此为全新变更，不修改已有 openspec spec

## Impact

- **后端**：ArticleGeneratorService/app/ 全目录受影响（新增 auth / deps / services / tasks/ 包；修改 main.py / api/* / models / schemas / tasks）
- **LLMService**：测试重写 + adapter 合并
- **前端**：新增 LoginView / components / hooks / store；删除 2 个孤儿页面；API 层 5 文件拆分；router 加守卫
- **依赖新增**：python-jose[cryptography]、passlib[bcrypt]
- **配置新增**：JWT_SECRET、ACCESS_TOKEN_EXPIRE_MINUTES、SEED_USERNAME、SEED_PASSWORD；CORS_ORIGINS 修改
- **BREAKING**：T01 后所有受保护 API 需 Bearer token，无 token 请求返回 401
