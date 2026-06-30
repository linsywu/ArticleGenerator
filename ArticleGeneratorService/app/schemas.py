"""
Pydantic 请求/响应模型
"""
from datetime import datetime, timezone, date
from typing import Optional, List, Any, Annotated
from pydantic import BaseModel, Field, field_validator, BeforeValidator, PlainSerializer
import json

from .models import _local_iso

# 自定义 datetime 类型：序列化时自动转为 CST ISO 字符串
CstDateTime = Annotated[datetime, PlainSerializer(lambda dt: _local_iso(dt), return_type=str)]


def _ensure_utc_tz(dt: datetime) -> datetime:
    """确保 datetime 带 UTC 时区（naive datetime 视为 UTC）"""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def mask_api_key(key: str) -> str:
    """掩码 api_key: sk-abc123...xyz → sk-a***xyz"""
    if not key or len(key) <= 7:
        return key
    return key[:3] + "***" + key[-4:]


# 带时区的 datetime 类型：Pydantic 序列化时输出 +00:00 后缀
UtcDateTime = Annotated[datetime, BeforeValidator(_ensure_utc_tz)]


# ----- 认证 -----
class LoginRequest(BaseModel):
    """登录请求"""
    username: str
    password: str


class LoginResponse(BaseModel):
    """登录响应"""
    access_token: str
    token_type: str = "bearer"


# ----- 账号 -----
class AccountBase(BaseModel):
    platform: str
    account_name: str
    lora_path: Optional[str] = None
    sample_articles: Optional[str] = None


class AccountCreate(AccountBase):
    pass


class AccountUpdate(BaseModel):
    platform: Optional[str] = None
    account_name: Optional[str] = None
    lora_path: Optional[str] = None
    sample_articles: Optional[str] = None
    word_count_options: Optional[str] = None  # JSON string
    word_count: Optional[str] = None  # e.g. "1500-3000字"


class AccountResponse(AccountBase):
    id: int
    style_profile: Optional[str] = None
    style_profile_updated_at: Optional[CstDateTime] = None
    style_profile_structured: Optional[Any] = None
    style_profile_version: Optional[int] = None
    style_profile_status: Optional[str] = None
    word_count_options: Optional[str] = None
    word_count: Optional[str] = None  # e.g. "1500-3000字"
    created_at: CstDateTime

    class Config: from_attributes = True

    @field_validator("style_profile_structured", mode="before")
    @classmethod
    def parse_structured(cls, v):
        """将数据库中的 JSON 字符串转为 dict"""
        if v is None:
            return None
        if isinstance(v, dict):
            return v
        if isinstance(v, str):
            try:
                return json.loads(v)
            except (json.JSONDecodeError, TypeError):
                return None
        return None


# ----- 热点源 -----
class HotspotSourceBase(BaseModel):
    name: str
    type: str  # API / crawler
    config: Optional[str] = None
    enabled: bool = True


class HotspotSourceCreate(HotspotSourceBase):
    pass


class HotspotSourceUpdate(BaseModel):
    name: Optional[str] = None
    type: Optional[str] = None
    config: Optional[str] = None
    enabled: Optional[bool] = None


class HotspotSourceResponse(HotspotSourceBase):
    id: int
    created_at: CstDateTime

    class Config: from_attributes = True


# ----- 热点 -----
class HotspotBase(BaseModel):
    title: str
    source: str
    heat: int = 0
    summary: Optional[str] = None
    url: Optional[str] = None
    status: str = "unselected"


class HotspotResponse(HotspotBase):
    id: int
    created_at: CstDateTime

    class Config: from_attributes = True


class HotspotListParams(BaseModel):
    """热点列表查询参数"""
    status: Optional[str] = None
    source: Optional[str] = None
    keyword: Optional[str] = None
    page: int = 1
    page_size: int = 20


class HotspotListResponse(BaseModel):
    """热点列表分页响应"""
    data: List[HotspotResponse]
    total: int


class ArticleListResponse(BaseModel):
    """文章列表分页响应"""
    data: List["ArticleWithRelations"]
    total: int


# ----- 文章 -----
class ArticleBase(BaseModel):
    content: str
    title: Optional[str] = None
    status: str = "pending_review"


