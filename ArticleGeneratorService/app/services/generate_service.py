"""
生成服务层：触发生成、任务列表查询
"""
from fastapi import HTTPException
from sqlalchemy import desc
from sqlalchemy.orm import Session
from typing import Optional, List

from ..models import Hotspot, Account, Article, GenerationTask, _local_iso
from ..tasks import trigger_generate


def trigger_generation(
    db: Session,
    hotspot_ids: List[int],
    account_id: int,
    custom_topic: Optional[str] = None,
    outline: Optional[List[str]] = None,
    word_count: Optional[str] = None,
    direction: Optional[str] = None,
) -> dict:
    """校验参数、创建 Celery 任务和 GenerationTask 记录，返回提交结果"""
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="账号不存在")

    if not hotspot_ids and not custom_topic:
        raise HTTPException(status_code=400, detail="请选择至少一个热点或输入自定义主题")

    if hotspot_ids:
        existing = db.query(Hotspot).filter(Hotspot.id.in_(hotspot_ids)).all()
        existing_ids = {h.id for h in existing}
        invalid_ids = [hid for hid in hotspot_ids if hid not in existing_ids]
        if invalid_ids:
            raise HTTPException(status_code=400, detail=f"无效的热点ID: {invalid_ids}")

    task_ids = []

    if custom_topic:
        task = trigger_generate.delay(topic=custom_topic, account_id=account_id, hotspot_id=None, outline=outline, word_count=word_count, direction=direction)
        task_ids.append({"topic": custom_topic, "task_id": task.id})
        gt = GenerationTask(
            task_id=task.id,
            account_id=account_id,
            status="pending",
        )
        db.add(gt)
    else:
        for hid in hotspot_ids:
            hotspot = db.query(Hotspot).filter(Hotspot.id == hid).first()
            task = trigger_generate.delay(hotspot.title, account_id, hid, outline=outline, word_count=word_count)
            task_ids.append({"hotspot_id": hid, "task_id": task.id})
            gt = GenerationTask(
                task_id=task.id,
                hotspot_id=hid,
                account_id=account_id,
                status="pending",
            )
            db.add(gt)
    db.commit()
    return {"message": "任务已提交", "tasks": task_ids}


def list_generation_tasks(
    db: Session,
    status: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
) -> dict:
    """查询生成任务列表，支持状态筛选和分页"""
    q = db.query(GenerationTask)
    if status:
        if status == "generating":
            q = q.filter(GenerationTask.status.in_(["pending", "running"]))
        else:
            q = q.filter(GenerationTask.status == status)
    q = q.order_by(desc(GenerationTask.created_at))
    total = q.count()
    offset = (page - 1) * page_size
    tasks = q.offset(offset).limit(page_size).all()
    result = []
    for t in tasks:
        hotspot = db.query(Hotspot).filter(Hotspot.id == t.hotspot_id).first()
        account = db.query(Account).filter(Account.id == t.account_id).first()
        article_title = None
        if t.article_id:
            article = db.query(Article).filter(Article.id == t.article_id).first()
            if article:
                article_title = article.title

        result.append({
            "id": t.id,
            "task_id": t.task_id,
            "hotspot_id": t.hotspot_id,
            "account_id": t.account_id,
            "article_id": t.article_id,
            "status": t.status,
            "error_message": t.error_message,
            "title": article_title,
            "created_at": _local_iso(t.created_at),
            "hotspot": {"id": hotspot.id, "title": hotspot.title, "source": hotspot.source} if hotspot else None,
            "account": {"id": account.id, "account_name": account.account_name, "platform": account.platform} if account else None,
        })
    return {"data": result, "total": total}
