"""
素材中心 API
"""
import re
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import Optional

from ..database import get_db
from ..models import MpMaterial, MpAccount, _local_iso
from ..schemas import MpMaterialResponse, MpMaterialListResponse

router = APIRouter(prefix="/materials", tags=["素材中心"])


@router.get("", response_model=MpMaterialListResponse)
def list_materials(
    db: Session = Depends(get_db),
    account_id: Optional[int] = Query(None),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """获取素材列表"""
    q = db.query(MpMaterial)
    if account_id:
        q = q.filter(MpMaterial.account_id == account_id)
    if search:
        q = q.filter(MpMaterial.title.contains(search))
    q = q.order_by(desc(MpMaterial.collected_at))
    total = q.count()
    items = q.offset((page - 1) * page_size).limit(page_size).all()

    result = []
    for m in items:
        account = db.query(MpAccount).filter(MpAccount.id == m.account_id).first()
        result.append({
            "id": m.id,
            "account_id": m.account_id,
            "title": m.title,
            "author": m.author,
            "original_url": m.original_url,
            "cover_url": m.cover_url,
            "summary": m.summary,
            "word_count": m.word_count,
            "is_original": m.is_original,
            "published_at": _local_iso(m.published_at),
            "collected_at": _local_iso(m.collected_at),
            "created_at": _local_iso(m.created_at),
            "account": {"id": account.id, "name": account.name} if account else None,
        })
    return {"data": result, "total": total}


@router.get("/{material_id}", response_model=MpMaterialResponse)
def get_material(material_id: int, db: Session = Depends(get_db)):
    """获取素材详情"""
    material = db.query(MpMaterial).filter(MpMaterial.id == material_id).first()
    if not material:
        raise HTTPException(status_code=404, detail="素材不存在")
    account = db.query(MpAccount).filter(MpAccount.id == material.account_id).first()
    return {
        "id": material.id,
        "account_id": material.account_id,
        "title": material.title,
        "author": material.author,
        "original_url": material.original_url,
        "cover_url": material.cover_url,
        "summary": material.summary,
        "raw_html": material.raw_html,
        "content_html": material.content_html,
        "content_markdown": material.content_markdown,
        "word_count": material.word_count,
        "is_original": material.is_original,
        "published_at": _local_iso(material.published_at),
        "collected_at": _local_iso(material.collected_at),
        "created_at": _local_iso(material.created_at),
        "account": {"id": account.id, "name": account.name} if account else None,
    }


@router.post("/{material_id}/parse")
def parse_material(material_id: int, db: Session = Depends(get_db)):
    """触发延迟解析：HTML → Markdown"""
    material = db.query(MpMaterial).filter(MpMaterial.id == material_id).first()
    if not material:
        raise HTTPException(status_code=404, detail="素材不存在")
    if material.content_markdown:
        return {"content_markdown": material.content_markdown, "cached": True}

    html = material.raw_html or ""
    html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r'</?(div|p|h[1-6]|li|tr|br|article|section|header|footer)[^>]*>', '\n', html, flags=re.IGNORECASE)
    html = re.sub(r'<[^>]+>', '', html)
    html = html.replace('&nbsp;', ' ').replace('&lt;', '<').replace('&gt;', '>').replace('&amp;', '&').replace('&quot;', '"')
    html = re.sub(r'\n\s*\n', '\n\n', html)
    html = re.sub(r' +', ' ', html)
    md = html.strip()

    material.content_markdown = md
    db.commit()
    return {"content_markdown": md, "cached": False}
