"""
数据模型定义
"""
from datetime import datetime, timezone, timedelta, date
from sqlalchemy import Column, Integer, String, Text, DateTime, Date, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from .database import Base

CST = timezone(timedelta(hours=8))  # Asia/Shanghai


def _utcnow():
    return datetime.now(timezone.utc)


def _local_iso(dt: datetime | None) -> str | None:
    """Convert UTC datetime to Asia/Shanghai ISO string for frontend display"""
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(CST).isoformat()


class User(Base):
    """管理后台用户"""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(100), nullable=False, unique=True)
    password_hash = Column(String(200), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow)


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
    style_profile_structured = Column(Text)  # JSON: 7维度结构化画像
    style_profile_version = Column(Integer, default=1)
    style_profile_status = Column(String(20), default="none")  # idle/running/ready/failed
    word_count_options = Column(Text)  # JSON: ["800", "1500", "3000"]
    word_count = Column(Text, nullable=True)  # default word count description, e.g. "1500-3000字"
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
    title = Column(String(200))  # 文章标题
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
    custom_topic = Column(Text)  # 自定义主题（用户输入的标题/主题，无热点时作为标题回退）
    status = Column(String(20), default="pending")  # pending/running/success/failed
    error_message = Column(Text)
    sub_task_ids = Column(Text)  # JSON array: 子任务 Celery task_id 列表（humanize, review 等）
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
    description = Column(Text)  # 场景说明
    sort_order = Column(Integer, default=0)  # 显示排序
    enabled = Column(Integer, default=1)
    created_at = Column(DateTime(timezone=True), default=_utcnow)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)
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
    task_id = Column(String(100), default=None)
    scenario = Column(String(50), nullable=False)
    task_id = Column(String(100))  # Celery 任务 ID，关联 generation_tasks.task_id
    provider_id = Column(Integer)
    model = Column(String(100))
    system_prompt = Column(Text)  # 渲染后的完整 system prompt
    user_prompt = Column(Text)    # 渲染后的 user message
    prompt_tokens = Column(Integer, default=0)
    completion_tokens = Column(Integer, default=0)
    latency_ms = Column(Integer, default=0)
    status = Column(String(20), default="success")
    error_message = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)


class Track(Base):
    """一级赛道"""
    __tablename__ = "tracks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    keywords = Column(Text)  # JSON string
    forbidden_keywords = Column(Text)  # JSON string
    status = Column(Integer, default=1)  # 0=禁用 1=启用
    created_at = Column(DateTime(timezone=True), default=_utcnow)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    sub_tracks = relationship("SubTrack", back_populates="track", cascade="all, delete-orphan")


class SubTrack(Base):
    """二级赛道"""
    __tablename__ = "sub_tracks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    track_id = Column(Integer, ForeignKey("tracks.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    created_at = Column(DateTime(timezone=True), default=_utcnow)

    track = relationship("Track", back_populates="sub_tracks")


class MpAccount(Base):
    """公众号"""
    __tablename__ = "mp_accounts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), nullable=False)
    alias = Column(String(100))
    fakeid = Column(String(100))
    biz = Column(String(100))
    avatar = Column(String(500))
    description = Column(Text)
    track_ids = Column(Text)  # JSON string
    article_count = Column(Integer, default=0)
    last_collect_time = Column(DateTime)
    status = Column(Integer, default=1)
    created_at = Column(DateTime(timezone=True), default=_utcnow)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)


class MpCredential(Base):
    """采集凭证"""
    __tablename__ = "mp_credentials"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    token = Column(String(500), nullable=False)
    cookie = Column(Text, nullable=False)
    status = Column(String(20), default="normal")
    check_time = Column(DateTime)
    created_at = Column(DateTime(timezone=True), default=_utcnow)


class CollectTask(Base):
    """采集任务"""
    __tablename__ = "collect_tasks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), nullable=False)
    credential_id = Column(Integer, ForeignKey("mp_credentials.id", ondelete="RESTRICT"), nullable=False)
    track_ids = Column(Text)
    account_ids = Column(Text)
    collect_mode = Column(String(30), default="incremental")
    date_start = Column(Date)
    date_end = Column(Date)
    schedule_type = Column(String(20), default="manual")
    cron = Column(String(50))
    interval_hours = Column(Integer)
    status = Column(String(20), default="idle")
    created_at = Column(DateTime(timezone=True), default=_utcnow)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)


class MpMaterial(Base):
    """素材文章"""
    __tablename__ = "mp_materials"

    id = Column(Integer, primary_key=True, autoincrement=True)
    account_id = Column(Integer, ForeignKey("mp_accounts.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(500))
    author = Column(String(100))
    original_url = Column(String(1000), nullable=False)
    cover_url = Column(String(500))
    summary = Column(Text)
    raw_html = Column(Text)
    content_html = Column(Text)
    content_markdown = Column(Text)
    content_hash = Column(String(64))
    word_count = Column(Integer, default=0)
    is_original = Column(Integer, default=0)
    published_at = Column(DateTime)
    collected_at = Column(DateTime(timezone=True), default=_utcnow)
    created_at = Column(DateTime(timezone=True), default=_utcnow)


class CollectLog(Base):
    """采集日志"""
    __tablename__ = "collect_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(Integer, ForeignKey("collect_tasks.id", ondelete="CASCADE"), nullable=False)
    account_id = Column(Integer)
    start_time = Column(DateTime)
    end_time = Column(DateTime)
    total_count = Column(Integer, default=0)
    success_count = Column(Integer, default=0)
    fail_count = Column(Integer, default=0)
    error_message = Column(Text)
    progress = Column(Text)  # JSON array: [{step, time, detail}, ...]
    created_at = Column(DateTime(timezone=True), default=_utcnow)
