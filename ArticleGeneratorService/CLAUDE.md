<!-- 加载顺序：AI agent 应先加载本文件，再加载 ../CLAUDE.md 获取全局约束 -->
<!-- 本文件中的内容为 ArticleGeneratorService 独有；全局约定见 ../CLAUDE.md -->

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

## 架构

### 后端路由

| 路由 | 文件 | 职责 |
|------|------|------|
| `/api/auth` | `app/api/auth.py` | 认证（登录、JWT） |
| `/api/accounts` | `app/api/accounts.py` | 账号 CRUD |
| `/api/distill` | `app/api/distill.py` | 风格蒸馏 |
| `/api/reference-articles` | `app/api/reference_articles.py` | 参考文章管理 |
| `/api/hotspots` | `app/api/hotspots.py` | 热点列表/批量创建/手动抓取 |
| `/api/hotspot-sources` | `app/api/hotspot_sources.py` | 热点源配置 CRUD |
| `/api/articles` | `app/api/articles.py` | 文章列表/详情/状态更新 |
| `/api/generate` | `app/api/generate.py` | 触发生成/微调、写作方向、大纲、标题、任务状态 |
| `/api/generation-logs` | `app/api/generation_logs.py` | LLM 回调日志 |
| `/api/providers` | `app/api/providers.py` | API 提供商管理 |
| `/api/scenario-configs` | `app/api/scenario_configs.py` | 场景路由配置 |
| `/api/tasks` | `app/api/tasks.py` | 统一任务查询 |

### 数据库表

数据库表结构见 `ArticleGeneratorDatabase/CLAUDE.md`。共 6 张表：hotspots, accounts, articles, generation_tasks, refine_tasks, hotspot_sources。

### 服务内数据流

核心数据流见根 `CLAUDE.md`。服务内 Celery 任务编排细节见 `app/tasks.py`。

## 配置

`.env` 文件（参考 `.env.example`）：

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `DATABASE_URL` | `sqlite:///./article_generator.db` | 数据库连接 |
| `REDIS_URL` | `redis://localhost:6379/0` | Celery broker |
| `LLM_SERVICE_URL` | `http://localhost:8001` | LLM 服务地址 |

## 已知陷阱

### SQLite CWD 依赖
数据库路径 `article_generator.db` 相对于进程 CWD 解析。种子脚本、pytest、直接查询 **必须从 `ArticleGeneratorService/` 目录执行**，否则操作错误的数据库文件。详见根 `CLAUDE.md` 全局陷阱。

### JWT + Crawler Key 双认证
API 使用双认证模式，按端点配置认证依赖。**不要**使用全局中间件；在路由依赖中按需引入。参见 `app/api/` 下各文件。

### 新增 API 端点
遵循现有模式：在 `app/api/` 下按资源创建文件 → 定义 Router（prefix + tags）→ 在 `app/main.py` 中注册。
