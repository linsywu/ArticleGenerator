# ArticleGenerator 实施阶段报告（阶段 2-8）

## 实施时间

按开发计划执行，完成阶段 2 至阶段 8 的核心功能实现。

## 已完成内容

### 1. 数据库（ArticleGeneratorDatabase）

- `migrations/001_create_tables.sql`：热点表、文章表、账号表、热点源表、生成任务表
- 支持 MySQL，开发环境可用 SQLite（通过 SQLAlchemy 自动适配）

### 2. 后端服务（ArticleGeneratorService）

- FastAPI + SQLAlchemy + Celery
- 账号管理 CRUD：`/api/accounts`
- 热点源配置：`/api/hotspot-sources`
- 热点列表与批量创建：`/api/hotspots`、`/api/hotspots/batch`
- 文章列表与状态更新：`/api/articles`、`/api/articles/{id}/status`
- 生成触发：`/api/generate/trigger`、`/api/generate/refine/{id}`、`/api/generate/task/{task_id}`

### 3. 模型服务（LLMService）

- FastAPI 封装 `/generate`、`/refine`
- 模拟模式（MOCK_MODE=true）：无需 GPU，返回模板内容，用于联调

### 4. 热点抓取（HotspotCrawler）

- 使用免费聚合 API（cenguigui.cn）抓取微博、知乎、百度等热榜
- `run_crawl.py` 抓取并 POST 到后端 `/api/hotspots/batch`
- 支持去重、热度解析

### 5. 管理后台（ArticleGeneratorAdm）

- Vue 3 + Vite + Element Plus + TypeScript
- 热点列表页：多选、批量生成、账号选择
- 文章评审页：查看、通过、拒绝、微调
- 待发布页：复制全文、标记已发布
- 账号管理页：新增、删除

### 6. Docker 编排

- `docker-compose.yml`：Redis、MySQL、API、Celery、LLM
- 各模块 Dockerfile

## 文件存放

按 `.cursor/rules/file-placement.mdc` 约定：

- 本报告存放于 `.cursor/reports/`
- 开发计划于 `.cursor/plans/`
- 数据库迁移于 `ArticleGeneratorDatabase/migrations/`

## 待人工配置项

- 真实 LLM：需配置 GPU、模型路径、LoRA，并设置 `MOCK_MODE=false`
- 热点源 API Key：若使用天行数据、聚合数据等付费 API，需在热点源配置中填写
- 生产环境：建议使用 MySQL、配置 CORS、设置访问密码
