# 风格蒸馏质量重构 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把风格蒸馏从"7 维度逐维泛化输出"重构为"两阶段引证式提炼"，产出带原文引证、跨垂类自适应的写作风格指南。

**Architecture:** Stage 1（distill-extract，低温度）通读全部文章→自动定位作者类型→提取带原文引证的标志性特征；Stage 2（distill-synthesize）把特征凝练成 600-900 字指南，含开头/结尾/标志词/禁忌四类可模仿样板。指南存入 `account.style_profile`，Gateway 已自动注入到所有生成模板的 `{{style_profile}}`，下游零改动。

**Tech Stack:** FastAPI + Celery + SQLAlchemy（后端）/ Vue 3 + Element Plus（前端）/ SQL 迁移脚本

## Global Constraints

- 注释/回复语言：中文
- 提交格式：语义化（`feat:`/`fix:`/`refactor:`/`docs:`）
- 后端测试从 `ArticleGeneratorService/` 目录运行（SQLite CWD 依赖）
- 前端变更必须浏览器验证，禁止仅 build+test 即声称通过（前端验证铁律）
- 禁止未经授权删除业务数据；本计划只删 `scenario_configs` 中的旧 `distill` 配置和 `style_profile_structured` 列（均为配置/派生数据，dev 环境安全）
- 文章压缩替代 800 字硬截断；>15 篇均匀抽样（不引入 embedding 聚类）

**设计文档:** `docs/superpowers/specs/2026-07-06-distill-quality-redesign.md`

---

## File Structure

| 文件 | 责任 | 操作 |
|------|------|------|
| `scripts/seed_providers.py` | 删除旧 `distill` 场景，新增 `distill-extract` + `distill-synthesize` 两个 scenario_config | 修改 |
| `ArticleGeneratorService/app/tasks.py` | 重写 `trigger_distill`（两阶段）；新增 `_compress_articles`/`_sample_segments` 辅助；删除 direction/outline/title 中 structured 读取 | 修改 |
| `ArticleGeneratorService/app/api/distill.py` | status 端点改为按 status 枚举返回 stage/stage_name | 修改 |
| `ArticleGeneratorService/app/models.py` | 移除 `style_profile_structured` 列 | 修改 |
| `ArticleGeneratorService/app/schemas.py` | 移除 `style_profile_structured` 字段 + validator | 修改 |
| `ArticleGeneratorDatabase/migrations/020_drop_style_profile_structured.sql` | DROP COLUMN 迁移 | 新建 |
| `ArticleGeneratorService/tests/test_distill_task.py` | 两阶段断言重写 | 修改 |
| `ArticleGeneratorService/tests/test_distill_status.py` | status 枚举断言重写 | 修改 |
| `ArticleGeneratorAdm/src/api/types.ts` | 移除 `StyleProfile` 接口 + `style_profile_structured` 字段 | 修改 |
| `ArticleGeneratorAdm/src/api/client.ts` | `getDistillStatus` 返回类型改 stage/stage_name | 修改 |
| `ArticleGeneratorAdm/src/components/accounts/DistillDialog.vue` | 展示整段指南；2 阶段进度；按钮逻辑 | 修改 |

---

### Task 1: 种子场景替换（distill-extract + distill-synthesize）

**Files:**
- Modify: `scripts/seed_providers.py`（distill 场景块，约 42-59 行；UPSERT 循环前加删除逻辑，约 235 行前）

**Interfaces:**
- Produces: 两个新 scenario_config：`distill-extract`（变量 `num_articles`/`articles_content`）、`distill-synthesize`（变量 `features`）。Task 2 的 `trigger_distill` 按这两个 scenario 名调用 LLM。

- [ ] **Step 1: 在 seed_providers.py 的 scenarios 列表中，用两个新场景替换旧 distill 场景**

找到旧 distill 场景块（`"scenario": "distill"` 那个字典），整块替换为下面两个场景：

