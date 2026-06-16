"""
Celery 异步任务：文章生成与微调
"""
import json
import re
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
def trigger_generate(self, hotspot_title: str, account_id: int, hotspot_id: int = None, outline: list = None, word_count: str = None):
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

        # 获取结构化画像字段
        structured = None
        if account and account.style_profile_structured:
            try:
                structured = json.loads(account.style_profile_structured)
            except (json.JSONDecodeError, TypeError):
                pass

        # 构建增强的 user_prompt
        outline_text = ""
        if outline:
            outline_items = [f"{i+1}. {p}" for i, p in enumerate(outline)]
            outline_text = "【写作大纲】\n" + "\n".join(outline_items) + "\n\n请严格按照以上大纲逐段写作。"

        # 注入风格要求
        style_instructions = ""
        if structured:
            sp = structured
            style_instructions = (
                f"【风格要求 - 必须严格遵守】\n"
                f"句式：{sp.get('sentence_pattern', '长短句参差，避免单调')}\n"
                f"用词：{sp.get('vocabulary_pattern', '')}\n"
                f"禁忌——绝对不要出现以下内容：{sp.get('taboos', '')}\n"
                f"留白：{sp.get('blank_leaving', '道理只讲七分，不总结不升华')}\n"
            )

        # 字数指令（用户选择优先 → 账号配置 → 默认值）
        word_count_instruction = "字数1500左右。"
        if word_count:
            word_count_instruction = f"字数{word_count}。"
        elif account and account.word_count:
            word_count_instruction = f"字数{account.word_count}。"

        user_prompt = (
            f'以"{hotspot_title}"为题，写一篇文章。\n\n'
            f'{style_instructions}\n'
            f'{outline_text}\n'
            f'{word_count_instruction}'
        )

        # 调用 LLM 服务
        llm_url = settings.llm_service_url.rstrip("/")
        payload = {
            "hotspot_title": hotspot_title,
            "account_id": account_id,
            "user_prompt": user_prompt,
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

        # 提取标题：优先取第一行 # 标题，否则取第一行非空文本（截断50字）
        title = None
        lines = content.strip().split("\n")
        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue
            if stripped.startswith("# "):
                title = stripped[2:].strip()
                break
            elif stripped.startswith("## "):
                title = stripped[3:].strip()
                break
            else:
                # 第一行非空文本，当做标题（截断50字）
                title = stripped[:50]
                break
        if not title:
            title = hotspot_title[:50] if hotspot_title else None

        # 写入文章表
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
    """异步蒸馏：参考文章 → 结构化风格画像"""
    db = SessionLocal()
    try:
        # 截断过长的单篇文章（每篇最多 800 字符，防止超出 LLM 上下文窗口）
        max_per_article = 800
        truncated = []
        for a in articles_content:
            if len(a) > max_per_article:
                truncated.append(a[:max_per_article] + "\n\n[... 后续内容已截断 ...]")
            else:
                truncated.append(a)

        llm_url = settings.llm_service_url.rstrip("/")
        with httpx.Client(timeout=300.0) as client:
            resp = client.post(f"{llm_url}/chat", json={
                "scenario": "distill",
                "account_id": account_id,
                "variables": {
                    "num_articles": str(num_articles),
                    "articles_content": "\n\n---\n\n".join(truncated),
                },
            })
            resp.raise_for_status()
            data = resp.json()

        content = data.get("content", "")
        if not content:
            raise ValueError("蒸馏返回内容为空")

        # 解析 LLM 返回的结构化 JSON（多层容错）
        structured = None

        def try_parse_json(text: str):
            """尝试多种策略从 LLM 输出中提取 JSON"""
            if not text or not text.strip():
                return None

            # 策略 0: 清洗控制字符
            cleaned = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', '', text)

            # 策略 1: 直接解析清洗后的内容
            try:
                return json.loads(cleaned)
            except json.JSONDecodeError:
                pass

            # 策略 2: 提取第一个 JSON 对象 {...}
            obj_match = re.search(r'\{.*\}', cleaned, re.DOTALL)
            if obj_match:
                try:
                    return json.loads(obj_match.group(0))
                except json.JSONDecodeError:
                    pass

            # 策略 3: 提取 markdown 代码块中的 JSON
            code_match = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', cleaned, re.DOTALL)
            if code_match:
                try:
                    return json.loads(code_match.group(1))
                except json.JSONDecodeError:
                    pass

            # 策略 4: 尝试 ast.literal_eval（处理 Python dict 格式）
            try:
                import ast
                return ast.literal_eval(cleaned.strip())
            except (ValueError, SyntaxError):
                pass

            return None

        structured = try_parse_json(content)

        # 生成兼容旧版的摘要文本
        summary_text = content  # 回退：使用原始返回内容
        if structured:
            parts = []
            dim_labels = {
                "thinking_pattern": "思维特征",
                "structure_pattern": "结构模式",
                "sentence_pattern": "句式特征",
                "vocabulary_pattern": "词汇偏好",
                "evidence_type": "论据类型",
                "taboos": "禁忌清单",
                "blank_leaving": "留白程度",
            }
            for key, label in dim_labels.items():
                if structured.get(key):
                    parts.append(f"【{label}】\n{structured[key]}")
            summary_text = "\n\n".join(parts)

        account = db.query(Account).filter(Account.id == account_id).first()
        if account:
            account.style_profile = summary_text  # 兼容旧版文本画像
            account.style_profile_structured = json.dumps(structured, ensure_ascii=False) if structured else None
            account.style_profile_status = "ready" if structured else "failed"
            account.style_profile_version = (account.style_profile_version or 0) + 1
            account.style_profile_updated_at = datetime.utcnow()
            db.commit()

        return {"account_id": account_id, "status": account.style_profile_status if account else "error"}
    except Exception as e:
        # 标记失败
        account = db.query(Account).filter(Account.id == account_id).first()
        if account:
            account.style_profile_status = "failed"
            db.commit()
        raise
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

        variables = {"idea": idea, "direction": direction}
        if structured:
            variables["structure_pattern"] = structured.get("structure_pattern", "")

        llm_url = settings.llm_service_url.rstrip("/")
        with httpx.Client(timeout=120.0) as client:
            resp = client.post(f"{llm_url}/chat", json={
                "scenario": "outline",
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
        }
        if account and account.style_profile:
            variables["style_profile"] = account.style_profile

        llm_url = settings.llm_service_url.rstrip("/")
        with httpx.Client(timeout=120.0) as client:
            resp = client.post(f"{llm_url}/chat", json={
                "scenario": "title",
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
