"""
账号管理 API
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from ..database import get_db
from ..models import Account
from ..schemas import AccountCreate, AccountUpdate, AccountResponse
from ..deps import get_current_user, verify_any_auth

router = APIRouter(prefix="/accounts", tags=["账号管理"])


@router.get("", response_model=List[AccountResponse])
def list_accounts(db: Session = Depends(get_db), _=Depends(verify_any_auth)):
    """获取账号列表"""
    return db.query(Account).order_by(Account.id.desc()).all()


@router.post("", response_model=AccountResponse)
def create_account(data: AccountCreate, db: Session = Depends(get_db), _=Depends(get_current_user)):
    """创建账号"""
    account = Account(**data.model_dump())
    db.add(account)
    db.commit()
    db.refresh(account)
    return account


@router.get("/{account_id}", response_model=AccountResponse)
def get_account(account_id: int, db: Session = Depends(get_db), _=Depends(verify_any_auth)):
    """获取账号详情（LLM Gateway 通过 X-API-Key 调用此接口注入 style_profile）"""
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="账号不存在")
    return account


@router.put("/{account_id}", response_model=AccountResponse)
def update_account(account_id: int, data: AccountUpdate, db: Session = Depends(get_db), _=Depends(get_current_user)):
    """更新账号"""
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="账号不存在")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(account, k, v)
    db.commit()
    db.refresh(account)
    return account


@router.delete("/{account_id}")
def delete_account(account_id: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    """删除账号"""
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="账号不存在")
    db.delete(account)
    db.commit()
    return {"message": "删除成功"}