```python
    # ── ① 风格蒸馏 Stage 1：证据提取 ──────────────────────────────────────────
    {
        "scenario": "distill-extract",
        "model": "claude-sonnet-4-20250514",
        "system_prompt_template": (
            "你是一位资深的写作风格分析师。通读以下参考文章，提炼这位作者**独有**的写作风格特征。\n\n"
            "## 工作步骤\n\n"
            "### 第一步：定位作者类型\n"
            "判断这位作者属于什么类型/垂类（情感两性、科技评论、财经分析、文学散文、生活方式、知识科普等），"
            "以及该类型的「主流写法」是什么样。后续所有「独特性」判断都以此为基准。\n\n"
            "### 第二步：提取标志性特征\n"
            "在该类型内，找出这位作者**区别于主流写法**的标志性特征。"
            "只提取这位作者确实有、而同类型普通写作者没有的特征——不要给通用写作建议。\n\n"
            "## 硬性要求（违反则失败）\n"
            "1. **每条特征必须附原文逐字引用**（用「」标出原句/原词）。没有原文佐证的特征不要写。\n"
            "2. **不要写通用建议**。「应多用短句」「应结构清晰」这类对任何作者都成立的话，一律删除。\n"
            "3. **维度自定**：不要套用固定维度。这位作者最值得提炼的方面是什么，你就提炼什么。\n"
            "4. 宁可少而准（5-8 条带引证的特征），不要多而泛。\n\n"
            "## few-shot 对比\n\n"
            "❌ 泛化（错误）：「应优先使用短句，增强冲击力」——这是通用建议，任何作者都成立\n"
            "✅ 具体（正确）：「设问式开头：「你有没有发现，越是懂事的女人，越没人疼？」"
            "——几乎每篇用反问设问开篇制造代入感」\n\n"
            "## 输出格式\n\n"
            "作者类型：<判断的类型> · <一句话主流写法画像>\n\n"
            "标志性特征：\n"
            "1. <特征名>：「<原文引用>」—— <如何体现该特征，1 句话>\n"
            "2. ...\n"
            "（5-8 条）\n\n"
            "共 {{num_articles}} 篇参考文章：\n{{articles_content}}"
        ),
        "params": '{"max_tokens": 2048, "temperature": 0.2}',
        "priority": 10,
        "description": "① 蒸馏 Stage1 证据提取：定位作者类型+提取带引证的标志性特征",
        "sort_order": 1,
    },
    # ── ① 风格蒸馏 Stage 2：凝练指南 ──────────────────────────────────────────
    {
        "scenario": "distill-synthesize",
        "model": "claude-sonnet-4-20250514",
        "system_prompt_template": (
            "你是一位写作教练。下面是一位作者的标志性特征清单（含原文引证）。"
            "请把它凝练成一份**可直接指导模仿**的《写作风格指南》。\n\n"
            "## 特征清单\n{{features}}\n\n"
            "## 要求\n\n"
            "1. **保留具体范例**：指南必须包含——标志性开头范例（1-2 例，带原句）、"
            "标志性结尾范例（1-2 例，带原句）、高频标志词清单（具体词）、禁忌词/禁忌处理清单。\n"
            "2. **指令必须由范例推出**：每条写作指令都应能从上面的特征清单找到依据，不要凭空增加。\n"
            "3. **用第二人称指令式**，把范例嵌进指令：「开头常用设问引入，如『你有没有发现...』」。\n"
            "4. **连贯成文**：不是罗列，而是一份读起来连贯的风格说明，让另一个写作者读完就能上手模仿。\n\n"
            "## 输出\n\n"
            "一份 600-900 字的《写作风格指南》，段落自定，"
            "但必须包含开头/结尾/标志词/禁忌这几类具体样板。"
        ),
        "params": '{"max_tokens": 2048, "temperature": 0.5}',
        "priority": 10,
        "description": "① 蒸馏 Stage2 凝练指南：特征清单→含范例的写作风格指南",
        "sort_order": 1,
    },
```

- [ ] **Step 2: 在 UPSERT 循环前加删除旧 distill 场景的逻辑**

在 `for s in scenarios:` 这一行之前，插入：

```python
# 删除旧的 distill 场景（已被 distill-extract + distill-synthesize 替代）
old_distill = db.query(ScenarioConfig).filter(ScenarioConfig.scenario == "distill").first()
if old_distill:
    db.delete(old_distill)
    print("Deleted legacy scenario: distill (replaced by distill-extract + distill-synthesize)")
```

- [ ] **Step 3: 更新末尾打印文案**

把 `print("Done: 1 provider + 9 scenario configs seeded (UPSERT).")` 改为：

```python
print("Done: 1 provider + scenario configs seeded (UPSERT).")
```

- [ ] **Step 4: 在 dev DB 上跑种子脚本，验证旧 distill 被删、两个新场景被创建**

Run（从 ArticleGeneratorService 目录，避免 CWD 陷阱）:
```bash
cd ArticleGeneratorService && python ../scripts/seed_providers.py
```
Expected: 输出含 `Deleted legacy scenario: distill` 和 `Created scenario: distill-extract` / `Created scenario: distill-synthesize`。

- [ ] **Step 5: 验证 DB 中场景配置正确**

Run:
```bash
cd ArticleGeneratorService && sqlite3 article_generator.db "SELECT scenario FROM scenario_configs ORDER BY scenario;"
```
Expected: 列表中**没有** `distill`，**有** `distill-extract` 和 `distill-synthesize`。

- [ ] **Step 6: Commit**

```bash
git add scripts/seed_providers.py
git commit -m "feat: 种子场景替换 distill→distill-extract+distill-synthesize"
```

---

### Task 2: 重写 trigger_distill（两阶段 + 文章压缩 + status 枚举）

**Files:**
- Modify: `ArticleGeneratorService/app/tasks.py`（`trigger_distill` 函数，约 342-466 行；文件顶部附近加两个辅助函数）
- Test: `ArticleGeneratorService/tests/test_distill_task.py`（整文件重写）

**Interfaces:**
- Consumes: Task 1 的 `distill-extract`（变量 `num_articles`/`articles_content`）和 `distill-synthesize`（变量 `features`）场景
- Produces: `trigger_distill(account_id, articles_content, num_articles)` 写入 `account.style_profile`（整段指南），状态走 `extracting` → `synthesizing` → `ready`/`failed`，不再写 `style_profile_structured`