class ArticleResponse(ArticleBase):
    id: int
    hotspot_id: Optional[int] = None
    account_id: int
    refine_history: Optional[str] = None
    quality_score: Optional[int] = None
    compliance_score: Optional[int] = None
    review_notes: Optional[str] = None
    published_at: Optional[CstDateTime] = None
    created_at: CstDateTime
    updated_at: CstDateTime

    class Config: from_attributes = True


class ArticleWithRelations(ArticleResponse):
    """文章详情（含热点、账号信息）"""
    hotspot: Optional[HotspotResponse] = None
    account: Optional[AccountResponse] = None


# 解决 ArticleListResponse 前向引用
ArticleListResponse.model_rebuild()


# ----- 生成任务 -----
class GenerateRequest(BaseModel):
    """触发生成请求：可选热点 ID 列表或自定义主题"""
    hotspot_ids: List[int] = []
    account_id: int
    custom_topic: Optional[str] = None
    outline: Optional[List[str]] = None  # 大纲要点列表
    word_count: Optional[str] = None  # 用户选择的字数
    direction: Optional[str] = None  # 写作方向（用于生成提示词）
    direction_task_id: Optional[str] = None  # 方向生成 task_id（用于日志关联）
    outline_task_id: Optional[str] = None    # 大纲生成 task_id
    title_task_id: Optional[str] = None      # 标题生成 task_id


class RefineRequest(BaseModel):
    """微调请求"""
    keywords: str = Field(..., description="修改关键词")


class DirectionsRequest(BaseModel):
    """方向生成请求"""
    account_id: Optional[int] = 0
    idea: str
    word_count: Optional[str] = None


class DirectionsResponse(BaseModel):
    """方向生成响应"""
    directions: list


class OutlineRequest(BaseModel):
    """大纲生成请求"""
    account_id: int
    idea: str
    direction: str


class OutlineResponse(BaseModel):
    """大纲生成响应"""
    outline: list


class TitleRequest(BaseModel):
    """标题生成请求"""
    account_id: int
    idea: str
    direction: str
    outline: List[str]


class TitleResponse(BaseModel):
    """标题生成响应"""
    titles: List[str]


class ArticleStatusUpdate(BaseModel):
    """文章状态更新"""
    status: str  # approved / rejected / published


class ArticleUpdateRequest(BaseModel):
    """文章内容更新"""
    content: Optional[str] = None
    review_notes: Optional[str] = None


# ----- Provider -----
class ProviderBase(BaseModel):
    name: str
    base_url: str
    api_key: str
    models: Optional[str] = None
    enabled: bool = True

class ProviderCreate(ProviderBase): pass
class ProviderUpdate(BaseModel):
    name: Optional[str] = None
    base_url: Optional[str] = None
    api_key: Optional[str] = None
    models: Optional[str] = None
    enabled: Optional[bool] = None

    @field_validator("api_key", mode="before")
    @classmethod
    def skip_masked_key(cls, v: Optional[str]) -> Optional[str]:
        """如果传入掩码后的 key（如 sk-a***xyz），视为留空"""
        if v and "***" in v:
            return None
        return v

class ProviderResponse(ProviderBase):
    id: int
    created_at: CstDateTime
    class Config: from_attributes = True

    @field_validator("api_key", mode="after")
    @classmethod
    def mask_api_key_response(cls, v: str) -> str:
        return mask_api_key(v)


# ----- ScenarioConfig -----
class ScenarioConfigBase(BaseModel):
    scenario: str
    provider_id: int
    model: str = ""
    system_prompt_template: Optional[str] = None
    params: Optional[str] = None
    priority: int = 0
    description: Optional[str] = None
    sort_order: Optional[int] = None
    enabled: bool = True

class ScenarioConfigCreate(ScenarioConfigBase): pass
class ScenarioConfigUpdate(BaseModel):
    provider_id: Optional[int] = None
    model: Optional[str] = None
    system_prompt_template: Optional[str] = None
    params: Optional[str] = None
    priority: Optional[int] = None
    description: Optional[str] = None
    sort_order: Optional[int] = None
    enabled: Optional[bool] = None

class ScenarioConfigResponse(ScenarioConfigBase):
    id: int
    provider: Optional[ProviderResponse] = None
    created_at: CstDateTime
    class Config: from_attributes = True


