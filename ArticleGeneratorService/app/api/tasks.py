"""
统一任务查询 API：合并 generation_tasks 和 refine_tasks
"""
from datetime import timezone as dt_timezone
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc, union, literal_column, text
from typing import List, Optional
import json

from ..database import get_db
from ..models import GenerationTask, RefineTask, Article, Hotspot, Account, _local_iso
from celery.result import AsyncResult
from ..tasks import celery_app as _celery_app


def _as_utc(dt):
    """确保 datetime 带 UTC 时区（兼容旧数据中 naive datetime）"""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=dt_timezone.utc)
    return dt


# Valid non-DB task types for Celery fallback
_CELERY_TASK_TYPES = {"humanize", "distill", "direction", "outline", "title", "quality_review", "compliance_review"}


def _infer_task_type(task_name: str) -> str:
    """Infer task type from Celery task name by extracting suffix after trigger_.

    Example: app.tasks.trigger_humanize -> humanize
    """
    if "trigger_" in task_name:
        suffix = task_name.split("trigger_")[-1]
        # Strip any sub-module prefix (e.g., "collector." in "trigger_collector.run")
        task_type = suffix.split(".")[0]
        if task_type in _CELERY_TASK_TYPES:
            return task_type
    return "unknown"


def _celery_target(task_type: str) -> str:
    """Return a readable target label for non-DB task types."""
    labels = {
        "humanize": "去AI味处理",
        "distill": "风格蒸馏",
        "direction": "方向生成",
        "outline": "大纲生成",
        "title": "标题生成",
        "quality_review": "质量评审",
        "compliance_review": "合规评审",
    }
    return labels.get(task_type, "后台任务")


router = APIRouter(prefix="/tasks", tags=["任务中心"])


@router.get("/unified")
def query_unified_tasks(
    status: Optional[str] = Query(None, description="逗号分隔的状态筛选，如 running,pending"),
    limit: int = Query(20, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """统一查询生成任务和微调任务，合并为统一格式"""
    status_list = [s.strip() for s in status.split(",") if s.strip()] if status else []

    # Query generation_tasks
    gen_q = db.query(
        GenerationTask.task_id.label("task_id"),
        literal_column("'generate'").label("task_type"),
        GenerationTask.status.label("status"),
        GenerationTask.article_id.label("article_id"),
        GenerationTask.hotspot_id.label("hotspot_id"),
        GenerationTask.account_id.label("account_id"),
        GenerationTask.error_message.label("error_message"),
        GenerationTask.created_at.label("created_at"),
        GenerationTask.updated_at.label("updated_at"),
    )
    if status_list:
        gen_q = gen_q.filter(GenerationTask.status.in_(status_list))

    # Query refine_tasks
    ref_q = db.query(
        RefineTask.task_id.label("task_id"),
        literal_column("'refine'").label("task_type"),
        RefineTask.status.label("status"),
        RefineTask.article_id.label("article_id"),
        literal_column("NULL").label("hotspot_id"),
        literal_column("NULL").label("account_id"),
        RefineTask.error_message.label("error_message"),
        RefineTask.created_at.label("created_at"),
        RefineTask.updated_at.label("updated_at"),
    )
    if status_list:
        ref_q = ref_q.filter(RefineTask.status.in_(status_list))

    # Merge and order by created_at desc
    merged = gen_q.union_all(ref_q).order_by(desc("created_at")).limit(limit).all()

    tasks = []
    running_count = 0
    pending_count = 0

    for row in merged:
        target = None
        account_name = None
        extra_info = None

        if row.task_type == "generate":
            # Target: hotspot.title → article.title → custom_topic
            if row.hotspot_id:
                hotspot = db.query(Hotspot).filter(Hotspot.id == row.hotspot_id).first()
                if hotspot:
                    target = hotspot.title
            if not target and row.article_id:
                article = db.query(Article).filter(Article.id == row.article_id).first()
                if article:
                    target = article.title or target
            if not target and row.custom_topic:
                target = row.custom_topic
            # Account name
            if row.account_id:
                account = db.query(Account).filter(Account.id == row.account_id).first()
                if account:
                    account_name = account.account_name
                    extra_info = account.platform
        elif row.task_type == "refine":
            # Target: article.title
            if row.article_id:
                article = db.query(Article).filter(Article.id == row.article_id).first()
                if article:
                    target = article.title or "文章 #{}".format(row.article_id)
                    # Try to get extra info (keywords) from refine_history
                    if article.refine_history:
                        try:
                            history = json.loads(article.refine_history)
                            if isinstance(history, list) and len(history) > 0:
                                last = history[-1]
                                if isinstance(last, dict) and "keywords" in last:
                                    extra_info = last["keywords"]
                        except (json.JSONDecodeError, TypeError, IndexError):
                            pass

        task_item = {
            "task_id": row.task_id,
            "task_type": row.task_type,
            "status": row.status,
            "target": target or "未知主题",
            "article_id": row.article_id,
            "account_name": account_name,
            "extra_info": extra_info,
            "error_message": row.error_message,
            "created_at": _local_iso(row.created_at),
            "updated_at": _local_iso(row.updated_at),
        }
        tasks.append(task_item)

        if row.status == "running":
            running_count += 1
        elif row.status == "pending":
            pending_count += 1

    # Also count completed/failed for summary
    completed_q = db.query(GenerationTask).filter(
        GenerationTask.status.in_(["success", "failed", "cancelled"])
    ).count()
    completed_ref_q = db.query(RefineTask).filter(
        RefineTask.status.in_(["success", "failed"])
    ).count()

    # ── Celery fallback: query non-DB task types (humanize, distill, direction, outline, title, reviews) ──

    try:
        inspector = _celery_app.control.inspect()
        active_tasks = inspector.active() or {}
        reserved_tasks = inspector.reserved() or {}

        celery_task_ids = set()
        for worker_tasks in active_tasks.values():
            for t in worker_tasks:
                task_name = t.get("name", "")
                if task_name.startswith("app.tasks.trigger_"):
                    celery_task_ids.add((t["id"], task_name))
        for worker_tasks in reserved_tasks.values():
            for t in worker_tasks:
                task_name = t.get("name", "")
                if task_name.startswith("app.tasks.trigger_"):
                    celery_task_ids.add((t["id"], task_name))

        for task_id, task_name in celery_task_ids:
            # Skip if already in DB-tracked tasks
            if any(t["task_id"] == task_id for t in tasks):
                continue

            task_type = _infer_task_type(task_name)
            if task_type not in _CELERY_TASK_TYPES:
                continue

            async_result = AsyncResult(task_id, app=_celery_app)
            status = "running"
            if async_result.state == "PENDING":
                status = "pending"
            elif async_result.state == "SUCCESS":
                status = "success"
            elif async_result.state == "FAILURE":
                status = "failed"
            elif async_result.state == "REVOKED":
                status = "cancelled"

            if status_list and status not in status_list:
                continue

            task_item = {
                "task_id": task_id,
                "task_type": task_type,
                "status": status,
                "target": _celery_target(task_type) or "未知任务",
                "article_id": None,
                "account_name": None,
                "extra_info": None,
                "error_message": str(async_result.result) if async_result.state == "FAILURE" else None,
                "created_at": None,
                "updated_at": None,
            }
            tasks.append(task_item)
            if status == "running":
                running_count += 1
            elif status == "pending":
                pending_count += 1

    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"Celery task inspection failed (tasks will only show DB-tracked): {e}")

    return {
        "tasks": tasks,
        "running_count": running_count,
        "pending_count": pending_count,
        "completed_count": completed_q + completed_ref_q,
    }
