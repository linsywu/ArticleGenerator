"""
API 供应商管理
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from ..database import get_db
from ..models import Provider
from ..schemas import ProviderCreate, ProviderUpdate, ProviderResponse

router = APIRouter(prefix="/providers", tags=["API供应商"])


@router.get("", response_model=List[ProviderResponse])
def list_providers(db: Session = Depends(get_db)):
    return db.query(Provider).order_by(Provider.id).all()


@router.post("", response_model=ProviderResponse)
def create_provider(data: ProviderCreate, db: Session = Depends(get_db)):
    p = Provider(**data.model_dump())
    db.add(p)
    db.commit()
    db.refresh(p)
    return p


@router.get("/{provider_id}", response_model=ProviderResponse)
def get_provider(provider_id: int, db: Session = Depends(get_db)):
    p = db.query(Provider).filter(Provider.id == provider_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="供应商不存在")
    return p


@router.put("/{provider_id}", response_model=ProviderResponse)
def update_provider(provider_id: int, data: ProviderUpdate, db: Session = Depends(get_db)):
    p = db.query(Provider).filter(Provider.id == provider_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="供应商不存在")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(p, k, v)
    db.commit()
    db.refresh(p)
    return p


@router.delete("/{provider_id}")
def delete_provider(provider_id: int, db: Session = Depends(get_db)):
    p = db.query(Provider).filter(Provider.id == provider_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="供应商不存在")
    db.delete(p)
    db.commit()
    return {"message": "删除成功"}
