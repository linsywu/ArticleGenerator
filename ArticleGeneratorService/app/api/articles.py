"""
文章 API：评审、发布、微调
"""
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import Optional, List

from ..database import get_db
from ..models import Article, Hotspot, Account
from ..schemas import ArticleResponse, ArticleStatusUpdate, ArticleUpdateRequest, ArticleWithRelations, ArticleListResponse

router = APIRouter(prefix="/articles", tags=["文章"])


@router.get("", response_model=ArticleListResponse)
def list_articles(
    db: Session = Depends(get_db),
    status: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """获取文章列表，支持按状态筛选"""
    q = db.query(Article)
    if status:
        q = q.filter(Article.status == status)
    q = q.order_by(desc(Article.created_at))
    total = q.count()
    offset = (page - 1) * page_size
    articles = q.offset(offset).limit(page_size).all()
    # 手动加载关联
    result = []
    for a in articles:
        item = ArticleWithRelations(
            id=a.id,
            title=a.title,
            hotspot_id=a.hotspot_id,
            account_id=a.account_id,
            content=a.content,
            status=a.status,
            refine_history=a.refine_history,
            quality_score=a.quality_score,
            compliance_score=a.compliance_score,
            review_notes=a.review_notes,
            published_at=a.published_at,
            created_at=a.created_at,
            updated_at=a.updated_at,
            hotspot=a.hotspot,
            account=a.account,
        )
        result.append(item)
    return {"data": result, "total": total}


@router.get("/{article_id}", response_model=ArticleWithRelations)
def get_article(article_id: int, db: Session = Depends(get_db)):
    """获取文章详情"""
    article = db.query(Article).filter(Article.id == article_id).first()
    if not article:
        raise HTTPException(status_code=404, detail="文章不存在")
    return ArticleWithRelations(
        **{c.key: getattr(article, c.key) for c in Article.__table__.columns},
        hotspot=article.hotspot,
        account=article.account,
    )


@router.patch("/{article_id}/status")
def update_article_status(article_id: int, data: ArticleStatusUpdate, db: Session = Depends(get_db)):
    """更新文章状态：通过/拒绝/已发布"""
    article = db.query(Article).filter(Article.id == article_id).first()
    if not article:
        raise HTTPException(status_code=404, detail="文章不存在")
    if data.status not in ("approved", "rejected", "published"):
        raise HTTPException(status_code=400, detail="无效状态")
    article.status = data.status
    if data.status == "published":
        article.published_at = datetime.now(timezone.utc)
    db.commit()
    return {"message": "更新成功"}


@router.put("/{article_id}")
def update_article(article_id: int, data: ArticleUpdateRequest, db: Session = Depends(get_db)):
    """更新文章内容"""
    article = db.query(Article).filter(Article.id == article_id).first()
    if not article:
        raise HTTPException(status_code=404, detail="文章不存在")
    if data.content is not None:
        article.content = data.content
    if data.review_notes is not None:
        article.review_notes = data.review_notes
    db.commit()
    return {"message": "更新成功"}
