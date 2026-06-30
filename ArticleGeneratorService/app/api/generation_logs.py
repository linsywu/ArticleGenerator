"""
生成日志：供 LLMService 网关回调记录
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional, List
from ..database import get_db
from ..models import GenerationLog, GenerationTask, _local_iso
from ..schemas import GenerationLogCreate, GenerationLogResponse

router = APIRouter(prefix="/generation-logs", tags=["生成日志"])


def _log_to_dict(log: GenerationLog) -> dict:
    """将 ORM 对象转为 dict（避免 Pydantic 序列化 ORM 对象失败）"""
    return {
        "id": log.id,
        "scenario": log.scenario,
        "task_id": log.task_id,
        "provider_id": log.provider_id,
        "model": log.model,
        "system_prompt": log.system_prompt,
        "user_prompt": log.user_prompt,
        "prompt_tokens": log.prompt_tokens,
        "completion_tokens": log.completion_tokens,
        "latency_ms": log.latency_ms,
        "status": log.status,
        "error_message": log.error_message,
        "created_at": _local_iso(log.created_at),
    }


@router.post("")
def create_log(data: GenerationLogCreate, db: Session = Depends(get_db)):
    log = GenerationLog(**data.model_dump())
    db.add(log)
    db.commit()
    return {"message": "ok"}


@router.get("", response_model=dict)
def list_logs(
    scenario: Optional[str] = None,
    task_id: Optional[str] = Query(None, description="Celery 任务 ID"),
    page: int = 1,
    page_size: int = 50,
    db: Session = Depends(get_db),
):
    q = db.query(GenerationLog)
    if scenario:
        q = q.filter(GenerationLog.scenario == scenario)
    if task_id:
        # 查找关联的 GenerationTask，获取 sub_task_ids 以实现完整日志链
        gt = db.query(GenerationTask).filter(GenerationTask.task_id == task_id).first()
        task_ids = [task_id]
        if gt and gt.sub_task_ids:
            import json
            try:
                sub_ids = json.loads(gt.sub_task_ids)
                task_ids.extend(sub_ids)
            except (json.JSONDecodeError, TypeError):
                pass
        q = q.filter(GenerationLog.task_id.in_(task_ids))
    q = q.order_by(GenerationLog.created_at.asc())
    total = q.count()
    offset = (page - 1) * page_size
    logs = q.offset(offset).limit(page_size).all()
    return {"data": [_log_to_dict(l) for l in logs], "total": total}


@router.get("/by-generation-task/{gt_id}", response_model=dict)
def get_logs_for_generation_task(gt_id: int, db: Session = Depends(get_db)):
    """获取一个生成任务及其所有子任务链的日志（generate → humanize → reviews）"""
    gt = db.query(GenerationTask).filter(GenerationTask.id == gt_id).first()
    if not gt:
        return {"data": [], "total": 0}

    task_ids = [gt.task_id]
    if gt.sub_task_ids:
        try:
            import json
            sub_ids = json.loads(gt.sub_task_ids)
            task_ids.extend(sub_ids)
        except (json.JSONDecodeError, TypeError):
            pass

    logs = (
        db.query(GenerationLog)
        .filter(GenerationLog.task_id.in_(task_ids))
        .order_by(GenerationLog.created_at.asc())
        .all()
    )
    return {"data": [_log_to_dict(l) for l in logs], "total": len(logs)}
