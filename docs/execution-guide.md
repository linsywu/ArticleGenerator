# ArticleGenerator 项目执行说明

本文档提供将整个项目跑起来的详细步骤。

---

## 一、环境要求

| 依赖 | 版本/要求 |
|------|-----------|
| Python | 3.10+ |
| Node.js | 16+（推荐 18+） |
| Redis | 7.x（用于 Celery 消息队列） |
| pip / npm | 最新版 |

**可选**：Docker（用于 Redis 或全量 Docker 部署）

---

## 二、首次运行：完整流程

### 步骤 0：进入项目根目录

```bash
cd /path/to/ArticleGenerator
```

### 步骤 1：启动 Redis

Redis 为 Celery 消息队列所必需，任选其一：

**方式 A：Docker（推荐）**

```bash
docker run -d --name redis-article -p 6379:6379 redis:7-alpine
```

**方式 B：本地安装**

- macOS: `brew install redis && brew services start redis`
- Ubuntu: `sudo apt install redis-server && sudo systemctl start redis`

验证：`redis-cli ping` 应返回 `PONG`。

---

### 步骤 2：启动 LLM 模型服务

**模拟模式**（默认，无需 GPU）：

```bash
cd LLMService
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8001
```

**真实模式**（需 GPU 与模型）：在 `LLMService` 目录创建 `.env`，设置 `MOCK_MODE=false`、`MODEL_PATH=/path/to/model`，然后同上启动。

保持终端运行。验证：访问 http://localhost:8001 应看到 `{"message":"LLM Service","mock_mode":true}`（模拟）或 `mock_mode:false`（真实）。

---

### 步骤 3：启动后端 API

**新开一个终端**：

```bash
cd ArticleGeneratorService
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

默认使用 SQLite（`./article_generator.db`），无需额外配置。  
验证：访问 http://localhost:8000/docs 可打开 API 文档。

---

### 步骤 4：启动 Celery Worker

**再开一个终端**：

```bash
cd ArticleGeneratorService
celery -A app.tasks:celery_app worker -l info
```

需确保 Redis 已启动。看到 `celery@xxx ready` 即表示正常。

---

### 步骤 5：抓取热点

**再开一个终端**：

```bash
cd HotspotCrawler
pip install -r requirements.txt
python run_crawl.py
```

输出类似 `{'created': 30, 'total': 30}` 表示热点已写入后端。

---

### 步骤 6：启动管理后台

**再开一个终端**：

```bash
cd ArticleGeneratorAdm
npm install
npm run dev
```

访问 http://localhost:5173 打开管理后台。

---

### 步骤 7：使用流程

1. **账号管理**：左侧菜单「账号管理」→ 新增账号（如平台：公众号，账号名：测试）
2. **热点列表**：左侧「热点列表」→ 勾选热点 → 点击「批量生成」→ 选择账号 → 确认
3. **文章评审**：左侧「文章评审」→ 查看、通过/拒绝或微调
4. **待发布**：左侧「待发布」→ 复制全文、标记已发布

---

## 三、端口一览

| 服务 | 端口 |
|------|------|
| 管理后台 | 5173 |
| 后端 API | 8000 |
| LLM 服务 | 8001 |
| Redis | 6379 |

---

## 四、环境变量（可选）

### ArticleGeneratorService

在 `ArticleGeneratorService` 目录创建 `.env`：

```
DATABASE_URL=sqlite:///./article_generator.db
REDIS_URL=redis://localhost:6379/0
LLM_SERVICE_URL=http://localhost:8001
```

### HotspotCrawler

在 `HotspotCrawler` 目录创建 `.env`：

```
API_BASE=http://localhost:8000
CRAWL_SOURCES=weibo,zhihu
```

### LLMService

默认 `MOCK_MODE=true`，无需配置。真实推理时：

1. 创建 `LLMService/.env`，设置：
   - `MOCK_MODE=false`
   - `MODEL_PATH=/path/to/chatglm3-6b`（必填）
   - `LORA_PATH=/path/to/lora`（可选）
2. 确保已安装 `torch`、`transformers`、`peft`（`pip install -r requirements.txt`）
3. 账号的 LoRA 路径在管理后台「账号管理」中配置，生成时自动传递

---

## 五、常见问题

### 1. Celery 报错 `ConnectionRefusedError`

说明 Redis 未启动或地址错误，检查 Redis 是否运行，以及 `REDIS_URL` 配置。

### 2. 热点列表为空

先执行 `python run_crawl.py` 抓取热点；若后端未启动，抓取会失败。

### 3. 生成文章一直“待评审”

检查 Celery Worker 是否在运行；若 LLM 服务未启动，生成任务会失败。

### 4. 前端请求 404 或跨域

确认后端在 8000 端口运行；开发时 Vite 会代理 `/api` 到后端，无需额外 CORS 配置。

### 5. 使用 MySQL 替代 SQLite

安装 `pymysql`，设置：

```
DATABASE_URL=mysql+pymysql://user:pass@localhost:3306/article_generator
```

并执行 `ArticleGeneratorDatabase/migrations/001_create_tables.sql` 初始化表结构。

---

## 六、一键启动（推荐）

在项目根目录执行：

```bash
./scripts/start.sh
```

脚本会自动完成：
1. 检查/启动 Redis（若已安装 Docker 则自动拉取并启动）
2. 安装 Python 依赖
3. 启动 LLM 服务、后端 API、Celery Worker（后台）
4. 抓取热点
5. 启动管理后台
6. 打开浏览器访问 http://localhost:5173

按 **Ctrl+C** 可停止所有服务。或执行 `./scripts/stop.sh` 手动停止。

---

## 七、Docker Compose 部署（可选）

```bash
docker-compose up -d
```

会启动 Redis、MySQL、API、Celery、LLM。管理后台需单独运行：

```bash
cd ArticleGeneratorAdm && npm install && npm run dev
```

然后访问 http://localhost:5173。
