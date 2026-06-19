# CLAUDE.md 文件结构整理 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将项目单一根 CLAUDE.md 拆分为全局概述 + 5 个服务级 CLAUDE.md + 5 个服务级 .claude/ 目录

**Architecture:** 根 CLAUDE.md 保留项目级架构导航和全局约定；各服务 CLAUDE.md 包含模块专用命令、路由、配置和陷阱；.claude/ 目录为服务级约束文件提供容器

**Tech Stack:** 纯 Markdown 文档，无代码变更

---

## 文件结构

```
ArticleGenerator/
├── CLAUDE.md                          ← [修改] 精简为项目级概述 (~80行)
├── ArticleGeneratorService/
│   ├── CLAUDE.md                      ← [新建] 后端 API 服务
│   └── .claude/                       ← [新建] 含 .gitkeep
├── LLMService/
│   ├── CLAUDE.md                      ← [新建] LLM 推理服务
│   └── .claude/                       ← [新建] 含 .gitkeep
├── ArticleGeneratorAdm/
│   ├── CLAUDE.md                      ← [新建] 管理后台前端
│   └── .claude/                       ← [新建] 含 .gitkeep
├── HotspotCrawler/
│   ├── CLAUDE.md                      ← [新建] 热点抓取服务
│   └── .claude/                       ← [新建] 含 .gitkeep
└── ArticleGeneratorDatabase/
    ├── CLAUDE.md                      ← [新建] 数据库迁移
    └── .claude/                       ← [新建] 含 .gitkeep
```

---

### Task 1: 创建 .claude/ 目录骨架

**Files:**
- Create: `ArticleGeneratorService/.claude/.gitkeep`
- Create: `LLMService/.claude/.gitkeep`
- Create: `ArticleGeneratorAdm/.claude/.gitkeep`
- Create: `HotspotCrawler/.claude/.gitkeep`
- Create: `ArticleGeneratorDatabase/.claude/.gitkeep`

- [ ] **Step 1: 创建目录和 .gitkeep 文件**

```bash
for dir in ArticleGeneratorService LLMService ArticleGeneratorAdm HotspotCrawler ArticleGeneratorDatabase; do
  mkdir -p "$dir/.claude"
  touch "$dir/.claude/.gitkeep"
done
```

- [ ] **Step 2: 验证目录结构**

```bash
for dir in ArticleGeneratorService LLMService ArticleGeneratorAdm HotspotCrawler ArticleGeneratorDatabase; do
  echo "$dir/.claude/: $(ls $dir/.claude/)"
done
```

Expected: 每行显示 `.gitkeep`

- [ ] **Step 3: 提交**

```bash
git add ArticleGeneratorService/.claude/ LLMService/.claude/ ArticleGeneratorAdm/.claude/ HotspotCrawler/.claude/ ArticleGeneratorDatabase/.claude/
git commit -m "feat: 为各服务创建 .claude/ 目录骨架"
```

---

### Task 2: 重构根 CLAUDE.md

**Files:**
- Modify: `CLAUDE.md` (全文替换)
- Reference: openspec specs `service-claude-md/spec.md` (场景要求根 CLAUDE.md ≤ 100 行)

- [ ] **Step 1: 写新的根 CLAUDE.md**

用以下内容全文替换 `CLAUDE.md`：

```markdown
# CLAUDE.md

本项目为 Claude Code 提供代码库指导。本文件覆盖项目级架构；各服务详情见服务级 `CLAUDE.md`。

## 项目概述

ArticleGenerator 是一个半自动化内容创作辅助系统，流程：**热点抓取 → 人工选择 → 智能生成 → 评审微调 → 发布辅助**。

## 服务导航

| 服务 | 路径 | CLAUDE.md | 职责 |
|------|------|-----------|------|
| 后端 API | `ArticleGeneratorService/` | [CLAUDE.md](ArticleGeneratorService/CLAUDE.md) | FastAPI + SQLAlchemy + Celery 后端 |
| LLM 推理 | `LLMService/` | [CLAUDE.md](LLMService/CLAUDE.md) | 模型推理 + LoRA |
| 管理后台 | `ArticleGeneratorAdm/` | [CLAUDE.md](ArticleGeneratorAdm/CLAUDE.md) | Vue 3 + Element Plus 前端 SPA |
| 热点抓取 | `HotspotCrawler/` | [CLAUDE.md](HotspotCrawler/CLAUDE.md) | 多平台热点聚合抓取 |
| 数据库迁移 | `ArticleGeneratorDatabase/` | [CLAUDE.md](ArticleGeneratorDatabase/CLAUDE.md) | MySQL 表结构迁移脚本 |

## 调用关系

```
HotspotCrawler ──POST──► ArticleGeneratorService ──HTTP──► LLMService (:8001)
     │                         │    │
     │                    Redis    SQLAlchemy
     │                         │    │