- [ ] **Step 1: 重写测试文件 test_distill_task.py（先写失败的测试）**

整个文件替换为：

```python
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
```

- [ ] **Step 2: 运行测试，确认失败**

Run:
```bash
cd ArticleGeneratorService && pytest tests/test_distill_task.py -v
```
Expected: FAIL（`_compress_articles` 不存在；`call_count == 2` 断言失败因为当前是 7 次调用）。

- [ ] **Step 3: 在 tasks.py 顶部辅助函数区新增 _compress_articles 和 _sample_segments**

在 `resolve_article_title` 函数之后、`trigger_generate` 之前插入：

```python
def _sample_segments(article: str, max_chars: int = 1200) -> str:
    """取首段 + 中段 + 尾段，保留全文风格信号（替代硬截断）"""
    if len(article) <= max_chars:
        return article
    chunk = max_chars // 3
    head = article[:chunk]
    mid = article[len(article) // 2 : len(article) // 2 + chunk]
    tail = article[-chunk:]
    return f"{head}\n\n[...中段抽样...]\n\n{mid}\n\n[...尾段...]\n\n{tail}"


def _compress_articles(articles_content: list) -> str:
    """
    文章压缩策略（替代旧的 800 字硬截断）：
    - ≤5 篇：全文输入
    - 6-15 篇：每篇取首/中/尾段抽样
    - >15 篇：均匀抽样到 15 篇（首+末+中间均匀），再对每篇抽样
    """
    MAX_FULL = 5
    MAX_SAMPLED = 15

    articles = list(articles_content)
    if len(articles) > MAX_SAMPLED:
        n = len(articles)
        # 均匀抽样到 MAX_SAMPLED 篇：含首篇、末篇、中间均匀分布
        indices = sorted(set(round(i * (n - 1) / (MAX_SAMPLED - 1)) for i in range(MAX_SAMPLED)))
        articles = [articles[i] for i in indices]

    parts = []
    use_full = len(articles) <= MAX_FULL
    for a in articles:
        parts.append(a if use_full else _sample_segments(a))
    return "\n\n---\n\n".join(parts)
```

- [ ] **Step 4: 重写 trigger_distill 函数（整块替换原 342-466 行）**

把整个 `trigger_distill` 函数替换为：

```python
@celery_app.task(bind=True)
def trigger_distill(self, account_id: int, articles_content: list, num_articles: int):
    """异步蒸馏：两阶段（证据提取 → 凝练指南），实时更新进度"""
    db = SessionLocal()
    try:
        # 文章压缩（替代 800 字硬截断）
        combined_articles = _compress_articles(articles_content)

        # 标记 extracting
        account = db.query(Account).filter(Account.id == account_id).first()
        if account:
            account.style_profile_status = "extracting"
            db.commit()

        llm_url = settings.llm_service_url.rstrip("/")

        # Stage 1：证据提取（低温度，重证据）
        with httpx.Client(timeout=120.0) as client:
            resp = client.post(f"{llm_url}/chat", json={
                "scenario": "distill-extract",
                "task_id": self.request.id,
                "account_id": account_id,
                "variables": {
                    "num_articles": str(num_articles),
                    "articles_content": combined_articles,
                },
            })
            resp.raise_for_status()
            data = resp.json()
        features = (data.get("content") or "").strip()
        if not features:
            raise ValueError("Stage 1 证据提取返回内容为空")

        # 标记 synthesizing
        account = db.query(Account).filter(Account.id == account_id).first()
        if account:
            account.style_profile_status = "synthesizing"
            db.commit()

        # Stage 2：凝练指南（中温度，重表达）
        with httpx.Client(timeout=120.0) as client:
            resp = client.post(f"{llm_url}/chat", json={
                "scenario": "distill-synthesize",
                "task_id": self.request.id,
                "account_id": account_id,
                "variables": {
                    "features": features,
                },
            })
            resp.raise_for_status()
            data = resp.json()
        guide = (data.get("content") or "").strip()
        if not guide:
            raise ValueError("Stage 2 凝练指南返回内容为空")

        # 落库整段指南
        account = db.query(Account).filter(Account.id == account_id).first()
        if account:
            account.style_profile = guide
            account.style_profile_status = "ready"
            account.style_profile_version = (account.style_profile_version or 0) + 1
            account.style_profile_updated_at = datetime.now(timezone.utc)
            db.commit()

        db.close()
        return {"account_id": account_id, "status": "ready"}

    except Exception as e:
        account = db.query(Account).filter(Account.id == account_id).first()
        if account:
            account.style_profile_status = "failed"
            account.style_profile = str(e)
            db.commit()
        db.close()
        raise
```

- [ ] **Step 5: 运行测试，确认通过**

Run:
```bash
cd ArticleGeneratorService && pytest tests/test_distill_task.py -v
```
Expected: PASS（5 个测试全过）。

- [ ] **Step 6: 跑全量后端测试，确认无回归**

Run:
```bash
cd ArticleGeneratorService && pytest tests/ -v 2>&1 | tail -20
```
Expected: 除已知 1 个 pre-existing 失败外全部 PASS。若 direction/outline/title 相关测试因 structured 读取报错，记下来在 Task 4 处理（此时还未删 structured 列，不应报错）。

