"""
公众号管理 API
"""
import json
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from ..database import get_db
from ..models import MpAccount
from ..schemas import (
    MpAccountCreate,
    MpAccountUpdate,
    MpAccountResponse,
    MpAccountImportByNameRequest,
    MpAccountImportByUrlRequest,
)

router = APIRouter(prefix="/mp-accounts", tags=["公众号管理"])


@router.get("", response_model=List[MpAccountResponse])
def list_mp_accounts(
    track_id: Optional[int] = Query(None, description="按赛道 ID 筛选"),
    status: Optional[int] = Query(None, description="按状态筛选"),
    search: Optional[str] = Query(None, description="按名称搜索"),
    db: Session = Depends(get_db),
):
    """获取公众号列表"""
    query = db.query(MpAccount)

    if status is not None:
        query = query.filter(MpAccount.status == status)

    if search:
        query = query.filter(MpAccount.name.ilike(f"%{search}%"))

    if track_id is not None:
        # track_ids 是 JSON 字符串数组，用 LIKE 匹配
        query = query.filter(MpAccount.track_ids.ilike(f"%{track_id}%"))

    return query.order_by(MpAccount.id.desc()).all()


@router.post("", response_model=MpAccountResponse)
def create_mp_account(data: MpAccountCreate, db: Session = Depends(get_db)):
    """创建公众号"""
    account = MpAccount(**data.model_dump())
    db.add(account)
    db.commit()
    db.refresh(account)
    return account


@router.get("/{account_id}", response_model=MpAccountResponse)
def get_mp_account(account_id: int, db: Session = Depends(get_db)):
    """获取公众号详情"""
    account = db.query(MpAccount).filter(MpAccount.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="公众号不存在")
    return account


@router.put("/{account_id}", response_model=MpAccountResponse)
def update_mp_account(account_id: int, data: MpAccountUpdate, db: Session = Depends(get_db)):
    """更新公众号"""
    account = db.query(MpAccount).filter(MpAccount.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="公众号不存在")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(account, k, v)
    db.commit()
    db.refresh(account)
    return account


@router.patch("/{account_id}/status")
def toggle_mp_account_status(account_id: int, db: Session = Depends(get_db)):
    """启停公众号"""
    account = db.query(MpAccount).filter(MpAccount.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="公众号不存在")
    account.status = 0 if account.status == 1 else 1
    db.commit()
    return {"message": "状态已更新", "status": account.status}


@router.delete("/{account_id}")
def delete_mp_account(account_id: int, db: Session = Depends(get_db)):
    """删除公众号"""
    account = db.query(MpAccount).filter(MpAccount.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="公众号不存在")
    db.delete(account)
    db.commit()
    return {"message": "删除成功"}


@router.post("/import-by-name")
def import_mp_account_by_name(data: MpAccountImportByNameRequest):
    """按名称导入公众号（暂未实现）"""
    return {
        "message": "Import functionality will be available after collector engine is built",
        "status": "not_implemented",
    }


@router.post("/import-by-url")
def import_mp_account_by_url(data: MpAccountImportByUrlRequest):
    """按链接导入公众号（暂未实现）"""
    return {
        "message": "Import functionality will be available after collector engine is built",
        "status": "not_implemented",
    }