ArticleGeneratorAdm ──Vite proxy──┘    ▼
  (:5173)                       SQLite/MySQL
```

## 常用命令

### 一键启停

```bash
./scripts/start.sh      # 启动所有服务（Redis → 后端 → Celery → 前端）
./scripts/stop.sh       # 停止所有服务
./scripts/run_all_tests.sh  # 运行全部测试
```

### Docker Compose

```bash
docker-compose up -d     # 启动 Redis、MySQL、API、Celery、LLM（管理后台需单独 npm run dev）
```

## 核心数据流

1. 抓取热点 → POST `/api/hotspots/batch` → 写入 `hotspots` 表
2. 前端多选热点 + 选账号 → POST `/api/generate/trigger` → Celery 任务
3. Celery Worker → LLM `/generate` → 写入 `articles` 表
4. 前端评审通过/拒绝 → PATCH `/api/articles/{id}/status`
5. 微调 → POST `/api/generate/refine/{id}` → Celery → LLM `/refine`
6. 已通过文章 → 复制全文 → 人工粘贴发布

## 项目约定

- 注释/回复语言：中文
- 提交格式：语义化，如 `feat: 新增热点抓取`、`fix: 修正文章生成超时`
- 分支：`main` 主分支，`feature/xxx` 功能分支，`fix/xxx` 修复分支
- 文件存放：开发计划 → `.cursor/plans/`，验证报告 → `.cursor/reports/`，设计文档 → `docs/`，数据库迁移 → `ArticleGeneratorDatabase/migrations/`

## 跨服务陷阱

### SQLite 数据库路径
数据库文件 `article_generator.db` 的路径相对于进程 **CWD** 解析。所有数据库操作（种子脚本、直接查询、pytest）必须从 `ArticleGeneratorService/` 目录运行。

### 数据库操作红线
**禁止未经人工授权删除数据库文件或数据**（即使是 dev 环境 SQLite）。Schema 不匹配时必须使用 `ALTER TABLE` 迁移脚本。

### 前端验证铁律
前端代码变更后，必须启动 dev server 实际访问页面验证，禁止仅依赖 `npm run build` + `npm run test` 通过即声称完成。
```

- [ ] **Step 2: 验证文件行数**

```bash
wc -l CLAUDE.md
```

Expected: ≤ 100 行

- [ ] **Step 3: 提交**

```bash
git add CLAUDE.md
git commit -m "refactor: 精简根 CLAUDE.md 为项目级概述，服务细节移至各服务 CLAUDE.md"
```

---

### Task 3: 创建 ArticleGeneratorService/CLAUDE.md

**Files:**
- Create: `ArticleGeneratorService/CLAUDE.md`

- [ ] **Step 1: 写后端服务 CLAUDE.md**

```markdown
<!-- 继承自 ../CLAUDE.md 项目级架构，本文件覆盖后端 API 服务专用内容 -->

# ArticleGeneratorService — 后端 API 服务

FastAPI + SQLAlchemy + Celery 后端，提供 REST API 和异步任务编排。

## 常用命令

### 启动

```bash
cd ArticleGeneratorService
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Celery Worker

```bash
cd ArticleGeneratorService
celery -A app.tasks:celery_app worker -l info
```

### 测试

```bash
cd ArticleGeneratorService && pytest tests/ -v
```

**注意**：pytest 必须从 `ArticleGeneratorService/` 目录运行（SQLite 路径相对于 CWD 解析）。

## 架构

### 后端路由

| 路由 | 文件 | 职责 |
|------|------|------|
| `/api/accounts` | `app/api/accounts.py` | 账号 CRUD |
| `/api/hotspots` | `app/api/hotspots.py` | 热点列表/批量创建/手动抓取 |
| `/api/hotspot-sources` | `app/api/hotspot_sources.py` | 热点源配置 CRUD |
| `/api/articles` | `app/api/articles.py` | 文章列表/详情/状态更新 |
| `/api/generate` | `app/api/generate.py` | 触发生成/微调、任务状态查询/取消 |

### 数据库表（6 张）

