"""
统一任务查询 API：合并 generation_tasks 和 refine_tasks
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc, union, literal_column, text
from typing import List, Optional
import json

from ..database import get_db
from ..models import GenerationTask, RefineTask, Article, Hotspot, Account

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
            # Target: hotspot.title or article.title
            if row.hotspot_id:
                hotspot = db.query(Hotspot).filter(Hotspot.id == row.hotspot_id).first()
                if hotspot:
                    target = hotspot.title
            if not target and row.article_id:
                article = db.query(Article).filter(Article.id == row.article_id).first()
                if article:
                    target = article.title or target
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
            "created_at": row.created_at.isoformat() if row.created_at else None,
            "updated_at": row.updated_at.isoformat() if row.updated_at else None,
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

    return {
        "tasks": tasks,
        "running_count": running_count,
        "pending_count": pending_count,
        "completed_count": completed_q + completed_ref_q,
    }
