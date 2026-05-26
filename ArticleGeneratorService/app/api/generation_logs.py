"""
生成日志：供 LLMService 网关回调记录
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import Optional
from ..database import get_db
from ..models import GenerationLog
from ..schemas import GenerationLogCreate

router = APIRouter(prefix="/generation-logs", tags=["生成日志"])


@router.post("")
def create_log(data: GenerationLogCreate, db: Session = Depends(get_db)):
    log = GenerationLog(**data.model_dump())
    db.add(log)
    db.commit()
    return {"message": "ok"}


@router.get("")
def list_logs(
    scenario: Optional[str] = None,
    page: int = 1,
    page_size: int = 50,
    db: Session = Depends(get_db),
):
    q = db.query(GenerationLog)
    if scenario:
        q = q.filter(GenerationLog.scenario == scenario)
    q = q.order_by(GenerationLog.created_at.desc())
    total = q.count()
    offset = (page - 1) * page_size
    logs = q.offset(offset).limit(page_size).all()
    return {"data": logs, "total": total}
