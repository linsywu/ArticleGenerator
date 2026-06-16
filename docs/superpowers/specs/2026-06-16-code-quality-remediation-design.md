# 代码质量修正 — 设计文档

> 基于 `docs/ai/plans/code-quality-remediation-plan.md`  
> 规范化入口：`/devflow` Full Flow  
> 日期：2026-06-16

---

## 1. 概述

对 ArticleGenerator 全栈项目执行系统性代码质量修正，覆盖安全、架构、一致性、测试、文档 5 个维度，共 27 个任务，分 P0→P1→P2→P3 四个优先级顺序执行。

## 2. P0 — 安全与正确性（T01–T06）

### T01 — JWT 鉴权基础框架

**方案**：用户名+密码 → JWT，种子用户通过 `.env` 创建。

**后端**：
- 新建 `app/models.py` 增加 `User` 表（id, username, password_hash, created_at, is_active）
- 新建 `app/auth.py`：`create_access_token()`、`verify_token()`、`get_password_hash()`、`verify_password()`
- 新建 `app/deps.py`：`get_current_user` 依赖（从 `Authorization: Bearer <token>` 解析）
- 新建 `app/api/auth.py`：`POST /api/auth/login` 返回 `{access_token, token_type: "bearer"}`
- `main.py`：注册 auth router；全局中间件：`/api/health` 白名单，其余默认需鉴权
- 依赖：`python-jose[cryptography]`、`passlib[bcrypt]`
- `.env` 新增：`JWT_SECRET`、`ACCESS_TOKEN_EXPIRE_MINUTES`、`SEED_USERNAME`、`SEED_PASSWORD`
- 启动时检查是否存在用户，无则自动用 `.env` 凭证创建种子管理员

**前端**：
- 新建 `LoginView.vue`：用户名+密码表单 → 调 `/api/auth/login` → 存 token 到 localStorage
- `router/index.ts`：`beforeEach` 守卫，无 token → 重定向 `/login`；`/login` 路由不鉴权
- `api/client.ts`：请求拦截器自动带 `Authorization: Bearer <token>`；响应拦截器 401 → 清 token → 跳 `/login`

**验收**：无 token 访问任意受保护 API 返回 401；登录后正常；token 过期后 401；`.env.example` 已更新。

### T02 — Provider api_key 脱敏存储与响应

**依赖**：T01

- `schemas.py`：新增 `mask_api_key()` 函数（`sk-***abc` 格式）；`ProviderResponse` 使用 `@validator` 掩码
- `api/providers.py`：写入时「留空=不修改」逻辑
- `api/scenario_configs.py`：同理脱敏
- LLMService 调用时通过内部 service 层取完整 key（不经过 API 响应）

**验收**：GET /api/providers 不返回完整 key；LLMService 仍能取完整 key。

### T03 — 统一数据库 Engine

- 删除 `tasks.py` 内独立 `create_engine` + `SessionLocal`
- 改为 `from app.database import SessionLocal`
- SQLite 路径改为绝对路径（`config.py` → `database.py` 拼接）

**验收**：Worker 与 API 同库读写；`CLAUDE.md` 陷阱说明仍成立。

### T04 — 修复 CreateView 步骤 6 死代码

- 删除步骤 6 模板（`CreateView.vue:162-177`）与 `submitForReview` 函数（`:310`）
- 文案改为「已加入任务中心」
- Step indicator 从 6 步减为 5 步

**验收**：无未赋值 ref；用户流程可走通且无误导按钮。

### T05 — 清理孤儿页面

- 删除 `GenerateView.vue`（617 行）、`DistillView.vue`（281 行）
- grep 确认无残留引用（router、组件 import）

**验收**：`npm run build` 通过；路由表与文件一致。

### T06 — 修复 CORS 配置

- `main.py`：`allow_origins` 改为读取 `.env` 列表，默认 `["http://localhost:5173"]`
- `allow_credentials=True` 仅在明确配置时启用
- `.env.example` 更新说明

**验收**：前端 dev 可跨域；不再 `["*"]` + `credentials=True`。

