"""
采集引擎 Worker
"""
import json
import logging
from datetime import datetime, timezone
from typing import Optional
from celery import shared_task
from ..database import SessionLocal
from ..models import MpCredential, MpAccount, CollectTask, MpMaterial, CollectLog
from .mp_client import MpClient

logger = logging.getLogger(__name__)


def _utcnow():
    return datetime.now(timezone.utc)


@shared_task(bind=True, max_retries=0)
def execute_collect_task(self, task_id: int):
    db = SessionLocal()
    task = None
    try:
        task = db.query(CollectTask).filter(CollectTask.id == task_id).first()
        if not task:
            logger.error(f"Task {task_id} not found")
            return

        # Create log entry early for progress tracking
        log_entry = _create_log(db, task.id)
        _log_progress(db, log_entry, "task_started", "开始执行采集任务")

        credential = db.query(MpCredential).filter(MpCredential.id == task.credential_id).first()
        if not credential:
            _log_progress(db, log_entry, "credential_check", "凭证不存在")
            log_entry.end_time = _utcnow()
            log_entry.error_message = "凭证不存在"
            _fail_task(db, task, "凭证不存在")
            return
        if credential.status in ("expired", "error"):
            _log_progress(db, log_entry, "credential_check", f"凭证状态异常: {credential.status}")
            log_entry.end_time = _utcnow()
            log_entry.error_message = f"凭证状态异常: {credential.status}"
            _fail_task(db, task, f"凭证状态异常: {credential.status}")
            return
        _log_progress(db, log_entry, "credential_check", f"凭证可用: {credential.name}")

        accounts = _resolve_accounts(db, task)
        if not accounts:
            _log_progress(db, log_entry, "accounts_resolved", "匹配到 0 个公众号")
            log_entry.end_time = _utcnow()
            log_entry.error_message = "没有匹配的公众号"
            _fail_task(db, task, "没有匹配的公众号")
            return
        _log_progress(db, log_entry, "accounts_resolved", f"匹配到 {len(accounts)} 个公众号")

        task.status = "running"
        db.commit()

        client = MpClient(credential.token, credential.cookie)

        for account in accounts:
            try:
                success, fail = _collect_from_account(db, client, account, task, log_entry)
                log_entry.success_count = (log_entry.success_count or 0) + success
                log_entry.fail_count = (log_entry.fail_count or 0) + fail
                log_entry.total_count = (log_entry.total_count or 0) + success + fail
            except Exception as e:
                logger.exception(f"Collection failed for {account.name}")
                log_entry.error_message = str(e)
            finally:
                db.commit()
                _update_account_stats(db, account.id)

        _log_progress(db, log_entry, "task_complete", f"采集任务完成，共 {len(accounts)} 个账号")
        task.status = "completed"
        log_entry.end_time = _utcnow()
        db.commit()
    except Exception as e:
        logger.exception(f"Task {task_id} failed")
        if task:
            task.status = "error"
            db.commit()
    finally:
        db.close()


def _resolve_accounts(db, task: CollectTask):
    account_ids = None
    if task.account_ids:
        try:
            account_ids = json.loads(task.account_ids)
        except (json.JSONDecodeError, TypeError):
            pass

    if account_ids:
        return db.query(MpAccount).filter(MpAccount.id.in_(account_ids), MpAccount.status == 1).all()

    track_ids = None
    if task.track_ids:
        try:
            track_ids = json.loads(task.track_ids)
        except (json.JSONDecodeError, TypeError):
            pass

    if track_ids:
        all_active = db.query(MpAccount).filter(MpAccount.status == 1).all()
        return [acc for acc in all_active if _account_in_tracks(acc, track_ids)]

    return db.query(MpAccount).filter(MpAccount.status == 1).all()


def _account_in_tracks(account, track_ids: list) -> bool:
    if not account.track_ids:
        return False
    try:
        acc_tracks = json.loads(account.track_ids)
        return any(str(t) in [str(tt) for tt in track_ids] for t in acc_tracks)
    except (json.JSONDecodeError, TypeError):
        return False


