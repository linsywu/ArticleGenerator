"""
Celery 异步任务：文章生成与微调
"""
import json
from datetime import datetime

import httpx
from celery import Celery
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from .config import settings
from .models import (
    Base,
    Hotspot,
    Account,
    Article,
    GenerationTask,
    RefineTask,
    ReferenceArticle,
    GenerationLog,
)

# Celery 应用
celery_app = Celery(
    "article_generator",
    broker=settings.redis_url,
    backend=settings.redis_url,
)
celery_app.conf.task_serializer = "json"
celery_app.conf.result_serializer = "json"
celery_app.conf.accept_content = ["json"]

# 同步数据库会话（Celery worker 内使用）
engine = create_engine(settings.database_url, connect_args={"check_same_thread": False} if "sqlite" in settings.database_url else {})
SessionLocal = sessionmaker(bind=engine)


def get_db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@celery_app.task(bind=True)
def trigger_generate(self, hotspot_title: str, account_id: int, hotspot_id: int = None):
    """
    异步生成文章：调用 LLM 服务，写入数据库
    """
    db = SessionLocal()
    gt = None
    try:
        gt = db.query(GenerationTask).filter(GenerationTask.task_id == self.request.id).first()
        if gt and gt.status == "cancelled":
            db.close()
            return  # 已被取消，直接退出
        if gt:
            gt.status = "running"
            db.commit()

        # 查询账号的 LoRA 路径
        account = db.query(Account).filter(Account.id == account_id).first()
        lora_path = account.lora_path if account else None

        # 调用 LLM 服务
        llm_url = settings.llm_service_url.rstrip("/")
        payload = {
            "hotspot_title": hotspot_title,
            "account_id": account_id,
            "user_prompt": (
                f'以"{hotspot_title}"为题，写一篇公众号文章。\\n\\n'
                '【结构要求 - 每次都要不同】\\n'
                '开头方式随机选择：直接亮出争议观点 / 对话开头 / 个人经历自述 / 数据或现象描述。不要每次都第三人称讲故事。\\n'
                '中间避免"观点→论证→案例"的标准三段论，可以突然插入一段看似无关的个人回忆、一句反问打断节奏、或一个让读者意外的类比。\\n'
                '结尾不要总结全文。可以戛然而止、可以抛出问题、可以展示矛盾的未解决状态。\\n\\n'
                '【留白要求 - 关键】\\n'
                '不要把道理讲完。最有力的话只说七分。剩下三分让读者自己琢磨。\\n'
                '每讲完一个观点后，删掉最后那句"总结升华"——直接跳到下一段。\\n\\n'
                '【内容要求】\\n'
                '至少2个有具体细节的案例。\\n'
                '至少1处让读者意外的角度或结论。\\n'
                '允许适度的语气不一致——愤怒时突然疲惫，坚定中插入一句自我怀疑。\\n'
                '字数1500左右。'
            ),
        }
        if lora_path:
            payload["lora_path"] = lora_path
        with httpx.Client(timeout=120.0) as client:
            resp = client.post(f"{llm_url}/generate", json=payload)
            resp.raise_for_status()
            data = resp.json()

        content = data.get("content", "")
        if not content:
            raise ValueError("LLM 返回内容为空")

        # 写入文章表
        article = Article(
            hotspot_id=hotspot_id,
            account_id=account_id,
            content=content,
            status="pending_review",
        )
        db.add(article)
        db.commit()
        db.refresh(article)

        # 更新热点状态（仅当关联了热点时）
        if hotspot_id:
            hotspot = db.query(Hotspot).filter(Hotspot.id == hotspot_id).first()
            if hotspot:
                hotspot.status = "generated"
                db.commit()

        # 更新任务状态
        if gt:
            gt.status = "success"
            gt.article_id = article.id
            db.commit()

        # 生成成功后，自动链式触发：去AI味 → 质量评审 + 合规评审
        if article:
            trigger_humanize.delay(article.id, article.content)

        return {"article_id": article.id}
    except Exception as e:
        gt = db.query(GenerationTask).filter(GenerationTask.task_id == self.request.id).first()
        if gt:
            gt.status = "failed"
            gt.error_message = str(e)
            db.commit()
        raise
    finally:
        db.close()


@celery_app.task(bind=True)
def trigger_humanize(self, article_id: int, content: str):
    """
    去AI味重写：调用 LLM 检测AI痕迹并真人化重写，然后链式触发评审
    """
    db = SessionLocal()
    try:
        llm_url = settings.llm_service_url.rstrip("/")
        with httpx.Client(timeout=120.0) as client:
            resp = client.post(f"{llm_url}/chat", json={
                "scenario": "humanize",
                "variables": {"article_content": content},
            })
            resp.raise_for_status()
            data = resp.json()

        humanized = data.get("content", "")
        if not humanized or humanized == content:
            # Humanization failed or no change, fall through to review
            humanized = content

        # Update article with humanized content
        article = db.query(Article).filter(Article.id == article_id).first()
        if article:
            article.content = humanized
            db.commit()

        # Chain to quality + compliance review
        trigger_quality_review.delay(article_id, humanized)
        trigger_compliance_review.delay(article_id, humanized)

        return {"article_id": article_id, "humanized": humanized != content}
    except Exception as e:
        # If humanization fails, still run reviews on original content
        if content:
            trigger_quality_review.delay(article_id, content)
            trigger_compliance_review.delay(article_id, content)
        raise
    finally:
        db.close()


