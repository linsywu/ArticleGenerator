"""
采集凭证管理 API
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from ..database import get_db
from ..models import MpCredential
from ..schemas import MpCredentialCreate, MpCredentialUpdate, MpCredentialResponse

router = APIRouter(prefix="/credentials", tags=["采集凭证管理"])


@router.get("", response_model=List[MpCredentialResponse])
def list_credentials(db: Session = Depends(get_db)):
    """获取凭证列表"""
    return db.query(MpCredential).order_by(MpCredential.id.desc()).all()


@router.post("", response_model=MpCredentialResponse)
def create_credential(data: MpCredentialCreate, db: Session = Depends(get_db)):
    """新增凭证"""
    credential = MpCredential(**data.model_dump())
    db.add(credential)
    db.commit()
    db.refresh(credential)
    return credential


@router.get("/{credential_id}", response_model=MpCredentialResponse)
def get_credential(credential_id: int, db: Session = Depends(get_db)):
    """获取凭证详情"""
    credential = db.query(MpCredential).filter(MpCredential.id == credential_id).first()
    if not credential:
        raise HTTPException(status_code=404, detail="凭证不存在")
    return credential


@router.put("/{credential_id}", response_model=MpCredentialResponse)
def update_credential(credential_id: int, data: MpCredentialUpdate, db: Session = Depends(get_db)):
    """编辑凭证"""
    credential = db.query(MpCredential).filter(MpCredential.id == credential_id).first()
    if not credential:
        raise HTTPException(status_code=404, detail="凭证不存在")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(credential, k, v)
    db.commit()
    db.refresh(credential)
    return credential


@router.delete("/{credential_id}")
def delete_credential(credential_id: int, db: Session = Depends(get_db)):
    """删除凭证"""
    credential = db.query(MpCredential).filter(MpCredential.id == credential_id).first()
    if not credential:
        raise HTTPException(status_code=404, detail="凭证不存在")
    db.delete(credential)
    db.commit()
    return {"message": "删除成功"}


@router.post("/{credential_id}/check")
def check_credential(credential_id: int, db: Session = Depends(get_db)):
    """检测凭证有效性（暂未实现）"""
    credential = db.query(MpCredential).filter(MpCredential.id == credential_id).first()
    if not credential:
        raise HTTPException(status_code=404, detail="凭证不存在")
    return {"status": "not_implemented"}