---

## 3. P1 — 架构与性能（T07–T13）

### T07 — 移除 Router 内 Celery 同步阻塞

**依赖**：T03

- `api/generate.py`：三处 `task.get(timeout=120)` 改为 `task.delay()` → 立即返回 `{task_id, status: "pending"}`
- 前端 `CreateView.vue` 轮询任务状态（已有 TaskCenterView 可复用）

**验收**：API 无 `task.get(timeout=...)`；端到端创建流程可用。

### T08 — 抽取 Service 层

- 新建 `app/services/generate_service.py`：生成触发编排、热点校验
- 新建 `app/services/article_service.py`：文章状态机（通过/拒绝/微调查询）
- `api/generate.py`、`api/articles.py` 瘦身：Router 函数多数 ≤30 行

**验收**：pytest 现有用例全绿。

### T09 — 拆分 Celery tasks

**依赖**：T08

- 新建 `app/celery_app.py`：Celery 实例
- 新建 `app/tasks/generate.py`、`tasks/review.py`、`tasks/distill.py`
- 提取重复 JSON 解析到 `app/utils/json_parse.py`
- 原 `app/tasks.py`（688 行）删除

**验收**：`celery -A app.celery_app worker` 可启动；任务名不变或文档化。

### T10 — 前端 API 层重构

**依赖**：T01

- `api/client.ts`：仅保留 axios 实例 + 拦截器（含 JWT token）
- 新建 `api/hotspots.ts`、`api/articles.ts`、`api/accounts.ts`、`api/tasks.ts`、`api/providers.ts`
- `api/index.ts` 聚合导出

**验收**：原有导入可用；拦截器统一 `ElMessage.error` + 401 处理。

### T11 — 抽取核心前端组件与 hooks

**依赖**：T04、T05、T10

- 新建 `components/ArticleEditorDialog.vue`：合并 ReviewView/PublishView/CreateView 中文章对话框
- 新建 `components/PageHeader.vue`：统一页面标题区
- 新建 `hooks/usePaginatedList.ts`：分页列表通用 hook
- 新建 `hooks/useActiveTasks.ts`：TaskCenterBell 轮询逻辑
- `App.vue` 瘦身（目标 <250 行）

**验收**：三处文章对话框合并为一组件；`App.vue` <250 行。

### T12 — 启用 Pinia Store

**依赖**：T10、T11

- 新建 `store/accounts.ts`：账号列表跨页缓存
- 新建 `store/tasks.ts`：运行中任务跨页共享
- 各 View 移除独立 fetch，改用 store

**验收**：切换页面不重复请求账号列表。

### T13 — 无效 hotspot_id 显式错误

- `api/generate.py`（或 service）：触发时校验全部 id
- 缺失则 400 + `{detail: "...", invalid_ids: [...]}`

**验收**：测试用例覆盖部分无效 id。

---

## 4. P2 — 一致性、测试与 DB（T14–T22）

### T14 — 数据库迁移集成

- `scripts/start.sh`：启动前执行 `ArticleGeneratorDatabase/migrations/`（按序号）
- `docker-compose.yml`：entrypoint 同
- `create_all` 降级为仅 dev 快捷方式

**验收**：空库启动后表结构与 migrations 一致。

### T15 — 拆分 models / schemas

- `models/` 包：`__init__.py`、`hotspot.py`、`article.py`、`account.py`、`task.py`、`user.py`、`provider.py`
- `schemas/` 包：同理按领域拆分
- 全项目 import 更新

**验收**：pytest 全绿；无单文件 >200 行。

### T16 — 后端测试补全

**依赖**：T02、T08

- 新增 `tests/test_providers.py`、`tests/test_scenario_configs.py`、`tests/test_auth.py`
- 修复 `conftest.py` 清表列表覆盖全部 ORM 模型

**验收**：`pytest tests/ -v` 全过。

### T17 — 重写 LLMService 测试

- mock gateway 调用；删除 `mock_mode` 相关断言
- 新建 `tests/test_gateway.py`
- `requirements.txt` 加 pytest