@celery_app.task(bind=True)
def trigger_refine(self, article_id: int, keywords: str):
    """
    异步微调文章：调用 LLM 服务，更新文章内容
    """
    db = SessionLocal()
    rt = None
    try:
        rt = db.query(RefineTask).filter(RefineTask.task_id == self.request.id).first()
        if rt:
            rt.status = "running"
            db.commit()

        article = db.query(Article).filter(Article.id == article_id).first()
        if not article:
            raise ValueError("文章不存在")

        llm_url = settings.llm_service_url.rstrip("/")
        with httpx.Client(timeout=120.0) as client:
            resp = client.post(
                f"{llm_url}/refine",
                json={"article_id": article_id, "content": article.content, "keywords": keywords},
            )
            resp.raise_for_status()
            data = resp.json()

        new_content = data.get("content", "")
        if not new_content:
            raise ValueError("LLM 返回内容为空")

        # 保留微调历史（简化：追加记录）
        history = []
        if article.refine_history:
            try:
                history = json.loads(article.refine_history)
            except Exception:
                pass
        history.append({"keywords": keywords, "prev_len": len(article.content)})
        article.content = new_content
        article.refine_history = json.dumps(history, ensure_ascii=False)
        article.status = "pending_review"
        db.commit()

        if rt:
            rt.status = "success"
            db.commit()

        return {"article_id": article_id}
    except Exception as e:
        rt = db.query(RefineTask).filter(RefineTask.task_id == self.request.id).first()
        if rt:
            rt.status = "failed"
            rt.error_message = str(e)
            db.commit()
        raise
    finally:
        db.close()


@celery_app.task(bind=True)
def trigger_distill(self, account_id: int, articles_content: list, num_articles: int):
    """异步蒸馏：参考文章 → 风格画像"""
    db = SessionLocal()
    try:
        llm_url = settings.llm_service_url.rstrip("/")
        with httpx.Client(timeout=300.0) as client:
            resp = client.post(f"{llm_url}/chat", json={
                "scenario": "distill",
                "account_id": account_id,
                "variables": {
                    "num_articles": str(num_articles),
                    "articles_content": "\n\n---\n\n".join(articles_content),
                },
            })
            resp.raise_for_status()
            data = resp.json()

        content = data.get("content", "")
        if not content:
            raise ValueError("蒸馏返回内容为空")

        account = db.query(Account).filter(Account.id == account_id).first()
        if account:
            account.style_profile = content
            account.style_profile_updated_at = datetime.utcnow()
            db.commit()

        return {"account_id": account_id}
    except Exception as e:
        raise
    finally:
        db.close()


@celery_app.task(bind=True)
def trigger_quality_review(self, article_id: int, article_content: str):
    """异步质量评审：文章 → 质量评分"""
    db = SessionLocal()
    try:
        llm_url = settings.llm_service_url.rstrip("/")
        with httpx.Client(timeout=120.0) as client:
            resp = client.post(f"{llm_url}/chat", json={
                "scenario": "quality_review",
                "variables": {"article_content": article_content},
            })
            resp.raise_for_status()
            data = resp.json()

        content = data.get("content", "")
        score = _parse_score(content)

        article = db.query(Article).filter(Article.id == article_id).first()
        if article:
            article.quality_score = score
            notes = (article.review_notes or "") + f"\n[质量评审] {content[:500]}"
            article.review_notes = notes.strip()
            db.commit()

        return {"article_id": article_id, "score": score}
    except Exception as e:
        raise
    finally:
        db.close()


@celery_app.task(bind=True)
def trigger_compliance_review(self, article_id: int, article_content: str):
    """异步合规评审：文章 → 合规评分"""
    db = SessionLocal()
    try:
        llm_url = settings.llm_service_url.rstrip("/")
        with httpx.Client(timeout=120.0) as client:
            resp = client.post(f"{llm_url}/chat", json={
                "scenario": "compliance_review",
                "variables": {"article_content": article_content},
            })
            resp.raise_for_status()
            data = resp.json()

        content = data.get("content", "")
        score = 100 if "safe" in content.lower() else _parse_score(content)

        article = db.query(Article).filter(Article.id == article_id).first()
        if article:
            article.compliance_score = score
            notes = (article.review_notes or "") + f"\n[合规评审] {content[:500]}"
            article.review_notes = notes.strip()
            db.commit()

        return {"article_id": article_id, "score": score}
    except Exception as e:
        raise
    finally:
        db.close()


def _parse_score(text: str) -> int:
    """从评审文本中提取分值"""
    import re

    nums = re.findall(r"\b([0-9]{1,3})\b", text)
    if nums:
        scores = [int(n) for n in nums if 0 <= int(n) <= 100]
        if scores:
            return sum(scores) // len(scores)
    return 0
