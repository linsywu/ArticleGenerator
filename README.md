# ArticleGenerator 半自动化内容创作辅助系统

热点抓取 → 人工选择 → 智能生成 → 评审微调 → 发布辅助

## 快速开始

**详细执行说明**：见 [docs/execution-guide.md](docs/execution-guide.md)

### 一键启动（推荐）

```bash
./scripts/start.sh
```

自动启动所有服务并打开浏览器。按 Ctrl+C 停止。

### 方式一：手动分步启动

1. **启动 Redis**（需本地安装或 Docker）：
   ```bash
   docker run -d -p 6379:6379 redis:7-alpine
   ```

2. **启动模型服务**（模拟模式，无需 GPU）：
   ```bash
   cd LLMService && pip install -r requirements.txt && uvicorn app.main:app --host 0.0.0.0 --port 8001
   ```

3. **启动后端**：
   ```bash
   cd ArticleGeneratorService && pip install -r requirements.txt && uvicorn app.main:app --host 0.0.0.0 --port 8000
   ```

4. **启动 Celery Worker**（另开终端）：
   ```bash
   cd ArticleGeneratorService && celery -A app.tasks:celery_app worker -l info
   ```

5. **抓取热点**（另开终端）：
   ```bash
   cd HotspotCrawler && pip install -r requirements.txt && python run_crawl.py
   ```

6. **启动管理后台**：
   ```bash
   cd ArticleGeneratorAdm && npm install && npm run dev
   ```

7. 访问 http://localhost:5173

### 方式二：Docker Compose

```bash
docker-compose up -d
# 管理后台需单独运行：cd ArticleGeneratorAdm && npm run dev
```

## 模块说明

| 模块 | 说明 |
|------|------|
| HotspotCrawler | 热点抓取（微博、知乎等） |
| ArticleGeneratorService | 后端 API + Celery |
| LLMService | 模型服务（模拟/真实） |
| ArticleGeneratorAdm | 管理后台前端 |
| ArticleGeneratorDatabase | 数据库迁移脚本 |

## 测试

```bash
./scripts/run_all_tests.sh
```

各模块测试：ArticleGeneratorService (pytest)、LLMService (pytest)、HotspotCrawler (pytest)、ArticleGeneratorAdm (vitest)。

## 开发计划

见 [.cursor/plans/article-generator-dev-plan.md](.cursor/plans/article-generator-dev-plan.md)