- [ ] **Step 7: Commit**

```bash
git add ArticleGeneratorService/app/tasks.py ArticleGeneratorService/tests/test_distill_task.py
git commit -m "feat: 重写 trigger_distill 为两阶段引证式蒸馏"
```

---

### Task 3: 更新 distill status 端点（status 枚举 → stage/stage_name）

**Files:**
- Modify: `ArticleGeneratorService/app/api/distill.py`（`get_distill_status`，约 42-74 行）
- Test: `ArticleGeneratorService/tests/test_distill_status.py`（整文件重写）

**Interfaces:**
- Produces: `GET /accounts/{id}/distill/status` 返回 `{status: idle|running|completed|failed, stage?: 1|2, stage_name?: str, style_profile_version?: int, error?: str}`。Task 7 前端按此消费。

- [ ] **Step 1: 重写测试 test_distill_status.py**

整个文件替换为：

```python
"""Test distill status endpoint — status enum (extracting/synthesizing)"""


def test_distill_status_idle(auth_client, db_session):
    """未蒸馏的账号返回 idle"""
    from app.models import Account
    account = Account(platform="test", account_name="test_acc")
    db_session.add(account)
    db_session.commit()
    acc_id = account.id

    resp = auth_client.get(f"/api/accounts/{acc_id}/distill/status")
    assert resp.status_code == 200
    assert resp.json()["status"] == "idle"


def test_distill_status_extracting(auth_client, db_session):
    """Stage 1 运行中返回 running + stage 1"""
    from app.models import Account
    account = Account(
        platform="test", account_name="test_acc",
        style_profile_status="extracting",
    )
    db_session.add(account)
    db_session.commit()
    acc_id = account.id

    resp = auth_client.get(f"/api/accounts/{acc_id}/distill/status")
    data = resp.json()
    assert data["status"] == "running"
    assert data["stage"] == 1
    assert "提取" in data["stage_name"]


def test_distill_status_synthesizing(auth_client, db_session):
    """Stage 2 运行中返回 running + stage 2"""
    from app.models import Account
    account = Account(
        platform="test", account_name="test_acc",
        style_profile_status="synthesizing",
    )
    db_session.add(account)
    db_session.commit()
    acc_id = account.id

    resp = auth_client.get(f"/api/accounts/{acc_id}/distill/status")
    data = resp.json()
    assert data["status"] == "running"
    assert data["stage"] == 2
    assert "凝练" in data["stage_name"]


def test_distill_status_completed(auth_client, db_session):
    """蒸馏完成返回 completed + version"""
    from app.models import Account
    account = Account(
        platform="test", account_name="test_acc",
        style_profile_status="ready", style_profile_version=2,
    )
    db_session.add(account)
    db_session.commit()
    acc_id = account.id

    resp = auth_client.get(f"/api/accounts/{acc_id}/distill/status")
    data = resp.json()
    assert data["status"] == "completed"
    assert data["style_profile_version"] == 2


def test_distill_status_failed(auth_client, db_session):
    """蒸馏失败返回 failed + error"""
    from app.models import Account
    account = Account(
        platform="test", account_name="test_acc",
        style_profile_status="failed", style_profile="LLM 超时",
    )
    db_session.add(account)
    db_session.commit()
    acc_id = account.id

    resp = auth_client.get(f"/api/accounts/{acc_id}/distill/status")
    data = resp.json()
    assert data["status"] == "failed"
    assert "error" in data


def test_distill_status_404(auth_client):
    """不存在的账号返回 404"""
    resp = auth_client.get("/api/accounts/99999/distill/status")
    assert resp.status_code == 404
```

- [ ] **Step 2: 运行测试，确认失败**

Run:
```bash
cd ArticleGeneratorService && pytest tests/test_distill_status.py -v
```
Expected: FAIL（`extracting`/`synthesizing` 状态当前返回 idle；`stage` 字段不存在）。

- [ ] **Step 3: 重写 get_distill_status 函数**

把 `distill.py` 的 `get_distill_status` 整个替换为：

```python
@router.get("/{account_id}/distill/status")
def get_distill_status(account_id: int, db: Session = Depends(get_db)):
    """查询蒸馏任务状态（两阶段）"""
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="账号不存在")

    status = account.style_profile_status or "none"

    if status == "none":
        return {"status": "idle"}

    if status in ("extracting", "synthesizing"):
        stage = 1 if status == "extracting" else 2
        stage_name = "提取特征中" if status == "extracting" else "凝练指南中"
        return {"status": "running", "stage": stage, "stage_name": stage_name}

    if status == "ready":
        return {
            "status": "completed",
            "style_profile_version": account.style_profile_version,
        }

    if status == "failed":
        return {"status": "failed", "error": account.style_profile or "蒸馏失败"}

    return {"status": "idle"}
```

同时删除文件顶部不再使用的 `import json`（如果只剩这一处用它）。检查：`json` 在本文件其他地方是否还用——若不用则删掉 import。

- [ ] **Step 4: 运行测试，确认通过**