# ----- ReferenceArticle -----
class ReferenceArticleBase(BaseModel):
    account_id: int
    title: str
    content: str
    source_url: Optional[str] = None
    embedding: Optional[str] = None
    is_benchmark: bool = False

class ReferenceArticleCreate(ReferenceArticleBase): pass
class ReferenceArticleResponse(ReferenceArticleBase):
    id: int
    created_at: CstDateTime
    class Config: from_attributes = True


# ----- GenerationLog -----
class GenerationLogCreate(BaseModel):
    scenario: str
    task_id: Optional[str] = None
    provider_id: Optional[int] = None
    model: Optional[str] = None
    system_prompt: Optional[str] = None
    user_prompt: Optional[str] = None
    prompt_tokens: int = 0
    completion_tokens: int = 0
    latency_ms: int = 0
    status: str = "success"
    error_message: Optional[str] = None


class GenerationLogResponse(BaseModel):
    id: int
    scenario: str
    task_id: Optional[str] = None
    provider_id: Optional[int] = None
    model: Optional[str] = None
    system_prompt: Optional[str] = None
    user_prompt: Optional[str] = None
    prompt_tokens: int = 0
    completion_tokens: int = 0
    latency_ms: int = 0
    status: str = "success"
    error_message: Optional[str] = None
    created_at: CstDateTime

    class Config: from_attributes = True


# ----- Distill -----
class DistillRequest(BaseModel):
    account_id: int


# ── 方向生成 ──
class DirectionsRequest(BaseModel):
    account_id: Optional[int] = 0
    idea: str
    word_count: Optional[str] = None

class DirectionItem(BaseModel):
    id: str
    title: str

class DirectionsResponse(BaseModel):
    directions: List[DirectionItem]

# ── 大纲生成 ──
class OutlineRequest(BaseModel):
    account_id: int
    idea: str
    direction: str

class OutlinePoint(BaseModel):
    order: int
    point: str

class OutlineResponse(BaseModel):
    outline: List[OutlinePoint]


# ----- 赛道 -----
class SubTrackBase(BaseModel):
    name: str
    description: Optional[str] = None

class SubTrackCreate(SubTrackBase): pass

class SubTrackResponse(SubTrackBase):
    id: int
    track_id: int
    created_at: CstDateTime
    class Config: from_attributes = True

class TrackBase(BaseModel):
    name: str
    description: Optional[str] = None
    keywords: Optional[str] = None
    forbidden_keywords: Optional[str] = None

class TrackCreate(TrackBase): pass

class TrackUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    keywords: Optional[str] = None
    forbidden_keywords: Optional[str] = None

class TrackStatusUpdate(BaseModel):
    status: int

class TrackResponse(TrackBase):
    id: int
    status: int = 1
    sub_tracks: List[SubTrackResponse] = []
    created_at: CstDateTime
    updated_at: CstDateTime
    class Config: from_attributes = True


# ----- 公众号 -----
class MpAccountBase(BaseModel):
    name: str
    alias: Optional[str] = None
    fakeid: Optional[str] = None
    biz: Optional[str] = None
    avatar: Optional[str] = None
    description: Optional[str] = None
    track_ids: Optional[str] = None

class MpAccountCreate(MpAccountBase): pass

class MpAccountUpdate(BaseModel):
    name: Optional[str] = None
    alias: Optional[str] = None
    fakeid: Optional[str] = None
    biz: Optional[str] = None
    avatar: Optional[str] = None
    description: Optional[str] = None
    track_ids: Optional[str] = None

class MpAccountResponse(MpAccountBase):
    id: int
    article_count: int = 0
    last_collect_time: Optional[CstDateTime] = None
    status: int = 1
    created_at: CstDateTime
    updated_at: CstDateTime
    class Config: from_attributes = True

class MpAccountImportByNameRequest(BaseModel):
    names: List[str]
    credential_id: int

class MpAccountImportByUrlRequest(BaseModel):
    urls: List[str]
    credential_id: int


# ----- 采集凭证 -----
class MpCredentialCreate(BaseModel):
    name: str
    token: str
    cookie: str

class MpCredentialUpdate(BaseModel):
    name: Optional[str] = None
    token: Optional[str] = None
    cookie: Optional[str] = None

    @field_validator("token", mode="before")
    @classmethod
    def skip_masked_token(cls, v: Optional[str]) -> Optional[str]:
        if v and "***" in v:
            return None
        return v

    @field_validator("cookie", mode="before")
    @classmethod
    def skip_masked_cookie(cls, v: Optional[str]) -> Optional[str]:
        if v and "***" in v:
            return None
        return v

