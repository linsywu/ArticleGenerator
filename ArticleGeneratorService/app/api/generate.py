"""
文章生成与微调 API（触发 Celery 任务）
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional

from ..database import get_db
from ..models import Article, Account, GenerationTask, RefineTask
from ..schemas import GenerateRequest, RefineRequest, DirectionsRequest, OutlineRequest, TitleRequest
from ..tasks import celery_app, trigger_direction_generation, trigger_outline_generation, trigger_title_generation, trigger_refine
from ..services.generate_service import trigger_generation, list_generation_tasks as _list_generation_tasks

router = APIRouter(prefix="/generate", tags=["文章生成"])


@router.post("/trigger")
def trigger_article_generation(data: GenerateRequest, db: Session = Depends(get_db)):
    """触发生成：热点 ID 列表 或 自定义主题 + 账号 ID"""
    return trigger_generation(
        db=db,
        hotspot_ids=data.hotspot_ids,
        account_id=data.account_id,
        custom_topic=data.custom_topic,
        outline=data.outline,
        word_count=data.word_count,
        direction=data.direction,
    )


@router.post("/refine/{article_id}")
def trigger_article_refine(article_id: int, data: RefineRequest, db: Session = Depends(get_db)):
    """触发热点微调（全文重写）"""
    article = db.query(Article).filter(Article.id == article_id).first()
    if not article:
        raise HTTPException(status_code=404, detail="文章不存在")
    task = trigger_refine.delay(article_id, data.keywords)
    rt = RefineTask(task_id=task.id, article_id=article_id, status="pending")
    db.add(rt)
    db.commit()
    return {"message": "微调任务已提交", "task_id": task.id}


@router.get("/refine-task/{task_id}")
def get_refine_task_status(task_id: str, db: Session = Depends(get_db)):
    """查询微调任务状态"""
    task = db.query(RefineTask).filter(RefineTask.task_id == task_id).first()
    if not task:
        return {"task_id": task_id, "status": "unknown"}
    return {
        "task_id": task.task_id,
        "article_id": task.article_id,
        "status": task.status,
        "error_message": task.error_message,
    }


@router.get("/task/{task_id}")
def get_task_status(task_id: str, db: Session = Depends(get_db)):
    """查询生成任务状态（GenerationTask DB 记录）"""
    task = db.query(GenerationTask).filter(GenerationTask.task_id == task_id).first()
    if not task:
        return {"task_id": task_id, "status": "unknown"}
    return {
        "task_id": task.task_id,
        "status": task.status,
        "article_id": task.article_id,
        "error_message": task.error_message,
    }


@router.get("/task/{task_id}/result")
def get_celery_task_result(task_id: str):
    """查询 Celery 异步任务结果（方向/大纲/标题等无 DB 记录的任务）

    从 Celery 结果后端获取任务状态与返回值。
    仅用于 /directions、/outline、/titles 等非 GenerationTask 场景。
    """
    from celery.result import AsyncResult
    from ..tasks import celery_app as _celery
    async_result = AsyncResult(task_id, app=_celery)

    if async_result.state == "PENDING":
        return {"task_id": task_id, "status": "pending"}
    if async_result.state == "STARTED":
        return {"task_id": task_id, "status": "running"}
    if async_result.state == "SUCCESS":
        return {"task_id": task_id, "status": "success", "result": async_result.result}
    if async_result.state == "FAILURE":
        return {"task_id": task_id, "status": "failed", "error_message": str(async_result.result)}
    return {"task_id": task_id, "status": "unknown"}


@router.get("/tasks")
def get_tasks_batch(task_ids: str = Query(..., description="逗号分隔的 task_id 列表"), db: Session = Depends(get_db)):
    """批量查询生成任务状态"""
    ids = [t.strip() for t in task_ids.split(",") if t.strip()]
    if not ids:
        return {"tasks": []}
    tasks = db.query(GenerationTask).filter(GenerationTask.task_id.in_(ids)).all()
    return {
        "tasks": [
            {
                "task_id": t.task_id,
                "hotspot_id": t.hotspot_id,
                "status": t.status,
                "article_id": t.article_id,
                "error_message": t.error_message,
            }
            for t in tasks
        ],
    }


@router.get("/tasks/list")
def list_generation_tasks(
    db: Session = Depends(get_db),
    status: Optional[str] = Query(None, description="generating/pending/running/success/failed/cancelled"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """任务列表，支持状态筛选和分页。generating 表示 pending+running"""
    return _list_generation_tasks(db=db, status=status, page=page, page_size=page_size)


@router.post("/tasks/{task_id}/cancel")
def cancel_generation_task(task_id: str, db: Session = Depends(get_db)):
    """取消生成任务（仅 pending/running 可取消）"""
    task = db.query(GenerationTask).filter(GenerationTask.task_id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    if task.status not in ("pending", "running"):
        raise HTTPException(status_code=400, detail=f"任务状态为 {task.status}，无法取消")
    try:
        celery_app.control.revoke(task_id, terminate=True)
    except Exception:
        pass
    task.status = "cancelled"
    db.commit()
    return {"message": "已取消"}


@router.post("/directions")
def generate_directions(data: DirectionsRequest, db: Session = Depends(get_db)):
    """生成写作方向：根据想法和可选的账号风格，生成 3-5 个不同的切入角度"""
    if not data.idea.strip():
        raise HTTPException(status_code=400, detail="想法不能为空")

    task = trigger_direction_generation.delay(data.account_id or 0, data.idea.strip(), data.word_count)
    return {"task_id": task.id, "status": "pending", "message": "方向生成已提交"}


@router.post("/outline")
def generate_outline(data: OutlineRequest, db: Session = Depends(get_db)):
    """生成大纲：根据想法、选中的方向和账号风格，生成 5-8 个要点"""
    account = db.query(Account).filter(Account.id == data.account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="账号不存在")
    if not data.idea.strip():
        raise HTTPException(status_code=400, detail="想法不能为空")
    if not data.direction.strip():
        raise HTTPException(status_code=400, detail="写作方向不能为空")

    task = trigger_outline_generation.delay(data.account_id, data.idea.strip(), data.direction.strip())
    return {"task_id": task.id, "status": "pending", "message": "大纲生成已提交"}


@router.post("/titles")
def generate_titles(data: TitleRequest, db: Session = Depends(get_db)):
    """生成候选标题：想法+方向+大纲 → 3-5 个标题"""
    account = db.query(Account).filter(Account.id == data.account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="账号不存在")
    if not data.idea.strip():
        raise HTTPException(status_code=400, detail="想法不能为空")

    outline_points = [p for p in data.outline if p.strip()]
    task = trigger_title_generation.delay(data.account_id, data.idea.strip(), data.direction.strip(), outline_points)
    return {"task_id": task.id, "status": "pending", "message": "标题生成已提交"}