Run:
```bash
cd ArticleGeneratorService && pytest tests/test_distill_status.py -v
```
Expected: PASS（6 个测试全过）。

- [ ] **Step 5: Commit**

```bash
git add ArticleGeneratorService/app/api/distill.py ArticleGeneratorService/tests/test_distill_status.py
git commit -m "feat: distill status 端点改为两阶段 status 枚举"
```

---

### Task 4: 删除 direction/outline/title 中冗余的 structured 读取

**Files:**
- Modify: `ArticleGeneratorService/app/tasks.py`（`trigger_direction_generation` 约 511-530、`trigger_outline_generation` 约 620-640、`trigger_title_generation` 约 682-705）

**背景:** 这三个任务当前手动从 `account.style_profile_structured` 解析 JSON，拉 `thinking_pattern`/`structure_pattern`（或 style_profile）塞进 variables。但 Gateway（`gateway.py:68-72`）已按 `account_id` 自动注入整段 `{{style_profile}}`，这些手动注入是冗余的。删除后由 Gateway 统一注入。

- [ ] **Step 1: 清理 trigger_direction_generation**

找到该函数中读取 structured 的块：

```python
        # 获取账号的结构化画像
        account = db.query(Account).filter(Account.id == account_id).first()
        structured = None
        if account and account.style_profile_structured:
            try:
                structured = json.loads(account.style_profile_structured)
            except (json.JSONDecodeError, TypeError):
                pass

        # 构建变量
        variables = {"idea": idea}
        if word_count:
            variables["word_count"] = f"字数{word_count}。"
        else:
            variables["word_count"] = "字数1500左右。"

        if structured:
            variables["thinking_pattern"] = structured.get("thinking_pattern", "")
            variables["structure_pattern"] = structured.get("structure_pattern", "")
```

替换为（删除 structured 解析和手动注入，保留 idea/word_count；account 查询移到不需要则删）：

```python
        # 变量：style_profile 由 Gateway 按 account_id 自动注入
        variables = {"idea": idea}
        if word_count:
            variables["word_count"] = f"字数{word_count}。"
        else:
            variables["word_count"] = "字数1500左右。"
```

注意：若该函数后续不再用到 `account` 变量，相应删除查询。

- [ ] **Step 2: 清理 trigger_outline_generation**

找到类似块并替换：

```python
        account = db.query(Account).filter(Account.id == account_id).first()
        structured = None
        if account and account.style_profile_structured:
            try:
                structured = json.loads(account.style_profile_structured)
            except (json.JSONDecodeError, TypeError):
                pass

        variables = {
            "idea": idea,
            "direction": direction,
            "user_prompt": f"想法：{idea}\n\n写作方向：{direction}\n\n请生成5-8个要点的大纲，以JSON数组格式输出：[\"要点1\", \"要点2\", ...]",
        }
        if structured:
            variables["structure_pattern"] = structured.get("structure_pattern", "")
```

替换为：

```python
        variables = {
            "idea": idea,
            "direction": direction,
            "user_prompt": f"想法：{idea}\n\n写作方向：{direction}\n\n请生成5-8个要点的大纲，以JSON数组格式输出：[\"要点1\", \"要点2\", ...]",
        }
```

- [ ] **Step 3: 清理 trigger_title_generation**

找到类似块并替换：

```python
        account = db.query(Account).filter(Account.id == account_id).first()
        structured = None
        if account and account.style_profile_structured:
            try:
                structured = json.loads(account.style_profile_structured)
            except (json.JSONDecodeError, TypeError):
                pass

        # 构建大纲文本
        outline_text = "\n".join([f"- {p}" for p in outline]) if outline else ""

        variables = {
            "idea": idea,
            "direction": direction,
            "outline": outline_text,
            "user_prompt": f"想法：{idea}\n\n写作方向：{direction}\n\n大纲：\n{outline_text}\n\n请生成3-5个候选标题，以JSON字符串数组格式输出：[\"标题1\", \"标题2\", ...]",
        }
        if account and account.style_profile:
            variables["style_profile"] = account.style_profile
```

替换为（删除 structured 解析 + 直接 style_profile 注入，交给 Gateway）：

```python
        # 构建大纲文本
        outline_text = "\n".join([f"- {p}" for p in outline]) if outline else ""

        variables = {
            "idea": idea,
            "direction": direction,
            "outline": outline_text,
            "user_prompt": f"想法：{idea}\n\n写作方向：{direction}\n\n大纲：\n{outline_text}\n\n请生成3-5个候选标题，以JSON字符串数组格式输出：[\"标题1\", \"标题2\", ...]",
        }
```

- [ ] **Step 4: 运行全量后端测试，确认无回归**

Run:
```bash
cd ArticleGeneratorService && pytest tests/ -v 2>&1 | tail -20
```
Expected: 除 pre-existing 失败外全部 PASS。direction/outline/title 相关测试若依赖 structured 注入，应更新测试断言（但这些任务本就靠 Gateway 注入 style_profile，测试通常不验证 variables 细节）。

- [ ] **Step 5: Commit**

