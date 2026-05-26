"""
风格蒸馏：触发生成风格画像
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import Account, ReferenceArticle
from ..tasks import trigger_distill

router = APIRouter(prefix="/accounts", tags=["风格蒸馏"])


@router.post("/{account_id}/distill")
def distill_account_style(account_id: int, db: Session = Depends(get_db)):
    """触发风格蒸馏任务"""
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="账号不存在")

    articles = db.query(ReferenceArticle).filter(
        ReferenceArticle.account_id == account_id
    ).all()

    if not articles:
        raise HTTPException(status_code=400, detail="该账号没有参考文章，请先添加")

    articles_content = []
    for a in articles:
        articles_content.append(f"## {a.title}\n\n{a.content}")

    task = trigger_distill.delay(
        account_id=account_id,
        articles_content=articles_content,
        num_articles=len(articles),
    )

    return {"message": "蒸馏任务已提交", "task_id": task.id}
