"""Test distill task — two-stage (extract + synthesize)"""
from unittest.mock import patch, MagicMock
from app.tasks import trigger_distill
from app.models import Account
from app.database import SessionLocal


def test_distill_task_two_llm_calls_and_stores_guide():
    """蒸馏任务应调用 2 次 LLM（extract + synthesize）并落库整段指南"""
    db = SessionLocal()
    account = Account(platform="test", account_name="test_twostage")
    db.add(account)
    db.commit()
    acc_id = account.id
    db.close()

    stage1_output = (
        "作者类型：情感两性类 · 主流写法是过来人视角讲道理\n\n"
        "标志性特征：\n"
        "1. 设问式开头：「你有没有发现？」—— 反问设问开篇\n"
        "2. 短句堆叠：「他不爱你。他不心疼你。」—— 情绪高点连击"
    )
    stage2_output = "## 写作风格指南\n开头常用设问引入，如「你有没有发现...」。"

    with patch("app.tasks.httpx.Client") as mock_client:
        mock_instance = MagicMock()
        mock_client.return_value.__enter__.return_value = mock_instance

        resp1 = MagicMock()
        resp1.raise_for_status.return_value = None
        resp1.json.return_value = {"content": stage1_output}
        resp2 = MagicMock()
        resp2.raise_for_status.return_value = None
        resp2.json.return_value = {"content": stage2_output}

        mock_instance.post.side_effect = [resp1, resp2]

        result = trigger_distill(acc_id, ["## 测试文章\n\n正文内容"], 1)

    assert result["status"] == "ready"
    assert mock_instance.post.call_count == 2  # 两阶段，不是 7 维

    db = SessionLocal()
    account = db.query(Account).filter(Account.id == acc_id).first()
    assert account.style_profile_status == "ready"
    assert "写作风格指南" in (account.style_profile or "")
    assert account.style_profile_version >= 1
    db.close()


def test_distill_task_failure_marks_failed():
    """Stage 1 LLM 异常应标记为 failed"""
    db = SessionLocal()
    account = Account(platform="test", account_name="test_fail")
    db.add(account)
    db.commit()
    acc_id = account.id
    db.close()

    with patch("app.tasks.httpx.Client") as mock_client:
        mock_instance = MagicMock()
        mock_client.return_value.__enter__.return_value = mock_instance
        mock_instance.post.side_effect = Exception("LLM timeout")

        try:
            trigger_distill(acc_id, ["正文"], 1)
        except Exception:
            pass

    db = SessionLocal()
    account = db.query(Account).filter(Account.id == acc_id).first()
    assert account.style_profile_status == "failed"
    assert "LLM timeout" in (account.style_profile or "")
    db.close()


def test_distill_task_empty_stage1_marks_failed():
    """Stage 1 返回空内容应标记为 failed"""
    db = SessionLocal()
    account = Account(platform="test", account_name="test_empty")
    db.add(account)
    db.commit()
    acc_id = account.id
    db.close()

    with patch("app.tasks.httpx.Client") as mock_client:
        mock_instance = MagicMock()
        mock_client.return_value.__enter__.return_value = mock_instance
        resp1 = MagicMock()
        resp1.raise_for_status.return_value = None
        resp1.json.return_value = {"content": ""}  # 空
        mock_instance.post.side_effect = [resp1]

        try:
            trigger_distill(acc_id, ["正文"], 1)
        except Exception:
            pass

    db = SessionLocal()
    account = db.query(Account).filter(Account.id == acc_id).first()
    assert account.style_profile_status == "failed"
    db.close()


def test_compress_articles_full_text_under_threshold():
    """≤5 篇文章应保留全文"""
    from app.tasks import _compress_articles
    articles = ["短文一", "短文二"]
    result = _compress_articles(articles)
    assert "短文一" in result
    assert "短文二" in result
    assert "---" in result  # 分隔符


def test_compress_articles_samples_many_to_fifteen():
    """>15 篇文章应均匀抽样到 ≤15 篇"""
    from app.tasks import _compress_articles
    articles = [f"文章第{i}篇" for i in range(30)]
    result = _compress_articles(articles)
    # 首篇和末篇必须保留（覆盖早/近期风格）
    assert "文章第0篇" in result
    assert "文章第29篇" in result
    # 分隔符数量 ≤ 14（即 ≤15 段）
    assert result.count("---") <= 14