- `hotspots` — 热点（title, source, heat, url, status）
- `accounts` — 账号风格（platform, account_name, lora_path, sample_articles）
- `articles` — 文章（hotspot_id FK, account_id FK, content, status, refine_history JSON）
- `generation_tasks` — 生成任务（task_id UNIQUE, status, article_id）
- `refine_tasks` — 微调任务（task_id UNIQUE, article_id FK）
- `hotspot_sources` — 热点源配置（name, type, config JSON, enabled）

### 数据流

1. HotspotCrawler POST `/api/hotspots/batch` → `hotspots` 表（status=unselected）
2. 前端 POST `/api/generate/trigger` → 创建 Celery 任务 → `generation_tasks` 表
3. Celery Worker 调 LLM `/generate` → `articles` 表（status=pending_review）
4. 前端 PATCH `/api/articles/{id}/status` → 通过/拒绝
5. 微调 POST `/api/generate/refine/{id}` → Celery → LLM `/refine`

## 配置

`.env` 文件（参考 `.env.example`）：

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `DATABASE_URL` | `sqlite:///./article_generator.db` | 数据库连接 |
| `REDIS_URL` | `redis://localhost:6379/0` | Celery broker |
| `LLM_SERVICE_URL` | `http://localhost:8001` | LLM 服务地址 |

## 已知陷阱

### SQLite CWD 依赖
数据库路径 `article_generator.db` 相对于进程 CWD。种子脚本、pytest、直接查询必须从 `ArticleGeneratorService/` 目录执行，否则操作错误的数据库文件。

### JWT + Crawler Key 双认证
API 使用双认证模式，按端点配置。不要使用全局中间件；在路由依赖中按需引入。

### 新增 API 端点
遵循 `app/api/` 目录结构，每个资源一个文件，Router 在 `app/main.py` 中注册。
```

- [ ] **Step 2: 提交**

```bash
git add ArticleGeneratorService/CLAUDE.md
git commit -m "feat: 添加后端 API 服务 CLAUDE.md"
```

---

### Task 4: 创建 LLMService/CLAUDE.md

**Files:**
- Create: `LLMService/CLAUDE.md`

- [ ] **Step 1: 写 LLM 服务 CLAUDE.md**

```markdown
<!-- 继承自 ../CLAUDE.md 项目级架构，本文件覆盖 LLM 推理服务专用内容 -->

# LLMService — LLM 推理服务

基于 FastAPI + transformers + peft 的模型推理服务，提供 `/generate` 和 `/refine` 端点。支持 `MOCK_MODE` 模拟和真实 LoRA 推理。

## 常用命令

### 启动

```bash
cd LLMService
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```

### 测试

```bash
cd LLMService && pytest tests/ -v
```

## 架构

### API 端点

| 端点 | 用途 |
|------|------|
| `POST /generate` | 根据热点标题 + 账号风格生成文章 |
| `POST /refine` | 根据评审意见微调已有文章 |

### 模拟模式

默认 `MOCK_MODE=true`，无需 GPU。设为 `false` 后加载真实模型 + LoRA adapter。

## 配置

`.env` 文件（参考 `.env.example`）：

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `MOCK_MODE` | `true` | 模拟模式开关 |
| `MODEL_PATH` | — | 基础模型路径（MOCK_MODE=false 时必填） |
| `LORA_PATH` | — | LoRA adapter 路径（MOCK_MODE=false 时必填） |

## 已知陷阱

### Provider Adapter 注册
新增 LLM Provider 后必须：
1. 在 `LLMService/app/adapters/__init__.py` 中导入 adapter 模块
2. 通过 `register("provider名称")` 注册
3. OpenAI 兼容厂商（如 CrazyRouter）注册为 `OpenAIAdapter` 别名

### CrazyRouter 模型
- **可用**：`deepseek-v4-pro`（中文创作首选）、`deepseek-chat`（评审任务）
- **不可用**：`claude-sonnet-4-20250514`（该名称在 CrazyRouter 上无效）
- 场景→模型映射在 `scenario_configs` 表中管理

### Generate Prompt 分层架构
generate 场景采用 4 层结构：
1. 角色定义
2. 硬约束/禁用词
3. `{{style_profile}}` 占位
4. 任务指令 + `{{hotspot_title}}`

禁用词：总的来说、综上所述、首先其次最后、换言之、从某种程度上、随着、在当前。修改 Prompt 后需通过 Celery 重新生成验证效果。