def _collect_from_account(db, client: MpClient, account: MpAccount, task: CollectTask, log_entry: CollectLog) -> tuple:
    if not account.fakeid:
        info = client.search_account(account.name)
        if info:
            account.fakeid = info["fakeid"]
            account.biz = info.get("biz")
            account.avatar = info.get("avatar")
            account.description = account.description or info.get("description")
            db.commit()

    if not account.fakeid:
        logger.warning(f"Cannot collect from {account.name}: no fakeid")
        return 0, 0

    _log_progress(db, log_entry, "fetch_list_start", f"开始获取 {account.name} 的文章列表")
    articles = client.fetch_article_list(account.fakeid, task.collect_mode)
    _log_progress(db, log_entry, "list_complete", f"文章列表获取完毕，共 {len(articles)} 篇")

    success = 0
    fail = 0
    total = len(articles)
    _log_progress(db, log_entry, "parse_start", "开始解析正文")

    for i, art in enumerate(articles):
        try:
            existing = db.query(MpMaterial).filter(MpMaterial.original_url == art["link"]).first()
            if existing:
                continue

            html = client.fetch_article_html(art["link"])
            content_hash = MpClient.content_hash(html)

            hash_exists = db.query(MpMaterial).filter(MpMaterial.content_hash == content_hash).first()
            if hash_exists:
                continue

            meta = client.extract_metadata(html)
            content_html = MpClient.extract_article_content(html)
            word_count = MpClient.estimate_word_count(html)

            # Use API create_time (Unix timestamp) as primary published_at source
            published_at = None
            if art.get("create_time"):
                try:
                    published_at = datetime.fromtimestamp(art["create_time"], tz=timezone.utc)
                except (ValueError, TypeError, OSError):
                    pass

            material = MpMaterial(
                account_id=account.id,
                title=art["title"] or meta["title"],
                author=meta["author"],
                original_url=art["link"],
                cover_url=art["cover"],
                summary=art.get("digest", ""),
                raw_html=html,
                content_html=content_html,
                content_hash=content_hash,
                word_count=word_count,
                published_at=published_at or meta["published_at"],
                collected_at=_utcnow(),
            )
            db.add(material)
            success += 1
        except Exception as e:
            logger.exception(f"Failed to collect article: {art.get('link')}")
            fail += 1

        # Log parsing progress every 5 articles
        if (i + 1) % 5 == 0:
            _log_progress(db, log_entry, "parse_progress", f"解析进度 {i + 1}/{total}")

    _log_progress(db, log_entry, "parse_complete", f"正文解析完成，成功 {success} / 失败 {fail}")
    db.commit()
    return success, fail


def _create_log(db, task_id: int, account_id: Optional[int] = None) -> CollectLog:
    log = CollectLog(task_id=task_id, account_id=account_id, start_time=_utcnow())
    db.add(log)
    db.commit()
    db.refresh(log)
    return log


def _log_progress(db, log_entry: CollectLog, step: str, detail: str = ""):
    """Append a progress step to the collect log"""
    progress = []
    if log_entry.progress:
        try:
            progress = json.loads(log_entry.progress)
        except (json.JSONDecodeError, TypeError):
            progress = []
    progress.append({
        "step": step,
        "time": _utcnow().isoformat(),
        "detail": detail,
    })
    log_entry.progress = json.dumps(progress, ensure_ascii=False)
    db.commit()


def _update_account_stats(db, account_id: int):
    account = db.query(MpAccount).filter(MpAccount.id == account_id).first()
    if account:
        account.last_collect_time = _utcnow()
        count = db.query(MpMaterial).filter(MpMaterial.account_id == account_id).count()
        account.article_count = count
        db.commit()


def _fail_task(db, task: CollectTask, reason: str):
    task.status = "error"
    db.commit()
    logger.error(f"Task {task.id} failed: {reason}")


@shared_task
def check_credentials_health():
    """Periodic credential health check (Celery Beat)"""
    db = SessionLocal()
    try:
        credentials = db.query(MpCredential).all()
        for cred in credentials:
            try:
                client = MpClient(cred.token, cred.cookie)
                if client.check_health():
                    cred.status = "normal"
                else:
                    cred.status = "expiring_soon" if cred.status == "normal" else "expired"
            except Exception:
                cred.status = "error"
            cred.check_time = _utcnow()
        db.commit()
    finally:
        db.close()
