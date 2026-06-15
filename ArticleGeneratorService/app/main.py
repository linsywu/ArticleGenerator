"""
ArticleGenerator 后端主入口
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .database import init_db
from .api import accounts, hotspot_sources, hotspots, articles, generate, providers, scenario_configs, reference_articles, distill, generation_logs, tasks

app = FastAPI(
    title="ArticleGenerator API",
    description="半自动化内容创作辅助系统",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins.split(",") if "," in settings.cors_origins else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(accounts.router, prefix="/api")
app.include_router(hotspot_sources.router, prefix="/api")
app.include_router(hotspots.router, prefix="/api")
app.include_router(articles.router, prefix="/api")
app.include_router(generate.router, prefix="/api")
app.include_router(providers.router, prefix="/api")
app.include_router(scenario_configs.router, prefix="/api")
app.include_router(reference_articles.router, prefix="/api")
app.include_router(distill.router, prefix="/api")
app.include_router(generation_logs.router, prefix="/api")
app.include_router(tasks.router, prefix="/api")


@app.on_event("startup")
def startup():
    """启动时初始化数据库"""
    init_db()


@app.get("/")
def root():
    return {"message": "ArticleGenerator API", "docs": "/docs"}
