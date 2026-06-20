"""
数据库连接与会话管理
"""
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from .config import settings


def _resolve_db_url(url: str) -> str:
    """将 SQLite 相对路径转换为绝对路径，避免 CWD 问题"""
    if url.startswith("sqlite:///./"):
        relative = url[len("sqlite:///./"):]
        app_dir = Path(__file__).resolve().parent.parent  # ArticleGeneratorService/
        resolved = app_dir / relative
        return f"sqlite:///{resolved}"
    return url


_resolved_url = _resolve_db_url(settings.database_url)

# SQLite 需要特殊配置以支持外键
connect_args = {}
if _resolved_url.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(
    _resolved_url,
    connect_args=connect_args,
    echo=False,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """依赖注入：获取数据库会话"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """创建所有表"""
    Base.metadata.create_all(bind=engine)
    # Enable SQLite foreign key enforcement
    with engine.connect() as conn:
        conn.exec_driver_sql("PRAGMA foreign_keys = ON")
        conn.commit()
    """初始化数据库表（开发用，生产建议用迁移脚本）"""
    Base.metadata.create_all(bind=engine)
