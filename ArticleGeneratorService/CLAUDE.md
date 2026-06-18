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

## 代码模式

以下模式为强制规范，参考实现见 `app/api/accounts.py`。

### 新增 API 端点的标准步骤

**Step 1: 定义 Schema**（`app/schemas.py`）

```python
class NewResourceCreate(BaseModel):
    name: str
    type: str = "default"

class NewResourceResponse(BaseModel):
    id: int
    name: str
    type: str
    class Config:
        from_attributes = True  # 允许从 ORM model 构建
```

**Step 2: 创建路由文件**（`app/api/new_resource.py`）

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import NewResource
from ..schemas import NewResourceCreate, NewResourceResponse

router = APIRouter(prefix="/api/new-resource", tags=["新资源"])

@router.get("", response_model=List[NewResourceResponse])
def list_resources(db: Session = Depends(get_db)):
    return db.query(NewResource).order_by(NewResource.id.desc()).all()

@router.post("", response_model=NewResourceResponse)
def create_resource(data: NewResourceCreate, db: Session = Depends(get_db)):
    resource = NewResource(**data.model_dump())
    db.add(resource)
    db.commit()
    db.refresh(resource)
    return resource
```

**Step 3: 注册路由**（`app/main.py`）

```python
from app.api.new_resource import router as new_resource_router
app.include_router(new_resource_router)
```

**Step 4: 写测试**（`tests/test_api_new_resource.py`）

```python
def test_create_resource(client):
    res = client.post("/api/new-resource", json={"name": "test"})
    assert res.status_code == 200
    assert res.json()["name"] == "test"
```

### 数据库迁移

新增字段流程：`ArticleGeneratorDatabase/migrations/` 下新建 `NNN_description.sql` → `app/models.py` 添加 Column → `app/schemas.py` 添加字段。

### 认证模式

按端点按需引入，**不使用全局中间件**：

```python
from ..auth import get_current_user, get_crawler_key

# 需要用户登录
@router.get("/protected")
def protected_route(user = Depends(get_current_user)): ...

# Crawler Key 认证（机器调用）
@router.post("/batch")
def batch_create(key = Depends(get_crawler_key)): ...

# 公开端点
@router.get("/public")
def public_route(): ...  # 不加 Depends
```

### Celery 任务

```python
# app/tasks.py — 定义任务
@celery_app.task(bind=True, max_retries=3)
def generate_article(self, task_data):
    try:
        # 调用 LLMService
        ...
    except Exception as e:
        self.retry(exc=e, countdown=60)

# API 中触发
from .tasks import generate_article
task = generate_article.delay(task_data)
```

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