```bash
git add ArticleGeneratorService/app/tasks.py
git commit -m "refactor: 删除 direction/outline/title 冗余 structured 读取，统一由 Gateway 注入"
```

---

### Task 5: 移除 style_profile_structured 字段 + 迁移

**Files:**
- Modify: `ArticleGeneratorService/app/models.py`（约 63 行）
- Modify: `ArticleGeneratorService/app/schemas.py`（约 71、80-93 行）
- Create: `ArticleGeneratorDatabase/migrations/020_drop_style_profile_structured.sql`

**前提:** Task 2-4 已确保无代码再读写 `style_profile_structured`。

- [ ] **Step 1: 从 models.py 移除列定义**

删除 `Account` 类中这一行：
```python
    style_profile_structured = Column(Text)  # JSON: 7维度结构化画像
```

- [ ] **Step 2: 从 schemas.py 移除字段和 validator**

在 `AccountResponse` 中删除字段：
```python
    style_profile_structured: Optional[Any] = None
```

删除整个 `parse_structured` validator：
```python
    @field_validator("style_profile_structured", mode="before")
    @classmethod
    def parse_structured(cls, v):
        """将数据库中的 JSON 字符串转为 dict"""
        if v is None:
            return None
        if isinstance(v, dict):
            return v
        if isinstance(v, str):
            try:
                return json.loads(v)
            except (json.JSONDecodeError, TypeError):
                return None
        return None
```

若移除后 `Any`/`json`/`field_validator` 不再被本文件其他地方使用，相应清理 import（保留被其他地方使用的）。

- [ ] **Step 3: 创建迁移文件 020_drop_style_profile_structured.sql**

```sql
-- 020: 移除 style_profile_structured 列
-- 蒸馏重构后不再使用 7 维度结构化画像，风格指南整段存于 style_profile
-- 注意：SQLite 3.35.0+ 支持 ALTER TABLE DROP COLUMN

ALTER TABLE accounts DROP COLUMN style_profile_structured;
```

- [ ] **Step 4: 在 dev DB 上执行迁移**

Run:
```bash
cd ArticleGeneratorService && sqlite3 article_generator.db "ALTER TABLE accounts DROP COLUMN style_profile_structured;"
```
Expected: 无输出（成功）。若报错 `near "DROP": syntax error`，说明 SQLite 版本 < 3.35，则改用重建表方式或升级 SQLite——记录下来人工处理。

- [ ] **Step 5: 验证列已删除，且后端测试仍通过**

Run:
```bash
cd ArticleGeneratorService && sqlite3 article_generator.db "PRAGMA table_info(accounts);" | grep structured || echo "COLUMN_REMOVED"
cd ArticleGeneratorService && pytest tests/ -v 2>&1 | tail -10
```
Expected: 输出 `COLUMN_REMOVED`；测试除 pre-existing 外全 PASS。

- [ ] **Step 6: Commit**

```bash
git add ArticleGeneratorService/app/models.py ArticleGeneratorService/app/schemas.py ArticleGeneratorDatabase/migrations/020_drop_style_profile_structured.sql
git commit -m "refactor: 移除 style_profile_structured 字段，新增 020 迁移"
```

---

### Task 6: 前端类型更新（types.ts + client.ts）

**Files:**
- Modify: `ArticleGeneratorAdm/src/api/types.ts`（约 16-24、34 行）
- Modify: `ArticleGeneratorAdm/src/api/client.ts`（约 212 行）

**Interfaces:**
- Produces: `Account` 接口移除 `style_profile_structured`；`getDistillStatus` 返回类型含 `stage`/`stage_name` 而非 `completed/total/current_dimension`。Task 7 DistillDialog 按此消费。

- [ ] **Step 1: 删除 types.ts 中的 StyleProfile 接口和字段**

删除整个 `StyleProfile` 接口（约 16-24 行）：
```typescript
export interface StyleProfile {
  thinking_pattern: string;
  structure_pattern: string;
  sentence_pattern: string;
  vocabulary_pattern: string;
  evidence_type: string;
  taboos: string;
  blank_leaving: string;
}
```

在 `Account` 接口中删除这一行：
```typescript
  style_profile_structured?: StyleProfile | null;
```

- [ ] **Step 2: 更新 client.ts 的 getDistillStatus 返回类型**

把：
```typescript
  getDistillStatus: (accountId: number) =>
    get<{ status: string; progress?: { completed: number; total: number; current_dimension: string }; style_profile_version?: number; error?: string }>(`/accounts/${accountId}/distill/status`),
```
改为：
```typescript
  getDistillStatus: (accountId: number) =>
    get<{ status: string; stage?: number; stage_name?: string; style_profile_version?: number; error?: string }>(`/accounts/${accountId}/distill/status`),
```

- [ ] **Step 3: 全局搜索确认无残留引用**

Run:
```bash
cd ArticleGeneratorAdm && grep -rn "style_profile_structured\|StyleProfile\|current_dimension" src/
```
Expected: 只有 `DistillDialog.vue` 还有引用（Task 7 处理）。若其他文件有引用，一并清理。

- [ ] **Step 4: Commit**

