"""
公众号管理 API
"""
import json
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from ..database import get_db
from ..models import MpAccount, MpCredential
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
def import_mp_account_by_name(data: MpAccountImportByNameRequest, db: Session = Depends(get_db)):
    """按名称批量导入公众号：通过 searchbiz 搜索并自动获取信息"""
    from ..collector.mp_client import MpClient

    credential = db.query(MpCredential).filter(MpCredential.id == data.credential_id).first()
    if not credential:
        raise HTTPException(status_code=404, detail="凭证不存在")
    if credential.status in ("expired", "error"):
        raise HTTPException(status_code=400, detail=f"凭证状态异常: {credential.status}，请先检测凭证")

    client = MpClient(credential.token, credential.cookie)
    results = {"success": [], "failed": []}

    for name in data.names:
        name = name.strip()
        if not name:
            continue
        try:
            info = client.search_account(name)
            if not info:
                results["failed"].append({"name": name, "reason": "未搜索到该公众号"})
                continue
            # Check if already exists by fakeid
            existing = db.query(MpAccount).filter(MpAccount.fakeid == info["fakeid"]).first()
            if existing:
                results["success"].append({"name": name, "id": existing.id, "action": "已存在"})
                continue
            account = MpAccount(
                name=info["name"],
                alias=info.get("alias", ""),
                fakeid=info["fakeid"],
                biz=info.get("biz", ""),
                avatar=info.get("avatar", ""),
                description=info.get("description", ""),
            )
            db.add(account)
            db.flush()
            results["success"].append({"name": name, "id": account.id, "action": "新建"})
        except Exception as e:
            results["failed"].append({"name": name, "reason": str(e)})

    db.commit()
    return results


@router.post("/import-by-url")
def import_mp_account_by_url(data: MpAccountImportByUrlRequest, db: Session = Depends(get_db)):
    """按文章链接批量导入公众号：从文章页提取公众号信息"""
    import re
    from ..collector.mp_client import MpClient

    credential = db.query(MpCredential).filter(MpCredential.id == data.credential_id).first()
    if not credential:
        raise HTTPException(status_code=404, detail="凭证不存在")
    if credential.status in ("expired", "error"):
        raise HTTPException(status_code=400, detail=f"凭证状态异常: {credential.status}，请先检测凭证")

    client = MpClient(credential.token, credential.cookie)
    results = {"success": [], "failed": []}

    for url in data.urls:
        url = url.strip()
        if not url:
            continue
        try:
            # Fetch article page HTML
            html = client.fetch_article_html(url)
            # Extract account info from HTML (公众号名称通常在 profile_link 或 js_name 中)
            # Try extracting biz from URL
            biz_match = re.search(r'__biz=([^&#]+)', html)
            name_match = re.search(r'var\s+nickname\s*=\s*["\']([^"\']+)["\']', html)
            if not name_match:
                name_match = re.search(r'<strong[^>]*class="[^"]*profile_nickname[^"]*"[^>]*>([^<]+)</strong>', html)
            if not biz_match:
                # Try extracting from the URL itself
                biz_match = re.search(r'__biz=([^&#]+)', url)

            if biz_match and name_match:
                biz = biz_match.group(1)
                name = name_match.group(1)
                existing = db.query(MpAccount).filter(MpAccount.biz == biz).first()
                if existing:
                    results["success"].append({"name": name, "id": existing.id, "action": "已存在"})
                else:
                    account = MpAccount(name=name, biz=biz)
                    db.add(account)
                    db.flush()
                    results["success"].append({"name": name, "id": account.id, "action": "新建"})
            else:
                results["failed"].append({"url": url[:60], "reason": "无法从文章中提取公众号信息"})
        except Exception as e:
            results["failed"].append({"url": url[:60], "reason": str(e)})

    db.commit()
    return results
