"""
文章生成与微调 API（触发 Celery 任务）
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import List, Optional

from ..database import get_db
from ..models import Hotspot, Account, Article, GenerationTask, RefineTask
from ..schemas import GenerateRequest, RefineRequest, DirectionsRequest, DirectionsResponse, OutlineRequest, OutlineResponse
from ..tasks import trigger_generate, trigger_refine, celery_app, trigger_direction_generation, trigger_outline_generation

router = APIRouter(prefix="/generate", tags=["文章生成"])


@router.post("/trigger")
def trigger_article_generation(data: GenerateRequest, db: Session = Depends(get_db)):
    """触发生成：热点 ID 列表 或 自定义主题 + 账号 ID"""
    account = db.query(Account).filter(Account.id == data.account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="账号不存在")

    if not data.hotspot_ids and not data.custom_topic:
        raise HTTPException(status_code=400, detail="请选择至少一个热点或输入自定义主题")

    task_ids = []

    # 自定义主题：创建独立任务（不关联热点）
    if data.custom_topic:
        task = trigger_generate.delay(data.custom_topic, data.account_id, hotspot_id=None, outline=data.outline, word_count=data.word_count)
        task_ids.append({"topic": data.custom_topic, "task_id": task.id})
        gt = GenerationTask(
            task_id=task.id,
            account_id=data.account_id,
            status="pending",
        )
        db.add(gt)
    else:
        for hid in data.hotspot_ids:
            hotspot = db.query(Hotspot).filter(Hotspot.id == hid).first()
            if not hotspot:
                continue
            task = trigger_generate.delay(hotspot.title, data.account_id, hid, outline=data.outline, word_count=data.word_count)
            task_ids.append({"hotspot_id": hid, "task_id": task.id})
            gt = GenerationTask(
                task_id=task.id,
                hotspot_id=hid,
                account_id=data.account_id,
                status="pending",
            )
            db.add(gt)
    db.commit()
    return {"message": "任务已提交", "tasks": task_ids}


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
    """查询生成任务状态"""
    task = db.query(GenerationTask).filter(GenerationTask.task_id == task_id).first()
    if not task:
        return {"task_id": task_id, "status": "unknown"}
    return {
        "task_id": task.task_id,
        "status": task.status,
        "article_id": task.article_id,
        "error_message": task.error_message,
    }


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
    q = db.query(GenerationTask)
    if status:
        if status == "generating":
            q = q.filter(GenerationTask.status.in_(["pending", "running"]))
        else:
            q = q.filter(GenerationTask.status == status)
    q = q.order_by(desc(GenerationTask.created_at))
    total = q.count()
    offset = (page - 1) * page_size
    tasks = q.offset(offset).limit(page_size).all()
    result = []
    for t in tasks:
        hotspot = db.query(Hotspot).filter(Hotspot.id == t.hotspot_id).first()
        account = db.query(Account).filter(Account.id == t.account_id).first()
        result.append({
            "id": t.id,
            "task_id": t.task_id,
            "hotspot_id": t.hotspot_id,
            "account_id": t.account_id,
            "article_id": t.article_id,
            "status": t.status,
            "error_message": t.error_message,
            "created_at": t.created_at,
            "hotspot": {"id": hotspot.id, "title": hotspot.title, "source": hotspot.source} if hotspot else None,
            "account": {"id": account.id, "account_name": account.account_name, "platform": account.platform} if account else None,
        })
    return {"data": result, "total": total}


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


@router.post("/directions", response_model=DirectionsResponse)
def generate_directions(data: DirectionsRequest, db: Session = Depends(get_db)):
    """生成写作方向：根据想法和账号风格，生成 3-5 个不同的切入角度"""
    account = db.query(Account).filter(Account.id == data.account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="账号不存在")
    if not data.idea.strip():
        raise HTTPException(status_code=400, detail="想法不能为空")

    task = trigger_direction_generation.delay(data.account_id, data.idea.strip(), data.word_count)
    result = task.get(timeout=120)

    directions = result.get("directions", [])
    if not directions:
        raise HTTPException(status_code=500, detail="方向生成失败，请重试")

    return DirectionsResponse(directions=[{"id": d.get("id", str(i)), "title": d.get("title", d)} for i, d in enumerate(directions)])


@router.post("/outline", response_model=OutlineResponse)
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
    result = task.get(timeout=120)

    outline = result.get("outline", [])
    if not outline:
        raise HTTPException(status_code=500, detail="大纲生成失败，请重试")

    return OutlineResponse(outline=[{"order": o.get("order", i+1), "point": o.get("point", o)} for i, o in enumerate(outline)])
