"""
采集任务管理 API
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from ..database import get_db
from ..models import CollectTask
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
    return query.order_by(CollectTask.id.desc()).all()


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
        raise HTTPException(status_code=404, detail="采集任务不存在")
    return task


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
    """执行采集任务（暂未实现）"""
    task = db.query(CollectTask).filter(CollectTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="采集任务不存在")
    return {"status": "not_implemented"}


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