### JSON 参数解析
LLM 网关请求参数需为合法 JSON。遗留端点使用 Pydantic model 校验。
```

- [ ] **Step 2: 提交**

```bash
git add LLMService/CLAUDE.md
git commit -m "feat: 添加 LLM 推理服务 CLAUDE.md"
```

---

### Task 5: 创建 ArticleGeneratorAdm/CLAUDE.md

**Files:**
- Create: `ArticleGeneratorAdm/CLAUDE.md`

- [ ] **Step 1: 写前端管理后台 CLAUDE.md**

```markdown
<!-- 继承自 ../CLAUDE.md 项目级架构，本文件覆盖管理后台前端专用内容 -->

# ArticleGeneratorAdm — 管理后台前端

Vue 3 + Element Plus + Vite SPA，通过 Vite 代理 `/api` 到后端 `:8000`。

## 常用命令

### 启动

```bash
cd ArticleGeneratorAdm
npm install
npm run dev        # Vite dev server :5173，代理 /api → :8000
```

### 构建

```bash
npm run build      # esbuild 剥离类型不做检查
```

### 测试

```bash
npx vitest run
```

## 页面路由

| 路径 | 组件 | 用途 |
|------|------|------|
| `/` | `HotspotsView` | 热点列表、多选、批量生成 |
| `/tasks` | `TasksView` | 生成任务状态、取消 |
| `/review` | `ReviewView` | 文章评审（通过/拒绝/微调） |
| `/publish` | `PublishView` | 待发布列表、复制、标记已发布 |
| `/hotspot-sources` | `HotspotSourcesView` | 热点源配置管理 |
| `/accounts` | `AccountsView` | 账号风格管理 |

## 代码约定

- 页面逻辑抽离为 `components/` 子组件
- 公用工具：`utils/`、`api/`、`store/`
- 业务 hooks：`hooks/`
- API client 结构：`client.ts` + `types.ts` + `modules/*.ts` + `index.ts`

## 已知陷阱

### 前端验证铁律（不可绕过）

**前端代码变更后，禁止仅依赖 `npm run build` + `npm run test` 通过即声称验证完成。** 必须：

1. 启动 Vite dev server（`npm run dev`）
2. 浏览器访问受影响的页面，打开控制台
3. 确认无 `Uncaught TypeError`、`is not a function` 等运行时错误
4. 走通关键操作流程

**原因**：`npm run build` 使用 esbuild 剥离类型不做检查；App.vue 级运行时逻辑无测试覆盖。

### 组件测试限制
jsdom 不支持 Vue SFC 的动态 `import()`，会导致 `InvalidCharacterError`。组件级测试需改为浏览器手动验证。API client 和纯 JS/TS 模块测试正常。

### Vite 代理
前端请求 `/api/*` 通过 Vite 代理转发到后端 `:8000`。开发时确保后端已在 `:8000` 运行。
```

- [ ] **Step 2: 提交**

```bash
git add ArticleGeneratorAdm/CLAUDE.md
git commit -m "feat: 添加管理后台前端 CLAUDE.md"
```

---

### Task 6: 创建 HotspotCrawler/CLAUDE.md

**Files:**
- Create: `HotspotCrawler/CLAUDE.md`

- [ ] **Step 1: 写热点抓取服务 CLAUDE.md**

```markdown
<!-- 继承自 ../CLAUDE.md 项目级架构，本文件覆盖热点抓取服务专用内容 -->

# HotspotCrawler — 热点抓取服务

从微博/知乎/百度/抖音/B站等平台抓取热点，POST 到后端 `/api/hotspots/batch`。

## 常用命令

### 单次抓取

```bash
cd HotspotCrawler
pip install -r requirements.txt
python run_crawl.py
```

### 测试

```bash
cd HotspotCrawler && pytest tests/ -v
```

## 架构

### 抓取流程

1. 读取 `CRAWL_SOURCES` 环境变量（逗号分隔源列表）
2. 调用各平台免费聚合 API（基于 httpx）
3. 汇总结果，POST 到后端 `{API_BASE}/api/hotspots/batch`
4. 后端写入 `hotspots` 表（status=unselected）

## 配置

`.env` 文件（参考 `.env.example`）：

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `API_BASE` | `http://localhost:8000` | 后端 API 地址 |
| `CRAWL_SOURCES` | `weibo,zhihu,baidu,douyin,bilibili` | 抓取源列表（逗号分隔） |

## 已知陷阱

### API 格式
POST 到 `/api/hotspots/batch` 的数据格式需与后端 Pydantic model 一致。新增字段时同步更新前后端。

