"""
文章服务层：状态转换机
"""
from datetime import datetime, timezone
from fastapi import HTTPException
from sqlalchemy.orm import Session

from ..models import Article

# 合法状态集
VALID_STATUSES = {"approved", "rejected", "published"}

# 允许的状态转换：{当前状态: [可转换到的状态列表]}
ALLOWED_TRANSITIONS = {
    "pending_review": ["approved", "rejected"],
    "approved": ["published"],
}


def update_article_status(db: Session, article_id: int, new_status: str) -> Article:
    """校验状态转换、更新文章状态，返回文章对象"""
    article = db.query(Article).filter(Article.id == article_id).first()
    if not article:
        raise HTTPException(status_code=404, detail="文章不存在")

    if new_status not in VALID_STATUSES:
        raise HTTPException(status_code=400, detail=f"无效状态: {new_status}")

    allowed = ALLOWED_TRANSITIONS.get(article.status)
    if allowed is None or new_status not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"无效的状态转换: {article.status} → {new_status}",
        )

    article.status = new_status
    if new_status == "published":
        article.published_at = datetime.now(timezone.utc)
    db.commit()
    return article
