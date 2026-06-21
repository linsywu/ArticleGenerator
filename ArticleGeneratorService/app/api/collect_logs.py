"""
采集日志 API
"""
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import Optional

from ..database import get_db
from ..models import CollectLog, CollectTask, MpAccount, _local_iso
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
            "start_time": _local_iso(log.start_time),
            "end_time": _local_iso(log.end_time),
            "total_count": log.total_count,
            "success_count": log.success_count,
            "fail_count": log.fail_count,
            "error_message": log.error_message,
            "created_at": _local_iso(log.created_at),
        })
    return {"data": result, "total": total}


@router.get("/{log_id}", response_model=CollectLogResponse)
def get_collect_log(log_id: int, db: Session = Depends(get_db)):
    """获取单条采集日志详情（含进度时间线）"""
    log = db.query(CollectLog).filter(CollectLog.id == log_id).first()
    if not log:
        raise HTTPException(status_code=404, detail="日志不存在")

    task = db.query(CollectTask).filter(CollectTask.id == log.task_id).first()
    account = db.query(MpAccount).filter(MpAccount.id == log.account_id).first() if log.account_id else None

    # Get sibling logs from same execution batch (within 10s window)
    siblings = []
    if log.start_time:
        from datetime import timedelta
        window_start = log.start_time - timedelta(seconds=10)
        window_end = log.start_time + timedelta(seconds=10)
        sibling_rows = db.query(CollectLog).filter(
            CollectLog.task_id == log.task_id,
            CollectLog.id != log.id,
            CollectLog.start_time >= window_start,
            CollectLog.start_time <= window_end
        ).all()
        sibling_account_ids = {s.account_id for s in sibling_rows if s.account_id}
        sib_accounts_map = {a.id: a for a in db.query(MpAccount).filter(MpAccount.id.in_(sibling_account_ids)).all()} if sibling_account_ids else {}
        for s in sibling_rows:
            sib_account = sib_accounts_map.get(s.account_id) if s.account_id else None
            siblings.append({
                "id": s.id,
                "account": {"id": sib_account.id, "name": sib_account.name} if sib_account else None,
                "success_count": s.success_count,
                "fail_count": s.fail_count,
            })

    # Parse progress JSON
    progress = []
    if log.progress:
        import json
        try:
            progress = json.loads(log.progress)
        except (json.JSONDecodeError, TypeError):
            pass

    return {
        "id": log.id,
        "task_id": log.task_id,
        "task_name": task.name if task else None,
        "account_id": log.account_id,
        "account": {"id": account.id, "name": account.name} if account else None,
        "start_time": _local_iso(log.start_time),
        "end_time": _local_iso(log.end_time),
        "total_count": log.total_count,
        "success_count": log.success_count,
        "fail_count": log.fail_count,
        "error_message": log.error_message,
        "created_at": _local_iso(log.created_at),
        "progress": progress,
        "siblings": siblings,
    }