**验收**：`cd LLMService && pytest tests/ -v` 全过。

### T18 — 前端测试与 typecheck

**依赖**：T10

- 重写 `router.test.ts`（import routes 而非硬编码）
- `format.ts` 单测
- `package.json` 增加 `"typecheck": "vue-tsc --noEmit"`
- 消除关键 `as any`

**验收**：`npm run test` + `npm run typecheck` 通过。

### T19 — 统一前端 UI 模式

**依赖**：T11

- 全部列表页使用 `PageHeader` + `v-loading`
- 修复 `TasksView` 亮色内联样式
- `ProvidersView` 错误处理补全

**验收**：三页视觉一致；无 `#f5f7fa` 硬编码。

### T20 — 合并重复 Adapter + 死代码清理

**范围**：LLMService + ArticleGeneratorService

- OpenAI 兼容基类（减少 adapter 重复）
- 删 `generator.py` mock、未用 `get_db_session`
- `gateway` Schema 移至 `schemas.py`

**验收**：grep 无引用死代码；adapter 测试通过。

### T21 — 常量与 Enum 集中

- `app/constants.py`：超时、默认字数、分页上限
- `app/enums.py`：文章状态、任务状态
- 业务代码消除魔法字符串（测试 fixture 允许）

**验收**：业务代码无散落字符串字面量。

### T22 — 结构化日志

- `app/logging_config.py`：统一格式（时间戳、级别、模块）
- api、tasks、gateway 替换 `print` → `logger.info/warning/error`
- 敏感信息不入日志（api_key 等自动掩码）

**验收**：启动后日志格式统一。

---

## 5. P3 — 优化与文档（T23–T27）

### T23 — 任务 API 统一入口

- 评估 `/api/generate/tasks/*` 与 `/api/tasks/unified` 双入口
- ADR 或 README 说明唯一推荐 API

**验收**：文档说明清晰。

### T24 — 拆分 App 布局样式

**依赖**：T11

- `styles/layout.css`：侧边栏、内容区布局
- `components/layout/AppSidebar.vue`：侧边栏导航
- `components/layout/TaskCenterBell.vue`：任务铃铛
- `App.vue` 以组合为主

**验收**：`App.vue` 以组合为主，布局逻辑不在组件内。

### T25 — CRUD 页抽象

**依赖**：T11、T19

- `hooks/useCrudDialog.ts`：通用 CRUD 对话框逻辑
- 改造 Providers / HotspotSources / ScenarioConfigs 三页

**验收**：三页各减少 30%+ 代码。

### T26 — 品牌与文档统一

- 统一「墨斋」命名：`index.html` title、侧边栏、README
- `ArticleGeneratorAdm/README.md` 补充架构与目录说明

**验收**：三处一致。

### T27 — Celery 重试与评审链健壮性

**依赖**：T09

- `autoretry_for` 配置
- 失败策略文档化
- 评审评分解析改进

**验收**：集成测试或手动用例文档。

---

## 6. 执行顺序

```
P0: T01 → T02 → T03 → T04 → T05 → T06
P1: T07 → T08 → T09 → T10 → T11 → T12 → T13
P2: T14 → T15 → T16/T17/T18（可并行）→ T19 → T20 → T21 → T22
P3: T23 → T24 → T25 → T26 → T27
```

每个任务独立 commit。完成一个 → 更新进度表 → 跑验收测试 → 下一项。

## 7. 新增依赖

| 模块 | 包 | 用途 |
|------|-----|------|
| 后端 | `python-jose[cryptography]` | JWT 签发/验证 |
| 后端 | `passlib[bcrypt]` | 密码哈希 |
| 后端 | `bcrypt` | passlib bcrypt 后端 |

## 8. 环境变量变更

```bash
# T01 新增
JWT_SECRET=<随机生成>
ACCESS_TOKEN_EXPIRE_MINUTES=1440
SEED_USERNAME=admin
SEED_PASSWORD=<初始密码>

# T06 修改
CORS_ORIGINS=http://localhost:5173    # 原为 *
```
