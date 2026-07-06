"""
Celery 异步任务：文章生成与微调
"""
import json
import logging
import re
from datetime import datetime, timezone

import httpx
from celery import Celery

from .config import settings
from .database import SessionLocal
from .models import (
    Base,
    Hotspot,
    Account,
    Article,
    GenerationTask,
    RefineTask,
    ReferenceArticle,
    GenerationLog,
    MpMaterial,
)
from app.collector.worker import execute_collect_task, check_credentials_health

# Celery 应用
celery_app = Celery(
    "article_generator",
    broker=settings.redis_url,
    backend=settings.redis_url,
)

logger = logging.getLogger(__name__)
celery_app.conf.task_serializer = "json"
celery_app.conf.result_serializer = "json"
celery_app.conf.accept_content = ["json"]
celery_app.conf.beat_schedule = {
    'check-credentials-health': {
        'task': 'app.collector.worker.check_credentials_health',
        'schedule': 21600.0,
    },
}


def get_db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def resolve_article_title(content: str, topic: str | None = None, hotspot_title: str | None = None) -> str | None:
    """
    解析文章最终标题。

    优先使用传入的标题（用户选择或热点标题），
    仅当传入标题为空时才从 LLM 输出内容中自动提取。

    这修复了一个 bug：用户选择标题后，文章列表展示的却是 LLM
    输出内容自动提取的标题。

    兼容旧参数名 hotspot_title（已废弃，优先使用 topic）。
    """
    # 兼容：优先 topic，回退 hotspot_title
    resolved = topic or hotspot_title
    if resolved and resolved.strip():
        return resolved.strip()[:200]

    # 回退：从 LLM 输出内容中提取标题
    if not content:
        return None

    lines = content.strip().split("\n")
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("# "):
            return stripped[2:].strip()[:200]
        elif stripped.startswith("## "):
            return stripped[3:].strip()[:200]
        else:
            return stripped[:50]

    return None


