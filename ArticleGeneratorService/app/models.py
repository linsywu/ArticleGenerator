"""
数据模型定义
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from .database import Base


class HotspotSource(Base):
    """热点源配置"""

    __tablename__ = "hotspot_sources"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    type = Column(String(50), nullable=False)  # API / crawler
    config = Column(Text)  # JSON 字符串
    enabled = Column(Integer, default=1)  # 0 否 1 是
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Account(Base):
    """账号风格"""

    __tablename__ = "accounts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    platform = Column(String(50), nullable=False)
    account_name = Column(String(100), nullable=False)
    lora_path = Column(String(500))
    sample_articles = Column(Text)  # JSON 字符串
    style_profile = Column(Text)
    style_profile_updated_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    articles = relationship("Article", back_populates="account")


class Hotspot(Base):
    """热点"""

    __tablename__ = "hotspots"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(500), nullable=False)
    source = Column(String(100), nullable=False)
    heat = Column(Integer, default=0)
    summary = Column(Text)
    url = Column(String(1000))
    status = Column(String(20), default="unselected")  # unselected/selected/generated
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    articles = relationship("Article", back_populates="hotspot")


class Article(Base):
    """文章"""

    __tablename__ = "articles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    hotspot_id = Column(Integer, ForeignKey("hotspots.id", ondelete="SET NULL"), nullable=True)
    account_id = Column(Integer, ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False)
    content = Column(Text, nullable=False)
    status = Column(String(20), default="pending_review")  # pending_review/approved/rejected/published
    refine_history = Column(Text)  # JSON 字符串
    quality_score = Column(Integer)
    compliance_score = Column(Integer)
    review_notes = Column(Text)
    published_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    hotspot = relationship("Hotspot", back_populates="articles")
    account = relationship("Account", back_populates="articles")


class GenerationTask(Base):
    """生成任务"""

    __tablename__ = "generation_tasks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(String(100), nullable=False, unique=True)
    hotspot_id = Column(Integer, ForeignKey("hotspots.id", ondelete="SET NULL"), nullable=True)
    account_id = Column(Integer, ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False)
    article_id = Column(Integer)
    status = Column(String(20), default="pending")  # pending/running/success/failed
    error_message = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class RefineTask(Base):
    """微调任务（用于前端轮询）"""

    __tablename__ = "refine_tasks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(String(100), nullable=False, unique=True)
    article_id = Column(Integer, ForeignKey("articles.id", ondelete="CASCADE"), nullable=False)
    status = Column(String(20), default="pending")  # pending/running/success/failed
    error_message = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Provider(Base):
    """API 供应商"""
    __tablename__ = "providers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    base_url = Column(String(500), nullable=False)
    api_key = Column(String(500), nullable=False)
    models = Column(Text)  # JSON
    enabled = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ScenarioConfig(Base):
    """场景路由配置"""
    __tablename__ = "scenario_configs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    scenario = Column(String(50), nullable=False)
    provider_id = Column(Integer, ForeignKey("providers.id", ondelete="CASCADE"), nullable=False)
    model = Column(String(100), nullable=False)
    system_prompt_template = Column(Text)
    params = Column(Text)  # JSON
    priority = Column(Integer, default=0)
    enabled = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    provider = relationship("Provider", lazy="joined")


class ReferenceArticle(Base):
    """参考文章"""
    __tablename__ = "reference_articles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    account_id = Column(Integer, ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(500), nullable=False)
    content = Column(Text, nullable=False)
    source_url = Column(String(1000))
    embedding = Column(Text)  # JSON
    is_benchmark = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)


class GenerationLog(Base):
    """生成日志"""
    __tablename__ = "generation_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    scenario = Column(String(50), nullable=False)
    provider_id = Column(Integer)
    model = Column(String(100))
    prompt_tokens = Column(Integer, default=0)
    completion_tokens = Column(Integer, default=0)
    latency_ms = Column(Integer, default=0)
    status = Column(String(20), default="success")
    error_message = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
