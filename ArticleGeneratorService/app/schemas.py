"""
Pydantic 请求/响应模型
"""
from datetime import datetime, timezone
from typing import Optional, List, Any, Annotated
from pydantic import BaseModel, Field, field_validator, BeforeValidator
import json


def _ensure_utc_tz(dt: datetime) -> datetime:
    """确保 datetime 带 UTC 时区（naive datetime 视为 UTC）"""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


# 带时区的 datetime 类型：Pydantic 序列化时输出 +00:00 后缀
UtcDateTime = Annotated[datetime, BeforeValidator(_ensure_utc_tz)]


# ----- 账号 -----
class AccountBase(BaseModel):
    platform: str
    account_name: str
    lora_path: Optional[str] = None
    sample_articles: Optional[str] = None
    word_count_options: Optional[str] = None  # JSON: ["1500字左右","2000到3000字"]
    word_count: Optional[str] = None  # 默认字数描述


class AccountCreate(AccountBase):
    pass


class AccountUpdate(BaseModel):
    platform: Optional[str] = None
    account_name: Optional[str] = None
    lora_path: Optional[str] = None
    sample_articles: Optional[str] = None
    word_count_options: Optional[str] = None
    word_count: Optional[str] = None


class AccountResponse(AccountBase):
    id: int
    word_count_options: Optional[str] = None
    word_count: Optional[str] = None
    style_profile: Optional[str] = None
    style_profile_updated_at: Optional[UtcDateTime] = None
    style_profile_structured: Optional[Any] = None
    style_profile_version: Optional[int] = None
    style_profile_status: Optional[str] = None
    created_at: UtcDateTime

    class Config:
        from_attributes = True

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
    created_at: UtcDateTime

    class Config:
        from_attributes = True


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
    created_at: UtcDateTime

    class Config:
        from_attributes = True


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
    title: Optional[str] = None  # 文章标题
    content: str
    status: str = "pending_review"


class ArticleResponse(ArticleBase):
    id: int
    title: Optional[str] = None
    hotspot_id: Optional[int] = None
    account_id: int
    refine_history: Optional[str] = None
    quality_score: Optional[int] = None
    compliance_score: Optional[int] = None
    review_notes: Optional[str] = None
    published_at: Optional[UtcDateTime] = None
    created_at: UtcDateTime
    updated_at: UtcDateTime

    class Config:
        from_attributes = True


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
    outline: Optional[List[str]] = None  # 新增：大纲要点列表
    word_count: Optional[str] = None  # 新增：用户选择的字数


class RefineRequest(BaseModel):
    """微调请求"""
    keywords: str = Field(..., description="修改关键词")


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

class ProviderResponse(ProviderBase):
    id: int
    created_at: UtcDateTime
    class Config: from_attributes = True


# ----- ScenarioConfig -----
class ScenarioConfigBase(BaseModel):
    scenario: str
    provider_id: int
    model: str = ""
    system_prompt_template: Optional[str] = None
    params: Optional[str] = None
    priority: int = 0
    description: Optional[str] = None  # 场景说明
    sort_order: int = 0  # 显示排序
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
    created_at: UtcDateTime
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
    created_at: UtcDateTime
    class Config: from_attributes = True


# ----- GenerationLog -----
class GenerationLogCreate(BaseModel):
    scenario: str
    provider_id: Optional[int] = None
    model: Optional[str] = None
    prompt_tokens: int = 0
    completion_tokens: int = 0
    latency_ms: int = 0
    status: str = "success"
    error_message: Optional[str] = None


# ----- Distill -----
class DistillRequest(BaseModel):
    account_id: int


# ── 方向生成 ──
class DirectionsRequest(BaseModel):
    account_id: int
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

# ── 标题生成 ──
class TitleRequest(BaseModel):
    account_id: int
    idea: str
    direction: str
    outline: List[str]

class TitleResponse(BaseModel):
    titles: List[str]
