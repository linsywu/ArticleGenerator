"""
采集任务管理 API
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from collections import defaultdict

from ..database import get_db
from ..models import CollectTask, CollectLog
from ..schemas import CollectTaskCreate, CollectTaskUpdate, CollectTaskResponse

router = APIRouter(prefix="/collect-tasks", tags=["采集任务管理"])


@router.get("", response_model=List[CollectTaskResponse])
def list_collect_tasks(
    status: Optional[str] = Query(None, description="按状态筛选"),
    db: Session = Depends(get_db),
):
    """获取采集任务列表"""
    query = db.query(CollectTask)
    if status:
        query = query.filter(CollectTask.status == status)
    tasks = query.order_by(CollectTask.id.desc()).all()

    # Batch fetch all logs for these tasks
    task_ids = [t.id for t in tasks]
    all_logs = (
        db.query(CollectLog)
        .filter(CollectLog.task_id.in_(task_ids))
        .order_by(CollectLog.task_id, CollectLog.created_at.desc())
        .all()
    )

    # Group logs by task_id
    task_logs = defaultdict(list)
    for log in all_logs:
        task_logs[log.task_id].append(log)

    result = []
    for task in tasks:
        task_dict = {c.name: getattr(task, c.name) for c in task.__table__.columns}
        logs = task_logs.get(task.id, [])
        if logs:
            # Only aggregate the most recent execution batch (within 5 seconds of latest)
            latest_time = logs[0].created_at
            recent_logs = [l for l in logs if l.created_at and (latest_time - l.created_at).total_seconds() <= 5]
            task_dict["last_result"] = {
                "total_count": sum(l.total_count or 0 for l in recent_logs),
                "success_count": sum(l.success_count or 0 for l in recent_logs),
                "fail_count": sum(l.fail_count or 0 for l in recent_logs),
                "executed_at": latest_time.isoformat() if latest_time else None,
            }
        else:
            task_dict["last_result"] = None
        result.append(task_dict)

    return result


@router.post("", response_model=CollectTaskResponse)
def create_collect_task(data: CollectTaskCreate, db: Session = Depends(get_db)):
    """新增采集任务"""
    task = CollectTask(**data.model_dump())
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


@router.get("/{task_id}", response_model=CollectTaskResponse)
def get_collect_task(task_id: int, db: Session = Depends(get_db)):
    """获取采集任务详情"""
    task = db.query(CollectTask).filter(CollectTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    logs = db.query(CollectLog).filter(CollectLog.task_id == task_id)\
        .order_by(CollectLog.created_at.desc()).all()

    task_dict = {c.name: getattr(task, c.name) for c in task.__table__.columns}
    if logs:
        # Only aggregate the most recent execution batch
        latest_time = logs[0].created_at
        recent_logs = [l for l in logs if l.created_at and (latest_time - l.created_at).total_seconds() <= 5]
        task_dict["last_result"] = {
            "total_count": sum(l.total_count or 0 for l in recent_logs),
            "success_count": sum(l.success_count or 0 for l in recent_logs),
            "fail_count": sum(l.fail_count or 0 for l in recent_logs),
            "executed_at": latest_time.isoformat() if latest_time else None,
        }
    else:
        task_dict["last_result"] = None

    return task_dict


@router.put("/{task_id}", response_model=CollectTaskResponse)
def update_collect_task(task_id: int, data: CollectTaskUpdate, db: Session = Depends(get_db)):
    """编辑采集任务"""
    task = db.query(CollectTask).filter(CollectTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="采集任务不存在")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(task, k, v)
    db.commit()
    db.refresh(task)
    return task


@router.delete("/{task_id}")
def delete_collect_task(task_id: int, db: Session = Depends(get_db)):
    """删除采集任务"""
    task = db.query(CollectTask).filter(CollectTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="采集任务不存在")
    db.delete(task)
    db.commit()
    return {"message": "删除成功"}


@router.post("/{task_id}/execute")
def execute_collect_task(task_id: int, db: Session = Depends(get_db)):
    """手动执行采集任务"""
    task = db.query(CollectTask).filter(CollectTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    if task.status == "running":
        raise HTTPException(status_code=400, detail="任务正在执行中")

    from ..tasks import celery_app
    celery_task = celery_app.send_task("app.collector.worker.execute_collect_task", args=[task_id])
    return {"message": "采集任务已提交", "celery_task_id": celery_task.id}


@router.post("/{task_id}/pause")
def pause_collect_task(task_id: int, db: Session = Depends(get_db)):
    """暂停采集任务"""
    task = db.query(CollectTask).filter(CollectTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="采集任务不存在")
    task.status = "paused"
    db.commit()
    return {"message": "任务已暂停"}


@router.post("/{task_id}/resume")
def resume_collect_task(task_id: int, db: Session = Depends(get_db)):
    """恢复采集任务"""
    task = db.query(CollectTask).filter(CollectTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="采集任务不存在")
    task.status = "idle"
    db.commit()
    return {"message": "任务已恢复"}