def _sample_segments(article: str, max_chars: int = 1200) -> str:
    """取首段 + 中段 + 尾段，保留全文风格信号（替代硬截断）"""
    if len(article) <= max_chars:
        return article
    chunk = max_chars // 3
    head = article[:chunk]
    mid = article[len(article) // 2 : len(article) // 2 + chunk]
    tail = article[-chunk:]
    return f"{head}\n\n[...中段抽样...]\n\n{mid}\n\n[...尾段...]\n\n{tail}"


def _compress_articles(articles_content: list) -> str:
    """
    文章压缩策略（替代旧的 800 字硬截断）：
    - ≤5 篇：全文输入
    - 6-15 篇：每篇取首/中/尾段抽样
    - >15 篇：均匀抽样到 15 篇（首+末+中间均匀），再对每篇抽样
    """
    MAX_FULL = 5
    MAX_SAMPLED = 15

    articles = list(articles_content)
    if len(articles) > MAX_SAMPLED:
        n = len(articles)
        # 均匀抽样到 MAX_SAMPLED 篇：含首篇、末篇、中间均匀分布
        indices = sorted(set(round(i * (n - 1) / (MAX_SAMPLED - 1)) for i in range(MAX_SAMPLED)))
        articles = [articles[i] for i in indices]

    parts = []
    use_full = len(articles) <= MAX_FULL
    for a in articles:
        parts.append(a if use_full else _sample_segments(a))
    return "\n\n---\n\n".join(parts)


@celery_app.task(bind=True)
def trigger_generate(self, topic: str, account_id: int, hotspot_id: int = None, outline: list = None, word_count: str = None, direction: str = None):
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

        # 查询账号
        account = db.query(Account).filter(Account.id == account_id).first()
        lora_path = account.lora_path if account else None

        # 构建大纲 section（整段，含标题和约束语；无大纲时为空字符串）
        outline_section = ""
        if outline:
            outline_items = [f"{i+1}. {p}" for i, p in enumerate(outline)]
            outline_section = (
                "## 写作大纲\n"
                + "\n".join(outline_items)
                + "\n\n请严格按照以上大纲逐段写作，大纲有几段文章就必须有几段。\n"
            )

        # 字数指令（用户选择优先 → 账号配置 → 默认值）
        word_count_instruction = "字数1500左右。"
        if word_count:
            word_count_instruction = f"字数{word_count}。"
        elif account and account.word_count:
            word_count_instruction = f"字数{account.word_count}。"

        # 调用 LLM 服务（通过 /chat 端点，variables 由 Gateway 渲染到 system_prompt_template）
        llm_url = settings.llm_service_url.rstrip("/")
        payload = {
            "scenario": "generate",
            "task_id": self.request.id,
            "account_id": account_id,
            "variables": {
                "topic": topic,
                "direction": direction or "",
                "outline_section": outline_section,
                "word_count_instruction": word_count_instruction,
            },
        }
        with httpx.Client(timeout=120.0) as client:
            resp = client.post(f"{llm_url}/chat", json=payload)
            resp.raise_for_status()
            data = resp.json()

        content = data.get("content", "")
        if not content:
            raise ValueError("LLM 返回内容为空")

        # 使用统一的标题解析逻辑（优先用户选择 → 回退自动提取）
        title = resolve_article_title(content, topic)

        # 写入文章表 (unchanged)
        article = Article(
            title=title,
            hotspot_id=hotspot_id,
            account_id=account_id,
            content=content,
            status="pending_review",
        )
        db.add(article)
        db.commit()
        db.refresh(article)

        # 更新热点状态（仅当关联了热点时）(unchanged)
        if hotspot_id:
            hotspot = db.query(Hotspot).filter(Hotspot.id == hotspot_id).first()
            if hotspot:
                hotspot.status = "generated"
                db.commit()

        # 生成成功后，同步执行去AI味（确保前端拿到的是最终内容，防止竞态）
        # quality_review 和 compliance_review 不修改 content，可保持异步
        humanized = content
        try:
            llm_url = settings.llm_service_url.rstrip("/")
            with httpx.Client(timeout=120.0) as client:
                resp = client.post(f"{llm_url}/chat", json={
                    "scenario": "humanize",
                    "task_id": self.request.id,
                    "variables": {
                        "article_content": content,
                        "outline_section": outline_section,
                    },
                })
                resp.raise_for_status()
                data = resp.json()
            humanized = data.get("content", "") or content
            if humanized and humanized != content:
                article.content = humanized
                db.commit()
        except Exception:
            # humanize 失败不影响主流程，保留原始内容
            pass

        # 更新任务状态（humanize 完成后才标记 success）
        if gt:
            gt.status = "success"
            gt.article_id = article.id
            db.commit()

        # 异步触发质量评审 + 合规评审（不修改 content）
        if article:
            qr_task = trigger_quality_review.delay(article.id, article.content)
            cr_task = trigger_compliance_review.delay(article.id, article.content)
            if gt:
                try:
                    existing = json.loads(gt.sub_task_ids) if gt.sub_task_ids else []
                    existing.extend([qr_task.id, cr_task.id])
                    gt.sub_task_ids = json.dumps(existing)
                    db.commit()
                except Exception:
                    pass

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
def trigger_humanize(self, article_id: int, content: str, outline_section: str = ""):
    """
    去AI味重写：调用 LLM 检测AI痕迹并真人化重写，然后链式触发评审
    """
    db = SessionLocal()
    try:
        llm_url = settings.llm_service_url.rstrip("/")
        with httpx.Client(timeout=120.0) as client:
            resp = client.post(f"{llm_url}/chat", json={
                "scenario": "humanize",
                "task_id": self.request.id,
                "variables": {
                    "article_content": content,
                    "outline_section": outline_section,
                },
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

        # Chain to quality + compliance review, track sub-task IDs
        qr_task = trigger_quality_review.delay(article_id, humanized)
        cr_task = trigger_compliance_review.delay(article_id, humanized)

        # Append sub-task IDs to the parent GenerationTask for log linking
        gt = db.query(GenerationTask).filter(GenerationTask.article_id == article_id).first()
        if gt:
            try:
                existing = json.loads(gt.sub_task_ids) if gt.sub_task_ids else []
                existing.extend([qr_task.id, cr_task.id])
                gt.sub_task_ids = json.dumps(existing)
                db.commit()
            except Exception:
                pass

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
    """异步蒸馏：两阶段（证据提取 → 凝练指南），实时更新进度"""
    db = SessionLocal()
    try:
        # 文章压缩（替代 800 字硬截断）
        combined_articles = _compress_articles(articles_content)

        # 标记 extracting
        account = db.query(Account).filter(Account.id == account_id).first()
        if account:
            account.style_profile_status = "extracting"
            db.commit()

        llm_url = settings.llm_service_url.rstrip("/")

        # Stage 1：证据提取（低温度，重证据）
        with httpx.Client(timeout=120.0) as client:
            resp = client.post(f"{llm_url}/chat", json={
                "scenario": "distill-extract",
                "task_id": self.request.id,
                "account_id": account_id,
                "variables": {
                    "num_articles": str(num_articles),
                    "articles_content": combined_articles,
                },
            })
            resp.raise_for_status()
            data = resp.json()
        features = (data.get("content") or "").strip()
        if not features:
            raise ValueError("Stage 1 证据提取返回内容为空")

        # 标记 synthesizing
        account = db.query(Account).filter(Account.id == account_id).first()
        if account:
            account.style_profile_status = "synthesizing"
            db.commit()

        # Stage 2：凝练指南（中温度，重表达）
        with httpx.Client(timeout=120.0) as client:
            resp = client.post(f"{llm_url}/chat", json={
                "scenario": "distill-synthesize",
                "task_id": self.request.id,
                "account_id": account_id,
                "variables": {
                    "features": features,
                },
            })
            resp.raise_for_status()
            data = resp.json()
        guide = (data.get("content") or "").strip()
        if not guide:
            raise ValueError("Stage 2 凝练指南返回内容为空")

        # 落库整段指南
        account = db.query(Account).filter(Account.id == account_id).first()
        if account:
            account.style_profile = guide
            account.style_profile_status = "ready"
            account.style_profile_version = (account.style_profile_version or 0) + 1
            account.style_profile_updated_at = datetime.now(timezone.utc)
            db.commit()

        db.close()
        return {"account_id": account_id, "status": "ready"}

    except Exception as e:
        account = db.query(Account).filter(Account.id == account_id).first()
        if account:
            account.style_profile_status = "failed"
            account.style_profile = str(e)
            db.commit()
        db.close()
        raise


@celery_app.task(bind=True)
def trigger_material_summary(self, material_id: int, title: str, content: str):
    """生成素材摘要：标题+内容 → 150-300字摘要，落库"""
    db = SessionLocal()
    try:
        material = db.query(MpMaterial).filter(MpMaterial.id == material_id).first()
        if not material:
            raise ValueError(f"素材不存在: {material_id}")

        llm_url = settings.llm_service_url.rstrip("/")
        with httpx.Client(timeout=120.0) as client:
            resp = client.post(f"{llm_url}/chat", json={
                "scenario": "material-summary",
                "task_id": self.request.id,
                "account_id": 0,
                "variables": {
                    "title": title or "",
                    "content": content or "",
                    "user_prompt": f"请为以下文章生成简洁摘要：\n\n标题：{title or ''}\n\n内容：{content or ''}",
                },
            })
            resp.raise_for_status()
            data = resp.json()

        summary = (data.get("content") or "").strip()
        if not summary:
            raise ValueError("摘要生成返回内容为空")

        # 保存到数据库
        material.summary = summary
        db.commit()

        return {"material_id": material_id, "summary": summary}
    finally:
        db.close()


@celery_app.task(bind=True)
def trigger_direction_generation(self, account_id: int, idea: str, word_count: str = None):
    """生成写作方向：想法 → 3-5 个不同切入角度"""
    db = SessionLocal()
    try:
        # 获取账号的结构化画像
        account = db.query(Account).filter(Account.id == account_id).first()
        structured = None
        if account and account.style_profile_structured:
            try:
                structured = json.loads(account.style_profile_structured)
            except (json.JSONDecodeError, TypeError):
                pass

        # 构建变量
        variables = {"idea": idea}
        if word_count:
            variables["word_count"] = f"字数{word_count}。"
        else:
            variables["word_count"] = "字数1500左右。"

        if structured:
            variables["thinking_pattern"] = structured.get("thinking_pattern", "")
            variables["structure_pattern"] = structured.get("structure_pattern", "")

        llm_url = settings.llm_service_url.rstrip("/")
        with httpx.Client(timeout=120.0) as client:
            resp = client.post(f"{llm_url}/chat", json={
                "scenario": "direction",
                "task_id": self.request.id,
                "account_id": account_id,
                "variables": variables,
            })
            resp.raise_for_status()
            data = resp.json()

        content = data.get("content", "")
        if not content:
            raise ValueError("方向生成返回内容为空")

        # 解析 JSON 输出
        directions = []
        try:
            parsed = json.loads(content)
            if isinstance(parsed, list):
                directions = parsed
            elif isinstance(parsed, dict) and "directions" in parsed:
                directions = parsed["directions"]
        except json.JSONDecodeError:
            match = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', content, re.DOTALL)
            if match:
                try:
                    parsed = json.loads(match.group(1))
                    if isinstance(parsed, list):
                        directions = parsed
                    elif isinstance(parsed, dict) and "directions" in parsed:
                        directions = parsed["directions"]
                except json.JSONDecodeError:
                    pass

        # Fallback: parse numbered/bulleted text lines into directions
        if not directions:
            text_lines = []
            for line in content.strip().split("\n"):
                line = line.strip()
                if not line:
                    continue
                # Match "1. title" / "1) title" / "- title" / "• title"
                m = re.match(r'^(?:\d+[\.\)]\s*|[-•]\s+)(.+)', line)
                if m:
                    title = re.sub(r'\*+$', '', m.group(1)).strip()
                    if title:
                        text_lines.append(title)
                        continue
                # Match "方向一：title" / "角度1：title"
                m = re.match(r'^(?:方向|角度)\s*[一二三四五六七八九十\d]+\s*[：:]\s*(.+)', line)
                if m:
                    title = m.group(1).strip()
                    if title:
                        text_lines.append(title)
                        continue
                # Match "**A. title**" / "A) title" / "A. title"
                m = re.match(r'^(?:\*\*)?([A-E])[\.\)]\s*(.+?)(?:\*\*)?$', line)
                if m:
                    title = m.group(2).rstrip("*").strip()
                    if title:
                        text_lines.append(title)
                        continue
            if text_lines:
                labels = []
                for i, t in enumerate(text_lines[:5]):
                    labels.append({"id": chr(65 + i), "title": t})
                directions = labels

        # Final fallback: 所有解析器失败时，若 ≥3 个候选行才兜底，否则抛错
        if not directions and content.strip():
            candidates = [
                l.strip() for l in content.strip().split("\n")
                if l.strip() and 2 < len(l.strip()) < 200
            ]
            if len(candidates) >= 3:
                directions = [
                    {"id": chr(65 + i), "title": candidates[i]}
                    for i in range(min(len(candidates), 5))
                ]

        if not directions:
            raise ValueError(f"方向生成返回内容无法解析: {content[:200]}")

        return {"account_id": account_id, "directions": directions}
    finally:
        db.close()


@celery_app.task(bind=True)
def trigger_outline_generation(self, account_id: int, idea: str, direction: str):
    """生成大纲：想法+方向 → 5-8 个要点"""
    db = SessionLocal()
    try:
        account = db.query(Account).filter(Account.id == account_id).first()
        structured = None
        if account and account.style_profile_structured:
            try:
                structured = json.loads(account.style_profile_structured)
            except (json.JSONDecodeError, TypeError):
                pass

        variables = {
            "idea": idea,
            "direction": direction,
            "user_prompt": f"想法：{idea}\n\n写作方向：{direction}\n\n请生成5-8个要点的大纲，以JSON数组格式输出：[\"要点1\", \"要点2\", ...]",
        }
        if structured:
            variables["structure_pattern"] = structured.get("structure_pattern", "")

        llm_url = settings.llm_service_url.rstrip("/")
        with httpx.Client(timeout=120.0) as client:
            resp = client.post(f"{llm_url}/chat", json={
                "scenario": "outline",
                "task_id": self.request.id,
                "account_id": account_id,
                "variables": variables,
            })
            resp.raise_for_status()
            data = resp.json()

        content = data.get("content", "")
        if not content:
            raise ValueError("大纲生成返回内容为空")

        # 解析 JSON 输出
        outline = []
        try:
            parsed = json.loads(content)
            if isinstance(parsed, list):
                outline = parsed
            elif isinstance(parsed, dict) and "outline" in parsed:
                outline = parsed["outline"]
        except json.JSONDecodeError:
            match = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', content, re.DOTALL)
            if match:
                try:
                    parsed = json.loads(match.group(1))
                    if isinstance(parsed, list):
                        outline = parsed
                    elif isinstance(parsed, dict) and "outline" in parsed:
                        outline = parsed["outline"]
                except json.JSONDecodeError:
                    pass

        return {"account_id": account_id, "outline": outline}
    finally:
        db.close()


@celery_app.task(bind=True)
def trigger_title_generation(self, account_id: int, idea: str, direction: str, outline: list):
    """生成标题：想法+方向+大纲 → 3-5 个候选标题"""
    db = SessionLocal()
    try:
        account = db.query(Account).filter(Account.id == account_id).first()
        structured = None
        if account and account.style_profile_structured:
            try:
                structured = json.loads(account.style_profile_structured)
            except (json.JSONDecodeError, TypeError):
                pass

        # 构建大纲文本
        outline_text = "\n".join([f"- {p}" for p in outline]) if outline else ""

        variables = {
            "idea": idea,
            "direction": direction,
            "outline": outline_text,
            "user_prompt": f"想法：{idea}\n\n写作方向：{direction}\n\n大纲：\n{outline_text}\n\n请生成3-5个候选标题，以JSON字符串数组格式输出：[\"标题1\", \"标题2\", ...]",
        }
        if account and account.style_profile:
            variables["style_profile"] = account.style_profile

        llm_url = settings.llm_service_url.rstrip("/")
        with httpx.Client(timeout=120.0) as client:
            resp = client.post(f"{llm_url}/chat", json={
                "scenario": "title",
                "task_id": self.request.id,
                "account_id": account_id,
                "variables": variables,
            })
            resp.raise_for_status()
            data = resp.json()

        content = data.get("content", "")
        if not content:
            raise ValueError("标题生成返回内容为空")

        # 解析 JSON 输出
        titles = []
        try:
            parsed = json.loads(content)
            if isinstance(parsed, list):
                titles = [t for t in parsed if isinstance(t, str)]
        except json.JSONDecodeError:
            match = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', content, re.DOTALL)
            if match:
                try:
                    parsed = json.loads(match.group(1))
                    if isinstance(parsed, list):
                        titles = [t for t in parsed if isinstance(t, str)]
                except json.JSONDecodeError:
                    pass

        if not titles:
            # Fallback: 将 idea 本身作为标题
            titles = [idea[:50]]

        return {"account_id": account_id, "titles": titles}
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
                "task_id": self.request.id,
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
                "task_id": self.request.id,
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
    """从评审文本中提取总分（优先匹配"总分"行，否则取最后一个合法分数）"""
    import re

    # 优先匹配 "总分：85" 或 "总分: 85" 或 "总分 85"
    total_match = re.search(r"总分[：:\s]*(\d{1,3})", text)
    if total_match:
        score = int(total_match.group(1))
        if 0 <= score <= 100:
            return score

    # 其次匹配 "综合评分：85" 等
    overall_match = re.search(r"(?:综合|最终)(?:评分|得分)[：:\s]*(\d{1,3})", text)
    if overall_match:
        score = int(overall_match.group(1))
        if 0 <= score <= 100:
            return score

    # 兜底：取最后一个 0-100 的数字（通常是总分）
    nums = re.findall(r"\b([0-9]{1,3})\b", text)
    if nums:
        scores = [int(n) for n in nums if 0 <= int(n) <= 100]
        if scores:
            return scores[-1]  # 最后一个，不是平均值

    return 0
