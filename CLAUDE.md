# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

ArticleGenerator 是一个半自动化内容创作辅助系统，流程：**热点抓取 → 人工选择 → 智能生成 → 评审微调 → 发布辅助**。

## 常用命令

### 启动/停止

```bash
./scripts/start.sh      # 一键启动所有服务（含 Redis、后端、Celery、前端）
./scripts/stop.sh       # 停止所有服务
./scripts/run_all_tests.sh  # 运行全部测试
```

### 分模块运行

```bash
# LLM 模型服务（:8001）
cd LLMService && pip install -r requirements.txt && uvicorn app.main:app --host 0.0.0.0 --port 8001

# 后端 API（:8000）
cd ArticleGeneratorService && pip install -r requirements.txt && uvicorn app.main:app --host 0.0.0.0 --port 8000

# Celery Worker（需 Redis 运行）
cd ArticleGeneratorService && celery -A app.tasks:celery_app worker -l info

# 热点抓取（单次）
cd HotspotCrawler && pip install -r requirements.txt && python run_crawl.py

# 管理后台（:5173，Vite 开发服务器代理 /api → :8000）
cd ArticleGeneratorAdm && npm install && npm run dev
```

### 测试

```bash
# 后端 API 测试（pytest）
cd ArticleGeneratorService && pytest tests/ -v

# LLM 服务测试（pytest）
cd LLMService && pytest tests/ -v

# 热点抓取测试（pytest）
cd HotspotCrawler && pytest tests/ -v

# 前端测试（vitest）
cd ArticleGeneratorAdm && npx vitest run
```

### Docker Compose

```bash
docker-compose up -d     # 启动 Redis、MySQL、API、Celery、LLM（管理后台需单独 npm run dev）
```

## 架构

### 模块与职责

| 模块 | 技术 | 职责 |
|------|------|------|
| `ArticleGeneratorService/` | FastAPI + SQLAlchemy + Celery | 后端 API（CRUD + 任务编排），Celery 消费 Redis 队列异步调用 LLM |
| `LLMService/` | FastAPI + transformers + peft | 模型推理（`/generate`、`/refine`），支持模拟模式和真实 LoRA 推理 |
| `HotspotCrawler/` | httpx + 免费聚合 API | 从微博/知乎/百度/抖音/B站抓取热点，POST 到后端 `/api/hotspots/batch` |
| `ArticleGeneratorAdm/` | Vue 3 + Element Plus + Vite | 管理后台 SPA，6 个页面（热点列表/任务列表/评审/待发布/热点源管理/账号管理） |
| `ArticleGeneratorDatabase/` | SQL 迁移脚本 | MySQL 表结构，按 `001_`、`002_` 序号执行 |

### 调用关系

```
HotspotCrawler ──POST──► ArticleGeneratorService ──HTTP──► LLMService (:8001)
     │                         │    │
     │                    Redis    SQLAlchemy
     │                         │    │
ArticleGeneratorAdm ──Vite proxy──┘    ▼
  (:5173)                       SQLite/MySQL
```

- 前端通过 Vite 代理 `/api` 到后端 `:8000`
- 后端通过 Celery（Redis 作为 broker）异步调用 LLM 服务
- LLM 服务默认 `MOCK_MODE=true`（无需 GPU），设为 `false` 后加载真实模型 + LoRA

### 核心数据流

1. 抓取热点 → POST `/api/hotspots/batch` → 写入 `hotspots` 表（status=unselected）
2. 前端多选热点 + 选账号 → POST `/api/generate/trigger` → 创建 Celery 任务 → 写入 `generation_tasks` 表
3. Celery Worker 消费任务 → 调 LLM `/generate` → 写入 `articles` 表（status=pending_review）
4. 前端评审页通过/拒绝 → PATCH `/api/articles/{id}/status`
5. 微调 → POST `/api/generate/refine/{id}` → Celery → LLM `/refine` → 更新文章 content
6. 已通过文章 → 复制全文 → 人工粘贴发布 → 标记 published

### 数据库表（6 张）

- `hotspots` — 热点（title, source, heat, url, status）
- `accounts` — 账号风格（platform, account_name, lora_path, sample_articles）
- `articles` — 文章（hotspot_id FK, account_id FK, content, status, refine_history JSON）
- `generation_tasks` — 生成任务（task_id UNIQUE, status, article_id）
- `refine_tasks` — 微调任务（task_id UNIQUE, article_id FK）
- `hotspot_sources` — 热点源配置（name, type, config JSON, enabled）

