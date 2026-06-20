"""
采集引擎 Worker
"""
import json
import logging
from datetime import datetime, timezone
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

        credential = db.query(MpCredential).filter(MpCredential.id == task.credential_id).first()
        if not credential:
            _fail_task(db, task, "凭证不存在")
            return
        if credential.status in ("expired", "error"):
            _fail_task(db, task, f"凭证状态异常: {credential.status}")
            return

        accounts = _resolve_accounts(db, task)
        if not accounts:
            _fail_task(db, task, "没有匹配的公众号")
            return

        task.status = "running"
        db.commit()

        client = MpClient(credential.token, credential.cookie)

        for account in accounts:
            log_entry = _create_log(db, task.id, account.id)
            try:
                success, fail = _collect_from_account(db, client, account, task)
                log_entry.success_count = success
                log_entry.fail_count = fail
                log_entry.total_count = success + fail
            except Exception as e:
                logger.exception(f"Collection failed for {account.name}")
                log_entry.error_message = str(e)
            finally:
                log_entry.end_time = _utcnow()
                db.commit()
                _update_account_stats(db, account.id)

        task.status = "idle"
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


def _collect_from_account(db, client: MpClient, account: MpAccount, task: CollectTask) -> tuple:
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

    articles = client.fetch_article_list(account.fakeid, task.collect_mode)

    success = 0
    fail = 0
    for art in articles:
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
                published_at=meta["published_at"],
                collected_at=_utcnow(),
            )
            db.add(material)
            success += 1
        except Exception as e:
            logger.exception(f"Failed to collect article: {art.get('link')}")
            fail += 1

    db.commit()
    return success, fail


def _create_log(db, task_id: int, account_id: int) -> CollectLog:
    log = CollectLog(task_id=task_id, account_id=account_id, start_time=_utcnow())
    db.add(log)
    db.commit()
    db.refresh(log)
    return log


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
