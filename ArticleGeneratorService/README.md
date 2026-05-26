# ArticleGeneratorService

后端 API 服务，基于 FastAPI + SQLAlchemy + Celery。

## 运行

```bash
# 安装依赖
pip install -r requirements.txt

# 启动 API（开发）
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 启动 Celery Worker（另开终端）
celery -A app.tasks:celery_app worker -l info
```

## API 文档

启动后访问 http://localhost:8000/docs

## 环境变量

见 `.env.example`