### 后端路由

| 路由 | 文件 | 职责 |
|------|------|------|
| `/api/accounts` | `app/api/accounts.py` | 账号 CRUD |
| `/api/hotspots` | `app/api/hotspots.py` | 热点列表/批量创建/手动抓取 |
| `/api/hotspot-sources` | `app/api/hotspot_sources.py` | 热点源配置 CRUD |
| `/api/articles` | `app/api/articles.py` | 文章列表/详情/状态更新 |
| `/api/generate` | `app/api/generate.py` | 触发生成/微调、任务状态查询/取消 |

### 前端路由

| 路径 | 页面 | 用途 |
|------|------|------|
| `/` | HotspotsView | 热点列表、多选、批量生成 |
| `/tasks` | TasksView | 生成任务状态、取消 |
| `/review` | ReviewView | 文章评审（通过/拒绝/微调） |
| `/publish` | PublishView | 待发布列表、复制、标记已发布 |
| `/hotspot-sources` | HotspotSourcesView | 热点源配置管理 |
| `/accounts` | AccountsView | 账号风格管理 |

## 配置与环境变量

- **后端** (`ArticleGeneratorService/.env`)：`DATABASE_URL`（默认 sqlite）、`REDIS_URL`、`LLM_SERVICE_URL`
- **LLM** (`LLMService/.env`)：`MOCK_MODE`（默认 true）、`MODEL_PATH`、`LORA_PATH`
- **抓取** (`HotspotCrawler/.env`)：`API_BASE`（后端地址）、`CRAWL_SOURCES`（逗号分隔源列表）
- 各模块均提供 `.env.example` 作为参考

## 项目约定

- 注释/回复语言：中文
- 提交格式：语义化，如 `feat: 新增热点抓取`、`fix: 修正文章生成超时`
- 分支：`main` 主分支，`feature/xxx` 功能分支，`fix/xxx` 修复分支
- 前端组件：页面逻辑抽离为 `components/` 子组件，公用工具放 `utils/`、`api/`、`store/`，业务 hooks 放 `hooks/`
- 文件存放：开发计划 → `.cursor/plans/`，验证报告 → `.cursor/reports/`，设计文档 → `docs/`，数据库迁移 → `ArticleGeneratorDatabase/migrations/`

## 已知陷阱

### SQLite 数据库路径
数据库文件 `article_generator.db` 的路径相对于进程 **CWD** 解析。所有数据库操作（种子脚本、直接查询、pytest）必须从 `ArticleGeneratorService/` 目录运行，否则会创建/读取错误的数据库文件。

### LLM 网关适配器注册
新增 Provider 后必须：(a) 在 `LLMService/app/adapters/__init__.py` 中导入对应的 adapter 模块，(b) 通过 `register("provider名称")` 注册。OpenAI 兼容厂商（如 CrazyRouter）直接注册为 OpenAIAdapter 别名。

### CrazyRouter 模型配置
- **可用模型：** `deepseek-v4-pro`（中文创作首选）、`deepseek-chat`（评审任务）
- **不可用：** `claude-sonnet-4-20250514`（该名称在 CrazyRouter 上无效）
- 场景→模型映射在 `scenario_configs` 表中，通过 `/generate` 页面的「场景配置」管理

### 前端组件测试限制
jsdom 环境不支持 Vue SFC 的动态 `import()`，会导致 `InvalidCharacterError`。组件级测试需改为浏览器手动验证。API client 和纯 JS/TS 模块测试正常。

### 生成 Prompt 分层架构
generate 场景采用 4 层结构：(1) 角色定义 (2) 硬约束/禁用词 (3) `{{style_profile}}` 占位 (4) 任务指令 + `{{hotspot_title}}`。禁用词：总的来说、综上所述、首先其次最后、换言之、从某种程度上、随着、在当前。修改 Prompt 后需通过 Celery 重新生成验证效果。

## Agent skills

### Issue tracker

Issues live as GitHub issues, accessed via the `gh` CLI. See `docs/agents/issue-tracker.md`.

### Triage labels

Default label vocabulary: `needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context layout: one `CONTEXT.md` + `docs/adr/` at the repo root. See `docs/agents/domain.md`.