```bash
git add ArticleGeneratorAdm/src/api/types.ts ArticleGeneratorAdm/src/api/client.ts
git commit -m "refactor: 前端类型移除 style_profile_structured，distill status 改 stage"
```

---

### Task 7: 前端 DistillDialog.vue 改造

**Files:**
- Modify: `ArticleGeneratorAdm/src/components/accounts/DistillDialog.vue`

**目标:** 展示从 7 维分块卡片 → 整段 `style_profile` 文本；进度从 7 维维度 → 2 阶段；按钮判断从 `style_profile_structured` → `style_profile`。

- [ ] **Step 1: 重写 template 中"风格画像"展示区**

把 template 中 idle 和 completed 两个分支里的 7 维卡片展示（约 46-53、80-89 行）替换为整段指南展示。

idle 分支（约 44-55 行）替换为：
```vue
        <!-- Idle / Empty -->
        <div v-if="status === 'idle'" class="distill-center">
          <p v-if="!articles.length" class="empty-hint">请先在左侧添加参考文章</p>
          <div v-else-if="account?.style_profile" class="profile-content-area">
            <div class="guide-text">{{ account.style_profile }}</div>
          </div>
          <p v-else class="empty-hint">点击下方按钮开始蒸馏</p>
        </div>
```

completed 分支（约 80-89 行）替换为：
```vue
        <!-- Completed -->
        <div v-else-if="status === 'completed'" class="distill-center">
          <div class="profile-content-area">
            <div class="guide-text">{{ account?.style_profile || '（无指南内容）' }}</div>
          </div>
        </div>
```

- [ ] **Step 2: 重写 running 分支的进度展示（7 维 → 2 阶段）**

把 running 分支（约 58-77 行）替换为：
```vue
        <!-- Running progress -->
        <div v-else-if="status === 'running'" class="distill-center">
          <div style="text-align:center;width:100%;">
            <div style="font-size:32px;animation:pulse 1.5s infinite;">⏳</div>
            <h4 style="margin:12px 0;">正在蒸馏风格...</h4>
            <div class="progress-bar">
              <div class="progress-fill" :style="{ width: progressPercent + '%' }"></div>
            </div>
            <p class="progress-text">{{ stageName }}（{{ stage }} / 2）</p>
            <div class="stage-status">
              <span :class="{ active: stage === 1, done: stage > 1 }">① 提取特征</span>
              <span class="arrow">→</span>
              <span :class="{ active: stage === 2 }">② 凝练指南</span>
            </div>
          </div>
        </div>
```

- [ ] **Step 3: 更新按钮判断条件**

把约 120 行：
```vue
            {{ account?.style_profile_structured ? '🔄 重新蒸馏' : '🔥 开始蒸馏' }}
```
改为：
```vue
            {{ account?.style_profile ? '🔄 重新蒸馏' : '🔥 开始蒸馏' }}
```

- [ ] **Step 4: 重写 script 部分——删除 7 维逻辑，改 2 阶段**

删除 `styleDimensions` 常量（约 153-161 行）和 `getDimContent` 函数（约 163-167 行）、`dimensionStatusList` computed（约 198-203 行）。

把 `progress` ref（约 175 行）：
```typescript
const progress = ref({ completed: 0, total: 7, current_dimension: "" });
```
改为：
```typescript
const stage = ref(1);
const stageName = ref("提取特征中");
```

把 `progressPercent` computed（约 186-189 行）改为：
```typescript
const progressPercent = computed(() => (stage.value === 1 ? 25 : 75));
```

删除 `etaSeconds` computed（约 190-196 行，2 阶段无法按维度估时）。

更新 `checkStatus` 中处理 running 的分支（约 239-242 行），把：
```typescript
      if (data.progress) progress.value = data.progress;
```
改为：
```typescript
      if (data.stage) stage.value = data.stage;
      if (data.stage_name) stageName.value = data.stage_name;
```

更新 `triggerDistill` 中初始化（约 294 行），把：
```typescript
    progress.value = { completed: 0, total: 7, current_dimension: "准备中" };
```
改为：
```typescript
    stage.value = 1;
    stageName.value = "提取特征中";
```

- [ ] **Step 5: 更新 style 部分——新增 guide-text 和 stage-status 样式**

在 `<style scoped>` 中删除不再使用的 `.dim-content-card`、`.dim-content-header`、`.dim-content-text`、`.dimension-status-grid`、`.dim-status-item*`，新增：

```css
.guide-text {
  font-size: 13px; line-height: 1.8; color: var(--text-dim);
  white-space: pre-wrap; background: var(--ink-surface);
  border-left: 2px solid var(--amber); border-radius: 0 var(--radius-md) var(--radius-md) 0;
  padding: 14px 16px; max-height: 420px; overflow-y: auto; width: 100%;
}
.stage-status { margin-top: 16px; font-size: 13px; display: flex; gap: 8px; justify-content: center; align-items: center; }
.stage-status span { color: var(--text-dim); }
.stage-status span.active { color: #409eff; font-weight: 600; }
.stage-status span.done { color: var(--green-muted); }
.stage-status .arrow { color: var(--text-muted); }
```

- [ ] **Step 6: 浏览器验证（前端验证铁律——不可绕过）**

