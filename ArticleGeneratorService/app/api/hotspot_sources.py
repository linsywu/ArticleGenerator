"""
热点源配置 API
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from ..database import get_db
from ..models import HotspotSource
from ..schemas import HotspotSourceCreate, HotspotSourceUpdate, HotspotSourceResponse

router = APIRouter(prefix="/hotspot-sources", tags=["热点源配置"])


@router.get("", response_model=List[HotspotSourceResponse])
def list_sources(db: Session = Depends(get_db)):
    """获取热点源列表"""
    sources = db.query(HotspotSource).order_by(HotspotSource.id).all()
    return [
        HotspotSourceResponse(
            id=s.id,
            name=s.name,
            type=s.type,
            config=s.config,
            enabled=bool(s.enabled),
            created_at=s.created_at,
        )
        for s in sources
    ]


@router.post("", response_model=HotspotSourceResponse)
def create_source(data: HotspotSourceCreate, db: Session = Depends(get_db)):
    """创建热点源"""
    s = HotspotSource(
        name=data.name,
        type=data.type,
        config=data.config,
        enabled=1 if data.enabled else 0,
    )
    db.add(s)
    db.commit()
    db.refresh(s)
    return HotspotSourceResponse(id=s.id, name=s.name, type=s.type, config=s.config, enabled=bool(s.enabled), created_at=s.created_at)


@router.get("/{source_id}", response_model=HotspotSourceResponse)
def get_source(source_id: int, db: Session = Depends(get_db)):
    """获取热点源详情"""
    s = db.query(HotspotSource).filter(HotspotSource.id == source_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="热点源不存在")
    return HotspotSourceResponse(id=s.id, name=s.name, type=s.type, config=s.config, enabled=bool(s.enabled), created_at=s.created_at)


@router.put("/{source_id}", response_model=HotspotSourceResponse)
def update_source(source_id: int, data: HotspotSourceUpdate, db: Session = Depends(get_db)):
    """更新热点源"""
    s = db.query(HotspotSource).filter(HotspotSource.id == source_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="热点源不存在")
    for k, v in data.model_dump(exclude_unset=True).items():
        if k == "enabled":
            setattr(s, k, 1 if v else 0)
        else:
            setattr(s, k, v)
    db.commit()
    db.refresh(s)
    return HotspotSourceResponse(id=s.id, name=s.name, type=s.type, config=s.config, enabled=bool(s.enabled), created_at=s.created_at)


@router.delete("/{source_id}")
def delete_source(source_id: int, db: Session = Depends(get_db)):
    """删除热点源"""
    source = db.query(HotspotSource).filter(HotspotSource.id == source_id).first()
    if not source:
        raise HTTPException(status_code=404, detail="热点源不存在")
    db.delete(source)
    db.commit()
    return {"message": "删除成功"}
