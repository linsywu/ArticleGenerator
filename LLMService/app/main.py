"""
LLM 网关服务：通用 AI 调用入口，支持多 Provider 按场景路由
"""
from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional, Dict, Any, List

from .gateway import gateway

app = FastAPI(
    title="ArticleGenerator LLM Gateway",
    description="通用 AI 调用网关，支持 Anthropic / DeepSeek / OpenAI",
    version="0.2.0",
)


class ChatRequest(BaseModel):
    scenario: str
    task_id: Optional[str] = None  # Celery 任务 ID，用于日志关联
    account_id: Optional[int] = None
    variables: Optional[Dict[str, Any]] = None
    extra_messages: Optional[List[Dict[str, str]]] = None


@app.get("/")
def root():
    return {"message": "LLM Gateway", "version": "0.2.0"}


@app.post("/chat")
def chat(req: ChatRequest):
    """统一聊天入口：按 scenario 路由到对应 provider + model"""
    result = gateway.chat(
        scenario=req.scenario,
        task_id=req.task_id,
        account_id=req.account_id,
        variables=req.variables,
        extra_messages=req.extra_messages,
    )
    if "error" in result:
        return {"content": "", "error": result["error"]}
    return result


class GenerateLegacyRequest(BaseModel):
    hotspot_title: Optional[str] = None
    topic: Optional[str] = None
    account_id: int
    lora_path: Optional[str] = None
    user_prompt: Optional[str] = None


class RefineLegacyRequest(BaseModel):
    article_id: int
    content: str
    keywords: str
    account_id: Optional[int] = None
    review_suggestions: Optional[str] = None


# 保留旧端点兼容（标记废弃），内部转发到 /chat
@app.post("/generate")
def generate_legacy(req: GenerateLegacyRequest):
    # 兼容新旧调用方：优先 topic，回退 hotspot_title
    resolved_topic = req.topic or req.hotspot_title or ""
    variables = {"topic": resolved_topic}
    if req.user_prompt:
        variables["user_prompt"] = req.user_prompt
    return gateway.chat(
        scenario="generate",
        account_id=req.account_id,
        variables=variables,
    )


@app.post("/refine")
def refine_legacy(req: RefineLegacyRequest):
    return gateway.chat(
        scenario="refine",
        account_id=req.account_id,
        variables={
            "article_content": req.content,
            "keywords": req.keywords,
            "review_suggestions": req.review_suggestions or "",
        },
    )
