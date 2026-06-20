"""
采集日志 API
"""
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import Optional

from ..database import get_db
from ..models import CollectLog, CollectTask

router = APIRouter(prefix="/collect-logs", tags=["采集日志"])


@router.get("")
def list_collect_logs(
    db: Session = Depends(get_db),
    task_id: Optional[int] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """获取采集日志列表"""
    q = db.query(CollectLog)
    if task_id:
        q = q.filter(CollectLog.task_id == task_id)
    q = q.order_by(desc(CollectLog.created_at))
    total = q.count()
    items = q.offset((page - 1) * page_size).limit(page_size).all()

    result = []
    for log in items:
        task = db.query(CollectTask).filter(CollectTask.id == log.task_id).first()
        result.append({
            "id": log.id,
            "task_id": log.task_id,
            "task_name": task.name if task else None,
            "account_id": log.account_id,
            "start_time": log.start_time.isoformat() if log.start_time else None,
            "end_time": log.end_time.isoformat() if log.end_time else None,
            "total_count": log.total_count,
            "success_count": log.success_count,
            "fail_count": log.fail_count,
            "error_message": log.error_message,
            "created_at": log.created_at.isoformat() if log.created_at else None,
        })
    return {"data": result, "total": total}
