"""
采集日志 API
"""
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import Optional

from ..database import get_db
from ..models import CollectLog, CollectTask, MpAccount
from ..schemas import CollectLogResponse, CollectLogListResponse

router = APIRouter(prefix="/collect-logs", tags=["采集日志"])


@router.get("", response_model=CollectLogListResponse)
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

    # Batch-fetch tasks and accounts to avoid N+1
    task_ids = {l.task_id for l in items}
    account_ids = {l.account_id for l in items if l.account_id}
    tasks_map = {t.id: t for t in db.query(CollectTask).filter(CollectTask.id.in_(task_ids)).all()} if task_ids else {}
    accounts_map = {a.id: a for a in db.query(MpAccount).filter(MpAccount.id.in_(account_ids)).all()} if account_ids else {}

    result = []
    for log in items:
        task = tasks_map.get(log.task_id)
        account = accounts_map.get(log.account_id) if log.account_id else None
        result.append({
            "id": log.id,
            "task_id": log.task_id,
            "task_name": task.name if task else None,
            "account_id": log.account_id,
            "account": {"id": account.id, "name": account.name} if account else None,
            "start_time": log.start_time.isoformat() if log.start_time else None,
            "end_time": log.end_time.isoformat() if log.end_time else None,
            "total_count": log.total_count,
            "success_count": log.success_count,
            "fail_count": log.fail_count,
            "error_message": log.error_message,
            "created_at": log.created_at.isoformat() if log.created_at else None,
        })
    return {"data": result, "total": total}
