# CLAUDE.md

<!-- 加载顺序：AI agent 应先加载服务级 CLAUDE.md，再加载本文件获取全局约束 -->

本文件为 Claude Code 提供项目级架构指导和全局约束。领域术语见 [CONTEXT.md](CONTEXT.md)；各服务详情见对应 `CLAUDE.md`。

## 约束文件索引

| 文件 | 路径 | 内容 |
|------|------|------|
| 领域术语表 | `CONTEXT.md` | 核心领域概念 + 按服务区分的术语 |
| 后端 CLAUDE.md | `ArticleGeneratorService/CLAUDE.md` | 后端 API 专用命令、路由、配置、陷阱 |
| LLM CLAUDE.md | `LLMService/CLAUDE.md` | LLM 推理专用命令、模型配置、陷阱 |
| 前端 CLAUDE.md | `ArticleGeneratorAdm/CLAUDE.md` | 管理后台专用命令、页面路由、组件约定、陷阱 |
| 抓取 CLAUDE.md | `HotspotCrawler/CLAUDE.md` | 热点抓取专用命令、源配置、陷阱 |
| 数据库 CLAUDE.md | `ArticleGeneratorDatabase/CLAUDE.md` | 迁移命令、表结构、迁移约定 |
| 后端约束 | `ArticleGeneratorService/.claude/` | 后端服务级设置 |
| LLM 约束 | `LLMService/.claude/` | LLM 服务级设置 |
| 前端约束 | `ArticleGeneratorAdm/.claude/` | 前端服务级设置 |
| 抓取约束 | `HotspotCrawler/.claude/` | 抓取服务级设置 |
| 数据库约束 | `ArticleGeneratorDatabase/.claude/` | 数据库服务级设置 |

## 项目概述

ArticleGenerator 是一个半自动化内容创作辅助系统，流程：**热点抓取 → 人工选择 → 智能生成 → 评审微调 → 发布辅助**。

## Agent 工具

| 文档 | 路径 | 内容 |
|------|------|------|
| Issue Tracker | `docs/agents/issue-tracker.md` | 使用 `gh` CLI 管理 GitHub Issues |
| Triage Labels | `docs/agents/triage-labels.md` | 标签词汇：`needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix` |
| Domain Docs | `docs/agents/domain.md` | 单上下文布局：`CONTEXT.md` + `docs/adr/` |

## 服务导航

| 服务 | 路径 | 技术栈 | 职责 |
|------|------|--------|------|
| 后端 API | `ArticleGeneratorService/` | FastAPI + SQLAlchemy + Celery | REST API + 任务编排，Celery 消费 Redis 队列异步调用 LLM |
| LLM 推理 | `LLMService/` | FastAPI + transformers + peft | 模型推理（`/generate`、`/refine`），支持 Mock 和真实 LoRA |
| 管理后台 | `ArticleGeneratorAdm/` | Vue 3 + Element Plus + Vite | 6 页面 SPA，Vite 代理 `/api` → `:8000` |
| 热点抓取 | `HotspotCrawler/` | httpx + 免费聚合 API | 多平台热点抓取，POST 到后端 `/api/hotspots/batch` |
| 数据库迁移 | `ArticleGeneratorDatabase/` | SQL 迁移脚本 | MySQL 表结构，按 `001_`、`002_` 序号执行 |

## 调用关系

```
HotspotCrawler ──POST──► ArticleGeneratorService ──HTTP──► LLMService (:8001)
     │                         │    │
     │                    Redis    SQLAlchemy
     │                         │    │
ArticleGeneratorAdm ──Vite proxy──┘    ▼
  (:5173)                       SQLite/MySQL
```

## 核心数据流

1. 抓取热点 → POST `/api/hotspots/batch` → 写入 `hotspots` 表（status=unselected）
2. 前端多选热点 + 选账号 → POST `/api/generate/trigger` → 创建 Celery 任务
3. Celery Worker → LLM `/generate` → 写入 `articles` 表（status=pending_review）
4. 前端评审通过/拒绝 → PATCH `/api/articles/{id}/status`
5. 微调 → POST `/api/generate/refine/{id}` → Celery → LLM `/refine`
6. 已通过文章 → 复制全文 → 人工粘贴发布

## 常用命令

### 一键启停

```bash
./scripts/start.sh      # 启动所有服务（Redis → 后端 → Celery → 前端）
./scripts/stop.sh       # 停止所有服务
./scripts/run_all_tests.sh  # 运行全部测试
```

### Docker Compose

```bash
docker-compose up -d     # 启动 Redis、MySQL、API、Celery、LLM
```

各服务专用命令见对应 `CLAUDE.md`。

## 项目约定

- 注释/回复语言：中文
- 提交格式：语义化，如 `feat: 新增热点抓取`、`fix: 修正文章生成超时`
- 分支：`main` 主分支，`feature/xxx` 功能分支，`fix/xxx` 修复分支
- 文件存放：开发计划 → `.cursor/plans/`，验证报告 → `.cursor/reports/`，设计文档 → `docs/`
- **内容原则**：一处声明，多处引用。不在多个文件中重复相同内容。

## 全局陷阱（细节见各服务 CLAUDE.md）

| 陷阱 | 涉及服务 | 详见 |
|------|----------|------|
| SQLite 数据库路径相对于 CWD 解析，必须从正确目录运行 | 后端 | `ArticleGeneratorService/CLAUDE.md` |
| 前端变更必须浏览器验证，禁止仅依赖 build+test | 前端 | `ArticleGeneratorAdm/CLAUDE.md` |
| 禁止未经授权删除数据库文件或数据 | 数据库 | `ArticleGeneratorDatabase/CLAUDE.md` |
| LLM Provider 新增后必须注册 Adapter | LLM | `LLMService/CLAUDE.md` |
