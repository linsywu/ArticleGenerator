"""
账号参考文章管理
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from ..database import get_db
from ..models import ReferenceArticle, Account
from ..schemas import ReferenceArticleCreate, ReferenceArticleResponse

router = APIRouter(prefix="/accounts/{account_id}/reference-articles", tags=["参考文章"])


@router.get("", response_model=List[ReferenceArticleResponse])
def list_articles(account_id: int, db: Session = Depends(get_db)):
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="账号不存在")
    return db.query(ReferenceArticle).filter(
        ReferenceArticle.account_id == account_id
    ).order_by(ReferenceArticle.id.desc()).all()


@router.post("", response_model=ReferenceArticleResponse)
def create_article(account_id: int, data: ReferenceArticleCreate, db: Session = Depends(get_db)):
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="账号不存在")
    article = ReferenceArticle(account_id=account_id, **data.model_dump(exclude={"account_id"}))
    db.add(article)
    db.commit()
    db.refresh(article)
    return article


@router.delete("/{article_id}")
def delete_article(account_id: int, article_id: int, db: Session = Depends(get_db)):
    article = db.query(ReferenceArticle).filter(
        ReferenceArticle.id == article_id,
        ReferenceArticle.account_id == account_id,
    ).first()
    if not article:
        raise HTTPException(status_code=404, detail="参考文章不存在")
    db.delete(article)
    db.commit()
    return {"message": "删除成功"}


@router.put("/{article_id}", response_model=ReferenceArticleResponse)
def update_article(account_id: int, article_id: int, data: ReferenceArticleCreate, db: Session = Depends(get_db)):
    article = db.query(ReferenceArticle).filter(
        ReferenceArticle.id == article_id,
        ReferenceArticle.account_id == account_id,
    ).first()
    if not article:
        raise HTTPException(status_code=404, detail="参考文章不存在")
    for k, v in data.model_dump(exclude={"account_id"}).items():
        setattr(article, k, v)
    db.commit()
    db.refresh(article)
    return article
