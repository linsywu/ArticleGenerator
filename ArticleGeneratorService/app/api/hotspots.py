"""
热点 API
"""
import sys
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_, desc
from typing import Optional, List

from ..database import get_db
from ..models import Hotspot
from ..schemas import HotspotResponse, HotspotBase, HotspotListResponse
from ..config import settings

router = APIRouter(prefix="/hotspots", tags=["热点"])


def _run_crawl():
    """调用 HotspotCrawler 抓取热点"""
    crawler_root = Path(__file__).resolve().parent.parent.parent.parent / "HotspotCrawler"
    if not crawler_root.exists():
        return {"created": 0, "total": 0, "error": "HotspotCrawler 模块不存在"}
    sys.path.insert(0, str(crawler_root))
    try:
        from crawler.sync_to_backend import sync_hotspots
        api_base = getattr(settings, "api_base_url", None) or "http://localhost:8000"
        return sync_hotspots(api_base=api_base)
    except Exception as e:
        return {"created": 0, "total": 0, "error": str(e)}
    finally:
        if str(crawler_root) in sys.path:
            sys.path.remove(str(crawler_root))


@router.get("", response_model=HotspotListResponse)
def list_hotspots(
    db: Session = Depends(get_db),
    status: Optional[str] = None,
    source: Optional[str] = None,
    keyword: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """获取热点列表，支持筛选和分页"""
    q = db.query(Hotspot)
    if status:
        q = q.filter(Hotspot.status == status)
    if source:
        q = q.filter(Hotspot.source == source)
    if keyword:
        q = q.filter(or_(Hotspot.title.contains(keyword), Hotspot.summary.contains(keyword)))
    q = q.order_by(desc(Hotspot.heat), desc(Hotspot.created_at))
    total = q.count()
    offset = (page - 1) * page_size
    items = q.offset(offset).limit(page_size).all()
    return {"data": items, "total": total}


@router.post("/crawl")
def crawl_hotspots():
    """手动拉取最新热点（调用 HotspotCrawler）"""
    return _run_crawl()


@router.get("/sources")
def list_hotspot_sources(db: Session = Depends(get_db)):
    """获取热点来源列表（用于筛选下拉，从已有热点聚合）"""
    rows = db.query(Hotspot.source).distinct().order_by(Hotspot.source).all()
    return {"sources": [r[0] for r in rows if r[0]]}


@router.post("", response_model=HotspotResponse)
def create_hotspot(data: HotspotBase, db: Session = Depends(get_db)):
    """创建热点（供抓取模块调用）"""
    hotspot = Hotspot(**data.model_dump())
    db.add(hotspot)
    db.commit()
    db.refresh(hotspot)
    return hotspot


@router.post("/batch")
def batch_create_hotspots(items: List[HotspotBase], db: Session = Depends(get_db)):
    """批量创建热点（供抓取模块调用）"""
    created = 0
    for data in items:
        # 简单去重：同标题同来源跳过
        exists = db.query(Hotspot).filter(
            Hotspot.title == data.title,
            Hotspot.source == data.source,
        ).first()
        if not exists:
            hotspot = Hotspot(**data.model_dump())
            db.add(hotspot)
            db.flush()  # 使本次循环新增在下次 exists 检查中可见
            created += 1
    db.commit()
    return {"created": created, "total": len(items)}


@router.get("/{hotspot_id}", response_model=HotspotResponse)
def get_hotspot(hotspot_id: int, db: Session = Depends(get_db)):
    """获取热点详情"""
    hotspot = db.query(Hotspot).filter(Hotspot.id == hotspot_id).first()
    if not hotspot:
        raise HTTPException(status_code=404, detail="热点不存在")
    return hotspot
