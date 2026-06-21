"""
ArticleGenerator 后端主入口
"""
import logging
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .database import init_db, SessionLocal

logger = logging.getLogger(__name__)
from .models import User
from .auth import get_password_hash
from .api import accounts, hotspot_sources, hotspots, articles, generate, providers, scenario_configs, reference_articles, distill, generation_logs, tasks, tracks, mp_accounts, credentials, collect_tasks, materials, collect_logs
from .api import auth as auth_api
from .deps import get_current_user, verify_any_auth
from . import tasks as _celery_tasks  # ensures Celery app + collector tasks are registered

app = FastAPI(
    title="ArticleGenerator API",
    description="半自动化内容创作辅助系统",
    version="0.1.0",
)

# Parse CORS origins — ban wildcard + credentials combo for security
origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
if not origins or "*" in origins:
    origins = ["http://localhost:5173"]  # Safe dev default
    allow_creds = False
else:
    allow_creds = True

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=allow_creds,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── 公开端点 ──
app.include_router(auth_api.router, prefix="/api")

@app.get("/api/health")
def health_check():
    """健康检查"""
    return {"status": "ok"}


# ── 混合路由（部分公开、部分受保护，依赖在路由内部处理）──
app.include_router(hotspots.router, prefix="/api")
app.include_router(hotspot_sources.router, prefix="/api")


# ── 受保护路由（需 JWT）──
app.include_router(accounts.router, prefix="/api", dependencies=[Depends(get_current_user)])
app.include_router(articles.router, prefix="/api", dependencies=[Depends(get_current_user)])
app.include_router(generate.router, prefix="/api", dependencies=[Depends(get_current_user)])
app.include_router(providers.router, prefix="/api", dependencies=[Depends(get_current_user)])
app.include_router(scenario_configs.router, prefix="/api", dependencies=[Depends(verify_any_auth)])
app.include_router(reference_articles.router, prefix="/api", dependencies=[Depends(get_current_user)])
app.include_router(distill.router, prefix="/api", dependencies=[Depends(get_current_user)])
app.include_router(generation_logs.router, prefix="/api", dependencies=[Depends(get_current_user)])
app.include_router(tasks.router, prefix="/api", dependencies=[Depends(get_current_user)])
app.include_router(tracks.router, prefix="/api", dependencies=[Depends(get_current_user)])
app.include_router(mp_accounts.router, prefix="/api", dependencies=[Depends(get_current_user)])
app.include_router(credentials.router, prefix="/api", dependencies=[Depends(get_current_user)])
app.include_router(collect_tasks.router, prefix="/api", dependencies=[Depends(get_current_user)])
app.include_router(materials.router, prefix="/api", dependencies=[Depends(get_current_user)])
app.include_router(collect_logs.router, prefix="/api", dependencies=[Depends(get_current_user)])


def seed_admin_user():
    """启动时自动创建初始管理员账号（如无用户）"""
    db = SessionLocal()
    try:
        count = db.query(User).count()
        if count == 0:
            user = User(
                username=settings.seed_username,
                password_hash=get_password_hash(settings.seed_password),
            )
            db.add(user)
            db.commit()
            logger.info("已创建初始管理员账号: %s", settings.seed_username)
    except Exception as e:
        logger.warning("创建管理员账号失败: %s", e)
        db.rollback()
    finally:
        db.close()


@app.on_event("startup")
def startup():
    """启动时初始化数据库并创建种子用户"""
    init_db()
    seed_admin_user()


@app.get("/")
def root():
    return {"message": "ArticleGenerator API", "docs": "/docs"}