### 抓取频率
免费聚合 API 有频率限制。避免在短时间内重复抓取同一平台。
```

- [ ] **Step 2: 提交**

```bash
git add HotspotCrawler/CLAUDE.md
git commit -m "feat: 添加热点抓取服务 CLAUDE.md"
```

---

### Task 7: 创建 ArticleGeneratorDatabase/CLAUDE.md

**Files:**
- Create: `ArticleGeneratorDatabase/CLAUDE.md`

- [ ] **Step 1: 写数据库迁移 CLAUDE.md**

```markdown
<!-- 继承自 ../CLAUDE.md 项目级架构，本文件覆盖数据库迁移专用内容 -->

# ArticleGeneratorDatabase — 数据库迁移

MySQL 表结构迁移脚本，按序号命名（`001_`、`002_`…）。

## 常用命令

### 执行迁移

```bash
cd ArticleGeneratorDatabase
# 迁移脚本位于 migrations/ 目录，按序号顺序执行
mysql -u root -p article_generator < migrations/001_initial_schema.sql
```

## 表结构概览（6 张表）

| 表 | 用途 | 关键字段 |
|----|------|----------|
| `hotspots` | 热点数据 | title, source, heat_score, url, status |
| `accounts` | 账号风格 | platform, account_name, lora_path, sample_articles |
| `articles` | 生成文章 | hotspot_id FK, account_id FK, content, status, refine_history |
| `generation_tasks` | 生成任务 | task_id UNIQUE, status, article_id |
| `refine_tasks` | 微调任务 | task_id UNIQUE, article_id FK |
| `hotspot_sources` | 热点源配置 | name, type, config JSON, enabled |

## 迁移约定

- 脚本放在 `migrations/` 目录下
- 命名格式：`NNN_description.sql`（如 `001_initial_schema.sql`）
- 按序号升序执行，不可跳过
- 每次新增迁移需在 `migrations/README.md` 中记录变更说明
- **禁止未经授权执行 DROP TABLE / DELETE FROM 操作**（即使是开发环境）

## 已知陷阱

### CWD 依赖
后端 `DATABASE_URL` 使用相对路径时，SQLite 文件相对于 `ArticleGeneratorService/` 目录解析。本地开发与迁移脚本的 CWD 可能不一致，注意检查数据库文件位置。
```

- [ ] **Step 2: 提交**

```bash
git add ArticleGeneratorDatabase/CLAUDE.md
git commit -m "feat: 添加数据库迁移 CLAUDE.md"
```

---

### Task 8: 最终验证

- [ ] **Step 1: 确认所有文件存在**

```bash
echo "=== CLAUDE.md 文件 ==="
for f in \
  CLAUDE.md \
  ArticleGeneratorService/CLAUDE.md \
  LLMService/CLAUDE.md \
  ArticleGeneratorAdm/CLAUDE.md \
  HotspotCrawler/CLAUDE.md \
  ArticleGeneratorDatabase/CLAUDE.md; do
  [ -f "$f" ] && echo "✅ $f ($(wc -l < "$f") lines)" || echo "❌ $f MISSING"
done

echo ""
echo "=== .claude/ 目录 ==="
for d in \
  ArticleGeneratorService/.claude \
  LLMService/.claude \
  ArticleGeneratorAdm/.claude \
  HotspotCrawler/.claude \
  ArticleGeneratorDatabase/.claude; do
  [ -d "$d" ] && echo "✅ $d/ ($(ls "$d"))" || echo "❌ $d MISSING"
done
```

Expected: 所有条目显示 ✅

- [ ] **Step 2: 确认根 CLAUDE.md 包含服务导航**

```bash
grep -c "CLAUDE.md" CLAUDE.md
```

Expected: 输出 ≥ 5（每个服务一个导航链接）

- [ ] **Step 3: 确认 git status**

```bash
git status
```

Expected: working tree clean（所有变更已提交）

- [ ] **Step 4: 最终提交（如有遗漏）**

```bash
git add -A
git diff --cached --stat
# 如有遗漏文件，提交
```

---

## 自审清单

1. **Spec 覆盖**：
   - `service-claude-md`: Task 2 (根重构) + Tasks 3-7 (5 个服务文件) ✓
   - `service-claude-dir`: Task 1 (.claude/ 目录) ✓

2. **占位符检查**：无 TBD/TODO/空代码块 ✓

3. **一致性**：所有 `CLAUDE.md` 使用统一模板（继承声明 + 命名规范）✓