class MpCredentialResponse(BaseModel):
    id: int
    name: str
    token: str
    cookie: str
    status: str
    check_time: Optional[CstDateTime] = None
    created_at: CstDateTime
    class Config: from_attributes = True

    @field_validator("token", mode="after")
    @classmethod
    def mask_token(cls, v): return v[:3] + "***" + v[-4:] if v and len(v) > 7 else v

    @field_validator("cookie", mode="after")
    @classmethod
    def mask_cookie(cls, v):
        if not v or len(v) <= 20: return v
        return v[:10] + "***" + v[-10:]


# ----- 采集任务 -----
class CollectTaskCreate(BaseModel):
    name: str
    credential_id: int
    track_ids: Optional[str] = None
    account_ids: Optional[str] = None
    collect_mode: str = "incremental"
    date_start: Optional[date] = None
    date_end: Optional[date] = None
    schedule_type: str = "manual"
    cron: Optional[str] = None
    interval_hours: Optional[int] = None

class CollectTaskUpdate(BaseModel):
    name: Optional[str] = None
    credential_id: Optional[int] = None
    track_ids: Optional[str] = None
    account_ids: Optional[str] = None
    collect_mode: Optional[str] = None
    date_start: Optional[date] = None
    date_end: Optional[date] = None
    schedule_type: Optional[str] = None
    cron: Optional[str] = None
    interval_hours: Optional[int] = None

class CollectTaskLastResult(BaseModel):
    total_count: int = 0
    success_count: int = 0
    fail_count: int = 0
    executed_at: Optional[str] = None

class CollectTaskResponse(BaseModel):
    id: int
    name: str
    credential_id: int
    track_ids: Optional[str] = None
    account_ids: Optional[str] = None
    collect_mode: str
    date_start: Optional[date] = None
    date_end: Optional[date] = None
    schedule_type: str
    cron: Optional[str] = None
    interval_hours: Optional[int] = None
    status: str
    last_result: Optional[CollectTaskLastResult] = None
    created_at: CstDateTime
    updated_at: CstDateTime
    class Config: from_attributes = True


# ----- 素材中心 -----

class MpMaterialResponse(BaseModel):
    id: int
    account_id: int
    title: Optional[str] = None
    author: Optional[str] = None
    original_url: str
    cover_url: Optional[str] = None
    summary: Optional[str] = None
    raw_html: Optional[str] = None
    content_html: Optional[str] = None
    content_markdown: Optional[str] = None
    content_hash: Optional[str] = None
    word_count: int = 0
    is_original: int = 0
    published_at: Optional[CstDateTime] = None
    collected_at: Optional[CstDateTime] = None
    created_at: Optional[CstDateTime] = None
    account: Optional[dict] = None

    class Config: from_attributes = True


class MpMaterialListItem(BaseModel):
    id: int
    account_id: int
    title: Optional[str] = None
    author: Optional[str] = None
    original_url: str
    cover_url: Optional[str] = None
    summary: Optional[str] = None
    word_count: int = 0
    is_original: int = 0
    published_at: Optional[CstDateTime] = None
    collected_at: Optional[CstDateTime] = None
    created_at: Optional[CstDateTime] = None
    account: Optional[dict] = None
    account: Optional[dict] = None

    class Config: from_attributes = True


class MpMaterialListResponse(BaseModel):
    data: list[MpMaterialListItem]
    total: int


# ----- 采集日志 -----

class CollectLogResponse(BaseModel):
    id: int
    task_id: int
    task_name: Optional[str] = None
    account_id: Optional[int] = None
    start_time: Optional[CstDateTime] = None
    end_time: Optional[CstDateTime] = None
    total_count: int = 0
    success_count: int = 0
    fail_count: int = 0
    error_message: Optional[str] = None
    created_at: Optional[CstDateTime] = None
    account: Optional[dict] = None
    progress: Optional[list] = None
    siblings: Optional[list] = None

    class Config: from_attributes = True


class CollectLogListResponse(BaseModel):
    data: list[CollectLogResponse]
    total: int