启动全栈服务（确保后端 :8000 + 前端 :5173 运行）：
```bash
./scripts/start.sh
```
浏览器访问 `/accounts`，打开某个有参考文章的账号的蒸馏弹窗：
1. 控制台无 `Uncaught TypeError`、无 `style_profile_structured is undefined` 报错
2. 未蒸馏账号：显示"点击下方按钮开始蒸馏"，按钮文案"🔥 开始蒸馏"
3. 已蒸馏账号（如陆拾一）：右侧展示整段 `style_profile` 指南文本，按钮文案"🔄 重新蒸馏"
4. 点击开始蒸馏：进度展示"提取特征中（1 / 2）"→"凝练指南中（2 / 2）"（若 LLM 服务未起，至少验证 UI 不崩）

- [ ] **Step 7: Commit**

```bash
git add ArticleGeneratorAdm/src/components/accounts/DistillDialog.vue
git commit -m "feat: DistillDialog 改展示整段指南 + 2 阶段进度"
```

---

### Task 8: 真实蒸馏端到端验证

**Files:** 无代码改动（验证任务）

**目标:** 对真实账号触发蒸馏，确认新输出带原文引证、不再有套话、整段连贯可读，且 DistillDialog 正确展示。

- [ ] **Step 1: 确保全栈服务运行（Redis + 后端 + Celery + LLM + 前端）**

Run:
```bash
redis-cli ping  # PONG
curl -s http://localhost:8000/api/accounts | head -c 100  # 有响应
curl -s http://localhost:8001/health 2>/dev/null || echo "LLM 服务需启动"
```
若有服务未起，`./scripts/start.sh` 启动。

- [ ] **Step 2: 对陆拾一账号（id=1，已有 14 篇参考文章）触发蒸馏**

浏览器 `/accounts` → 陆拾一 → 蒸馏弹窗 → "🔄 重新蒸馏"。
或 API 触发：
```bash
curl -X POST http://localhost:8000/api/accounts/1/distill -H "Authorization: Bearer <token>"
```

- [ ] **Step 3: 轮询状态直到 ready**

```bash
cd ArticleGeneratorService && watch -n 5 'sqlite3 article_generator.db "SELECT style_profile_status FROM accounts WHERE id=1;"'
```
Expected: `extracting` → `synthesizing` → `ready`。

- [ ] **Step 4: 查看新指南，人工对比质量**

```bash
cd ArticleGeneratorService && sqlite3 article_generator.db "SELECT style_profile FROM accounts WHERE id=1;"
```
Expected（质量验收标准）：
- ✅ 含原文逐字引用（「...」格式的原句）
- ✅ 不再有"应多用短句""应结构清晰"这类通用套话
- ✅ 含开头/结尾/标志词/禁忌四类具体样板
- ✅ 整段连贯，600-900 字
- ✅ 作者类型定位明确（如"情感两性类"）

- [ ] **Step 5: 浏览器验证 DistillDialog 展示新指南**

`/accounts` → 陆拾一 → 蒸馏弹窗，确认右侧正确展示新指南文本，版本号 +1。

- [ ] **Step 6: 更新设计文档状态（可选）**

若验证全通过，在设计文档顶部把"状态: 已确认，待实现"改为"状态: 已实现并验证"。

- [ ] **Step 7: 无需 commit（验证任务）；若改了设计文档则提交**

```bash
git add docs/superpowers/specs/2026-07-06-distill-quality-redesign.md
git commit -m "docs: 风格蒸馏重构验证通过" || echo "无文档改动，跳过"
```

---

## Self-Review

**1. Spec coverage（设计文档 → 任务映射）:**
- 两阶段架构 → Task 2 ✓
- Stage 1 四条硬性要求 + 多风格定位 + few-shot → Task 1（prompt 内容）✓
- Stage 2 四类可模仿样板 → Task 1 ✓
- 文章压缩策略（替代 800 字截断）→ Task 2（`_compress_articles`/`_sample_segments`）✓
- 整段注入（下游零改动）→ 无需任务，Gateway 已支持 ✓
- 移除 `style_profile_structured` → Task 5 ✓
- 进度走 status 枚举 → Task 3 ✓
- direction/outline/title 冗余清理 → Task 4 ✓
- 前端 DistillDialog 改展示整段指南 → Task 7 ✓
- 真实蒸馏验证 → Task 8 ✓

**2. Placeholder scan:** 无 TBD/TODO；每个代码步骤含完整代码。✓

**3. Type consistency:**
- `distill-extract` 场景变量 `num_articles`/`articles_content` ↔ Task 2 trigger_distill Stage 1 payload ✓
- `distill-synthesize` 场景变量 `features` ↔ Task 2 Stage 2 payload ✓
- status 枚举 `extracting`/`synthesizing` ↔ Task 3 端点 ↔ Task 7 前端 ✓
- `getDistillStatus` 返回 `stage`/`stage_name` ↔ Task 7 前端消费 ✓
- `trigger_distill(account_id, articles_content, num_articles)` 签名前后一致（API 调用处 `distill.py:33-37` 未改）✓

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-07-06-distill-quality-redesign.md`.
