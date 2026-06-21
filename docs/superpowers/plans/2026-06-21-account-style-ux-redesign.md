# Account Style UX Redesign — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace tabbed dialog with wizard + split-pane dialog + card action buttons, add real-time distill progress via polling, and fix missing word_count fields.

**Architecture:** 1 page component (`AccountsView`) + 6 focused child components. Backend uses Celery task with 7 per-dimension LLM calls, updating `style_profile_structured` + progress metadata in Account model. Frontend polls `GET /accounts/{id}/distill/status` every 2s for live progress.

**Tech Stack:** Vue 3 + Element Plus + TypeScript (frontend), FastAPI + Celery + SQLAlchemy (backend), SQLite

---

## Task 1: Backend — Account Model & Schema Fixes

**Files:**
- Modify: `app/models.py:51-67`
- Modify: `app/schemas.py:53-70`
- Create: (manual DB migration script)

### Step 1.1: Add word_count fields to Account model

Add `word_count` and `word_count_options` columns to the Account class in `app/models.py:51-67`.

Add after line 65 (`style_profile_status` line):

```python
class Account(Base):
    # ... existing columns ...
    style_profile_status = Column(String(20), default="none")  # idle/running/ready/failed
    word_count_options = Column(Text)  # JSON: ["800", "1500", "3000"]
    word_count = Column(Integer, nullable=True)  # default word count
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

### Step 1.2: Run DB migration

Run: Apply ALTER TABLE via SQLite:

```sql
ALTER TABLE accounts ADD COLUMN word_count_options TEXT;
ALTER TABLE accounts ADD COLUMN word_count INTEGER;
```

Run via Python migration script in `app/migrate_word_count.py`:

```python
"""Add word_count columns to accounts table"""
from app.database import engine, Base
from sqlalchemy import text

def migrate():
    with engine.connect() as conn:
        # Check if columns already exist
        result = conn.execute(text("PRAGMA table_info(accounts)"))
        columns = [row[1] for row in result.fetchall()]
        if "word_count_options" not in columns:
            conn.execute(text("ALTER TABLE accounts ADD COLUMN word_count_options TEXT"))
            print("Added word_count_options column")
        if "word_count" not in columns:
            conn.execute(text("ALTER TABLE accounts ADD COLUMN word_count INTEGER"))
            print("Added word_count column")
        conn.commit()

if __name__ == "__main__":
    migrate()
    print("Migration complete")
```

Run: `python -m app.migrate_word_count`

### Step 1.3: Update Pydantic schemas

Add `word_count_options` and `word_count` to `AccountUpdate` and `AccountResponse` in `app/schemas.py:53-84`.

```python
class AccountUpdate(BaseModel):
    platform: Optional[str] = None
    account_name: Optional[str] = None
    lora_path: Optional[str] = None
    sample_articles: Optional[str] = None
    word_count_options: Optional[str] = None  # JSON string
    word_count: Optional[int] = None

class AccountResponse(AccountBase):
    id: int
    style_profile: Optional[str] = None
    style_profile_updated_at: Optional[datetime] = None
    style_profile_structured: Optional[Any] = None
    style_profile_version: Optional[int] = None
    style_profile_status: Optional[str] = None
    word_count_options: Optional[str] = None
    word_count: Optional[int] = None
    created_at: datetime

    class Config: from_attributes = True

    @field_validator("style_profile_structured", mode="before")
    @classmethod
    def parse_structured(cls, v):
        # ... existing code unchanged ...
```

### Step 1.4: Commit

```bash
git add app/models.py app/schemas.py app/migrate_word_count.py
git commit -m "feat: add word_count fields to Account model and schemas"
```

---

## Task 2: Backend — Distill Status Endpoint

**Files:**
- Modify: `app/api/distill.py`

### Step 2.1: Add GET status route

Add to `app/api/distill.py` after the existing `POST /{account_id}/distill` route:

```python
import json
from ..models import Account


@router.get("/{account_id}/distill/status")
def get_distill_status(account_id: int, db: Session = Depends(get_db)):
    """查询蒸馏任务状态"""
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="账号不存在")

    status = account.style_profile_status or "none"

    if status == "none":
        return {"status": "idle"}

    if status == "running":
        # 从 style_profile_structured 中提取进度元数据
        progress = {"completed": 0, "total": 7, "current_dimension": ""}
        if account.style_profile_structured:
            try:
                raw = json.loads(account.style_profile_structured)
                if isinstance(raw, dict) and "_progress" in raw:
                    progress = raw["_progress"]
            except (json.JSONDecodeError, TypeError):
                pass
        return {"status": "running", "progress": progress}

    if status == "ready":
        return {
            "status": "completed",
            "style_profile_version": account.style_profile_version,
        }

    if status == "failed":
        return {"status": "failed", "error": account.style_profile or "蒸馏失败"}

    return {"status": "idle"}
```

### Step 2.2: Write backend test

Create `tests/test_distill_status.py`:

```python
"""Test distill status endpoint"""
from fastapi.testclient import TestClient
from app.main import app
from app.database import get_db, Base, engine
from app.models import Account, ReferenceArticle
import pytest


@pytest.fixture
def client():
    Base.metadata.create_all(bind=engine)
    yield TestClient(app)
    Base.metadata.drop_all(bind=engine)


def test_distill_status_idle(client):
    """未蒸馏的账号返回 idle"""
    # Create account
    from app.database import SessionLocal
    db = SessionLocal()
    account = Account(platform="test", account_name="test_acc")
    db.add(account)
    db.commit()
    acc_id = account.id
    db.close()

    resp = client.get(f"/accounts/{acc_id}/distill/status")
    assert resp.status_code == 200
    assert resp.json()["status"] == "idle"


def test_distill_status_running(client):
    """蒸馏中的账号返回 running + progress"""
    from app.database import SessionLocal
    db = SessionLocal()
    account = Account(
        platform="test",
        account_name="test_acc",
        style_profile_status="running",
        style_profile_structured='{"_progress": {"completed": 3, "total": 7, "current_dimension": "句式特征"}}'
    )
    db.add(account)
    db.commit()
    acc_id = account.id
    db.close()

    resp = client.get(f"/accounts/{acc_id}/distill/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "running"
    assert data["progress"]["completed"] == 3
    assert data["progress"]["current_dimension"] == "句式特征"


def test_distill_status_completed(client):
    """蒸馏完成的账号返回 completed"""
    from app.database import SessionLocal
    db = SessionLocal()
    account = Account(
        platform="test",
        account_name="test_acc",
        style_profile_status="ready",
        style_profile_version=2,
        style_profile_structured='{"thinking_pattern": "...", "structure_pattern": "..."}'
    )
    db.add(account)
    db.commit()
    acc_id = account.id
    db.close()

    resp = client.get(f"/accounts/{acc_id}/distill/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "completed"
    assert data["style_profile_version"] == 2


def test_distill_status_failed(client):
    """蒸馏失败的账号返回 failed + error"""
    from app.database import SessionLocal
    db = SessionLocal()
    account = Account(
        platform="test",
        account_name="test_acc",
        style_profile_status="failed",
        style_profile="LLM 返回格式异常"
    )
    db.add(account)
    db.commit()
    acc_id = account.id
    db.close()

    resp = client.get(f"/accounts/{acc_id}/distill/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "failed"
    assert "error" in data


def test_distill_status_404(client):
    """不存在的账号返回 404"""
    resp = client.get("/accounts/99999/distill/status")
    assert resp.status_code == 404
```

Run: `pytest tests/test_distill_status.py -v`
Expected: 5 tests pass

### Step 2.3: Commit

```bash
git add app/api/distill.py tests/test_distill_status.py
git commit -m "feat: add GET /accounts/{id}/distill/status endpoint"
```

---

## Task 3: Backend — Rewrite Distill Task (7 Per-Dimension Calls)

**Files:**
- Modify: `app/tasks.py:307-417`

### Step 3.1: Rewrite trigger_distill function

Replace the existing `trigger_distill` function (lines 307-417 in `app/tasks.py`):

```python
@celery_app.task(bind=True)
def trigger_distill(self, account_id: int, articles_content: list, num_articles: int):
    """异步蒸馏：逐维度调用 LLM，实时更新进度"""
    db = SessionLocal()
    try:
        # 截断文章
        max_per_article = 800
        truncated = []
        for a in articles_content:
            if len(a) > max_per_article:
                truncated.append(a[:max_per_article] + "\n\n[... 后续内容已截断 ...]")
            else:
                truncated.append(a)
        combined_articles = "\n\n---\n\n".join(truncated)

        # 标记为 running
        account = db.query(Account).filter(Account.id == account_id).first()
        if account:
            account.style_profile_status = "running"
            account.style_profile_structured = json.dumps({
                "_progress": {"completed": 0, "total": 7, "current_dimension": "准备中"}
            })
            db.commit()

        # 定义 7 个维度
        dimensions = [
            ("thinking_pattern", "思维模式", "分析作者的核心思维模式：是理性分析型、情感共鸣型、还是批判质疑型？描述其推理逻辑和论证方式。"),
            ("structure_pattern", "结构模式", "分析文章的结构特点：开篇方式、段落组织、过渡手法、结尾风格。"),
            ("sentence_pattern", "句式特征", "分析句式特点：长短句比例、修辞手法、句式多样性、节奏感。"),
            ("vocabulary_pattern", "词汇偏好", "分析词汇使用习惯：高频词汇、专业术语、口语化程度、用词偏好。"),
            ("evidence_type", "论据类型", "分析论据使用方式：数据引用、案例引用、个人经验、权威引用等。"),
            ("taboos", "写作禁忌", "识别写作中应避免的内容：敏感话题、表达方式禁忌、价值观红线。"),
            ("blank_leaving", "留白习惯", "分析留白手法：结尾方式、悬念设置、读者参与空间、余韵处理。"),
        ]

        llm_url = settings.llm_service_url.rstrip("/")
        structured = {}

        with httpx.Client(timeout=120.0) as client:
            for i, (dim_key, dim_label, dim_prompt) in enumerate(dimensions):
                try:
                    resp = client.post(f"{llm_url}/chat", json={
                        "scenario": "distill",
                        "account_id": account_id,
                        "variables": {
                            "num_articles": str(num_articles),
                            "articles_content": combined_articles,
                            "dimension": dim_label,
                            "dimension_prompt": dim_prompt,
                        },
                    })
                    resp.raise_for_status()
                    data = resp.json()
                    content = data.get("content", "").strip()

                    # 提取纯文本（去除可能的 markdown 标记）
                    if content:
                        structured[dim_key] = content

                except Exception as dim_err:
                    # 记录失败并终止
                    account = db.query(Account).filter(Account.id == account_id).first()
                    if account:
                        account.style_profile_status = "failed"
                        account.style_profile = f"维度 [{dim_label}] 蒸馏失败: {str(dim_err)}"
                        db.commit()
                    db.close()
                    return {"account_id": account_id, "status": "failed", "error": str(dim_err)}

                # 更新进度
                completed = i + 1
                structured["_progress"] = {
                    "completed": completed,
                    "total": 7,
                    "current_dimension": dim_label if completed < 7 else "完成"
                }

                account = db.query(Account).filter(Account.id == account_id).first()
                if account:
                    account.style_profile_structured = json.dumps(structured, ensure_ascii=False)
                    db.commit()

        # 7 个维度全部完成
        # 移除 _progress 元数据
        structured.pop("_progress", None)

        # 生成兼容旧版摘要文本
        dim_labels = {
            "thinking_pattern": "思维特征",
            "structure_pattern": "结构模式",
            "sentence_pattern": "句式特征",
            "vocabulary_pattern": "词汇偏好",
            "evidence_type": "论据类型",
            "taboos": "禁忌清单",
            "blank_leaving": "留白程度",
        }
        parts = []
        for key, label in dim_labels.items():
            if structured.get(key):
                parts.append(f"【{label}】\n{structured[key]}")
        summary_text = "\n\n".join(parts)

        account = db.query(Account).filter(Account.id == account_id).first()
        if account:
            account.style_profile = summary_text
            account.style_profile_structured = json.dumps(structured, ensure_ascii=False)
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

### Step 3.2: Write backend test for distill task

Create `tests/test_distill_task.py`:

```python
"""Test distill task progress updates"""
from unittest.mock import patch, MagicMock
from app.tasks import trigger_distill
from app.models import Account
from app.database import SessionLocal, Base, engine
import json


def test_distill_task_updates_progress():
    """蒸馏任务应逐维度更新进度"""
    db = SessionLocal()
    # Create test account
    account = Account(platform="test", account_name="test_progress")
    db.add(account)
    db.commit()
    acc_id = account.id
    db.close()

    # Mock httpx to return per-dimension responses
    mock_dim_responses = [
        {"content": "理性分析型，擅长逻辑推理"},
        {"content": "开门见山，三段式结构"},
        {"content": "长短句交替，善用排比"},
        {"content": "偏好理性词汇，较少口语"},
        {"content": "大量引用数据和研究"},
        {"content": "避免人身攻击，保持客观"},
        {"content": "结尾留白，引发思考"},
    ]

    with patch("app.tasks.httpx.Client") as mock_client:
        # Setup mock to return each dimension response in sequence
        mock_instance = MagicMock()
        mock_client.return_value.__enter__.return_value = mock_instance

        mock_responses = []
        for content in mock_dim_responses:
            mock_resp = MagicMock()
            mock_resp.raise_for_status.return_value = None
            mock_resp.json.return_value = {"content": content}
            mock_responses.append(mock_resp)

        mock_instance.post.side_effect = mock_responses

        # Run task
        result = trigger_distill(acc_id, ["## Test\n\nContent here"], 1)

        assert result["status"] == "ready"
        # Verify post was called 7 times (once per dimension)
        assert mock_instance.post.call_count == 7

    # Verify final state in DB
    db = SessionLocal()
    account = db.query(Account).filter(Account.id == acc_id).first()
    assert account.style_profile_status == "ready"
    assert account.style_profile_version >= 1

    structured = json.loads(account.style_profile_structured)
    assert structured["thinking_pattern"] == "理性分析型，擅长逻辑推理"
    assert structured["structure_pattern"] == "开门见山，三段式结构"
    assert "_progress" not in structured  # Cleaned up after completion
    db.delete(account)
    db.commit()
    db.close()


def test_distill_task_failure_marks_failed():
    """蒸馏失败应标记为 failed"""
    db = SessionLocal()
    account = Account(platform="test", account_name="test_fail")
    db.add(account)
    db.commit()
    acc_id = account.id
    db.close()

    with patch("app.tasks.httpx.Client") as mock_client:
        mock_instance = MagicMock()
        mock_client.return_value.__enter__.return_value = mock_instance

        # First call succeeds, second fails
        mock_resp_ok = MagicMock()
        mock_resp_ok.raise_for_status.return_value = None
        mock_resp_ok.json.return_value = {"content": "Good response"}

        mock_instance.post.side_effect = [mock_resp_ok, Exception("LLM timeout")]

        try:
            trigger_distill(acc_id, ["## Test\n\nContent"], 1)
        except Exception:
            pass

    db = SessionLocal()
    account = db.query(Account).filter(Account.id == acc_id).first()
    assert account.style_profile_status == "failed"
    assert "LLM timeout" in (account.style_profile or "")
    db.delete(account)
    db.commit()
    db.close()
```

Run: `pytest tests/test_distill_task.py -v`
Expected: 2 tests pass

### Step 3.3: Commit

```bash
git add app/tasks.py tests/test_distill_task.py
git commit -m "feat: rewrite distill task as 7 per-dimension LLM calls with progress"
```

---

## Task 4: Backend — Test word_count CRUD

**Files:**
- Create: `tests/test_account_word_count.py`

### Step 4.1: Write test

```python
"""Test word_count fields CRUD"""
from fastapi.testclient import TestClient
from app.main import app
from app.database import Base, engine, SessionLocal
from app.models import Account
import pytest


@pytest.fixture
def client():
    Base.metadata.create_all(bind=engine)
    yield TestClient(app)
    Base.metadata.drop_all(bind=engine)


def test_create_account_with_word_count(client):
    """创建账号时可设置字数配置"""
    resp = client.post("/accounts", json={
        "platform": "test",
        "account_name": "test_wc",
        "word_count_options": '["800","1500","3000"]',
        "word_count": 1500,
    })
    assert resp.status_code == 200
    data = resp.json()
    # 字数字段应在返回中
    assert data.get("word_count") == 1500


def test_update_word_count(client):
    """更新账号字数配置"""
    db = SessionLocal()
    account = Account(platform="test", account_name="wc_test2")
    db.add(account)
    db.commit()
    acc_id = account.id
    db.close()

    resp = client.put(f"/accounts/{acc_id}", json={
        "word_count_options": '["500","1000"]',
        "word_count": 500,
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["word_count"] == 500
    assert data["word_count_options"] == '["500","1000"]'
```

Run: `pytest tests/test_account_word_count.py -v`
Expected: 2 tests pass

### Step 4.2: Commit

```bash
git add tests/test_account_word_count.py
git commit -m "test: add word_count CRUD tests"
```

---

## Task 5: Frontend — Update API Types & Client

**Files:**
- Modify: `src/api/types.ts`
- Modify: `src/api/client.ts` or `src/api/modules/accounts.ts`

### Step 5.1: Update Account TypeScript interface

Add fields to the `Account` interface in `src/api/types.ts`:

```typescript
export interface Account {
  id: number;
  platform: string;
  account_name: string;
  lora_path?: string;
  sample_articles?: string;
  style_profile?: string;
  style_profile_updated_at?: string;
  style_profile_structured?: StyleProfile | null;
  style_profile_version?: number;
  style_profile_status?: string;  // "idle" | "running" | "ready" | "failed"
  word_count_options?: string;    // JSON array string, e.g. '["800","1500"]'
  word_count?: number | null;
  created_at: string;
}
```

### Step 5.2: Add getDistillStatus API method

Add to `src/api/client.ts` in the `api` object (after `triggerDistill`):

```typescript
// In the api object:
async getDistillStatus(accountId: number) {
  const { data } = await axios.get(`/accounts/${accountId}/distill/status`);
  return data as {
    status: "idle" | "running" | "completed" | "failed";
    progress?: { completed: number; total: number; current_dimension: string };
    style_profile_version?: number;
    error?: string;
  };
},
```

### Step 5.3: Update account CRUD to include word_count

Update `updateAccount` in `src/api/modules/accounts.ts` to include word_count fields in the payload type:

```typescript
export interface AccountUpdatePayload {
  platform?: string;
  account_name?: string;
  lora_path?: string;
  sample_articles?: string;
  word_count_options?: string;
  word_count?: number | null;
}
```

### Step 5.4: Commit

```bash
git add src/api/types.ts src/api/client.ts src/api/modules/accounts.ts
git commit -m "feat: add distill status API, word_count fields, update types"
```

---

## Task 6: Frontend — AccountCard Component

**Files:**
- Create: `src/components/accounts/AccountCard.vue`

### Step 6.1: Create AccountCard component

Create `src/components/accounts/AccountCard.vue`:

```vue
<template>
  <div class="account-card">
    <div class="card-top">
      <div class="card-avatar">{{ account.account_name.charAt(0) }}</div>
      <div class="card-meta">
        <span class="card-name">{{ account.account_name }}</span>
        <span class="card-platform">{{ account.platform }}</span>
      </div>
      <span class="card-badge" :class="badgeClass">
        <i v-if="account.style_profile_status === 'running'" class="el-icon-loading" style="margin-right:4px"></i>
        {{ badgeText }}
      </span>
    </div>
    <div class="card-bottom">
      <span class="card-date">{{ dateText }}</span>
      <el-dropdown trigger="click" @command="handleMenuCommand">
        <el-button size="small" text type="info" @click.stop>
          <i class="el-icon-more"></i>
        </el-button>
        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item command="delete">删除账号</el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
    </div>
    <!-- Action buttons -->
    <div class="card-actions">
      <el-button size="small" @click.stop="$emit('edit-basic')">✏️ 基本信息</el-button>
      <el-button size="small" type="primary" @click.stop="$emit('distill')">🎨 风格蒸馏</el-button>
      <el-button size="small" @click.stop="$emit('word-count')">📝 字数配置</el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { Account } from "@/api/types";
import { formatDateTime } from "@/utils/format";

const props = defineProps<{
  account: Account;
}>();

defineEmits<{
  (e: "edit-basic"): void;
  (e: "distill"): void;
  (e: "word-count"): void;
  (e: "delete"): void;
}>();

const statusMap: Record<string, { text: string; class: string }> = {
  ready: { text: "画像就绪", class: "badge-ready" },
  running: { text: "蒸馏中...", class: "badge-running" },
  failed: { text: "蒸馏失败", class: "badge-failed" },
};

const badgeInfo = computed(() => {
  const status = props.account.style_profile_status || "none";
  if (status === "ready") {
    const v = props.account.style_profile_version || 1;
    return { text: `画像就绪 v${v}`, class: "badge-ready" };
  }
  return statusMap[status] || { text: "待蒸馏", class: "badge-idle" };
});

const badgeText = computed(() => badgeInfo.value.text);
const badgeClass = computed(() => badgeInfo.value.class);

const dateText = computed(() => {
  if (props.account.style_profile_updated_at) {
    return `更新于 ${formatDateTime(props.account.style_profile_updated_at, "date")}`;
  }
  return "尚未蒸馏";
});

function handleMenuCommand(cmd: string) {
  if (cmd === "delete") {
    // emit delete event for parent to handle confirmation
    // (actual logic: parent shows confirm dialog)
  }
}
</script>

<style scoped>
/* Use existing .account-card styles from AccountsView.vue */
/* .account-card, .card-top, .card-avatar, .card-meta, .card-name, .card-platform */
/* .card-badge, .card-bottom, .card-date, .card-actions */

.account-card {
  background: var(--ink-mid);
  border: 1px solid var(--ink-border);
  border-radius: var(--radius-lg);
  padding: 20px;
}

.card-top {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 14px;
}

.card-avatar {
  width: 42px; height: 42px;
  border-radius: var(--radius-md);
  background: var(--amber-glow);
  color: var(--amber-light);
  display: flex; align-items: center; justify-content: center;
  font-family: var(--font-serif);
  font-size: 20px; font-weight: 700;
  flex-shrink: 0;
}

.card-meta { flex: 1; display: flex; flex-direction: column; gap: 2px; }

.card-name { font-size: 15px; font-weight: 600; color: var(--text-on-dark); }

.card-platform { font-size: 12px; color: var(--text-dim); }

.card-badge { font-size: 11px; padding: 3px 10px; border-radius: 20px; font-weight: 500; }

.badge-ready { background: rgba(91,140,90,0.12); color: var(--green-muted); }
.badge-idle { background: rgba(255,171,64,0.12); color: var(--amber-light); }
.badge-running { background: rgba(64,158,255,0.12); color: #409eff; }
.badge-failed { background: rgba(245,108,108,0.12); color: #f56c6c; }

.card-bottom {
  display: flex; justify-content: space-between; align-items: center;
}

.card-date { font-size: 12px; color: var(--text-dim); }

.card-actions {
  display: flex; gap: 6px; margin-top: 14px; padding-top: 14px;
  border-top: 1px solid var(--ink-border);
}
</style>
```

### Step 6.2: Commit

```bash
git add src/components/accounts/AccountCard.vue
git commit -m "feat: add AccountCard component with status badge and action buttons"
```

---

## Task 7: Frontend — ReferenceArticleForm Component

**Files:**
- Create: `src/components/accounts/ReferenceArticleForm.vue`

### Step 7.1: Create reusable article form

```vue
<template>
  <el-form :model="form" label-width="80px">
    <el-form-item label="标题" required>
      <el-input v-model="form.title" placeholder="文章标题" />
    </el-form-item>
    <el-form-item label="正文" required>
      <el-input v-model="form.content" type="textarea" :rows="6" placeholder="粘贴文章正文" />
    </el-form-item>
    <el-form-item label="来源链接">
      <el-input v-model="form.source_url" placeholder="https://...（可选）" />
    </el-form-item>
    <el-form-item label="代表篇">
      <el-switch v-model="form.is_benchmark" />
      <span style="margin-left:8px;font-size:12px;color:var(--text-dim)">标记为最具代表性的文章</span>
    </el-form-item>
  </el-form>
</template>

<script setup lang="ts">
import { reactive, watch } from "vue";

const props = defineProps<{
  article?: { title: string; content: string; source_url: string; is_benchmark: boolean };
}>();

const form = reactive({
  title: "",
  content: "",
  source_url: "",
  is_benchmark: false,
});

watch(() => props.article, (a) => {
  if (a) {
    form.title = a.title;
    form.content = a.content;
    form.source_url = a.source_url;
    form.is_benchmark = a.is_benchmark;
  }
}, { immediate: true });

function getFormData() {
  return { ...form };
}

function reset() {
  form.title = "";
  form.content = "";
  form.source_url = "";
  form.is_benchmark = false;
}

defineExpose({ getFormData, reset });
</script>
```

### Step 7.2: Commit

```bash
git add src/components/accounts/ReferenceArticleForm.vue
git commit -m "feat: add reusable ReferenceArticleForm component"
```

---

## Task 8: Frontend — BasicInfoDialog & WordCountDialog

**Files:**
- Create: `src/components/accounts/BasicInfoDialog.vue`
- Create: `src/components/accounts/WordCountDialog.vue`

### Step 8.1: Create BasicInfoDialog

```vue
<template>
  <el-dialog v-model="visible" title="编辑基本信息" width="480px" @close="$emit('closed')">
    <el-form :model="form" label-width="80px">
      <el-form-item label="平台">
        <el-input v-model="form.platform" placeholder="公众号 / 小红书 / 知乎" />
      </el-form-item>
      <el-form-item label="账号名">
        <el-input v-model="form.account_name" placeholder="账号名称" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="visible = false">取消</el-button>
      <el-button type="primary" :loading="saving" @click="handleSave">保存</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, reactive, watch } from "vue";
import { ElMessage } from "element-plus";
import { accountsApi } from "@/api/modules/accounts";
import { Account } from "@/api/types";

const props = defineProps<{ modelValue: boolean; account: Account | null }>();
const emit = defineEmits<{ (e: "update:modelValue", v: boolean): void; (e: "saved"): void }>();

const visible = ref(props.modelValue);
watch(() => props.modelValue, (v) => { visible.value = v; });
watch(visible, (v) => { emit("update:modelValue", v); });

const saving = ref(false);
const form = reactive({ platform: "", account_name: "" });

watch(() => props.account, (acc) => {
  if (acc) {
    form.platform = acc.platform;
    form.account_name = acc.account_name;
  }
}, { immediate: true });

async function handleSave() {
  if (!props.account?.id) return;
  saving.value = true;
  try {
    await accountsApi.update(props.account.id, { ...form });
    ElMessage.success("已更新");
    visible.value = false;
    emit("saved");
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || "保存失败");
  } finally {
    saving.value = false;
  }
}
</script>
```

### Step 8.2: Create WordCountDialog

```vue
<template>
  <el-dialog v-model="visible" title="字数配置" width="520px" @close="$emit('closed')">
    <el-form label-width="100px">
      <el-form-item label="字数选项">
        <div v-for="(opt, i) in options" :key="i" style="display:flex;gap:8px;margin-bottom:6px">
          <el-input v-model="options[i]" placeholder="例如：800" size="small" />
          <el-button size="small" text type="danger" @click="options.splice(i, 1)">×</el-button>
        </div>
        <el-button size="small" @click="options.push('')">＋ 添加选项</el-button>
      </el-form-item>
      <el-form-item label="默认字数">
        <el-select v-model="defaultWordCount" placeholder="选择默认字数" style="width:200px">
          <el-option v-for="opt in options.filter(Boolean)" :key="opt" :label="opt" :value="Number(opt)" />
        </el-select>
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="visible = false">取消</el-button>
      <el-button type="primary" :loading="saving" @click="handleSave">保存</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, watch } from "vue";
import { ElMessage } from "element-plus";
import { accountsApi } from "@/api/modules/accounts";
import { Account } from "@/api/types";

const props = defineProps<{ modelValue: boolean; account: Account | null }>();
const emit = defineEmits<{ (e: "update:modelValue", v: boolean): void; (e: "saved"): void }>();

const visible = ref(props.modelValue);
watch(() => props.modelValue, (v) => { visible.value = v; });
watch(visible, (v) => { emit("update:modelValue", v); });

const saving = ref(false);
const options = ref<string[]>([]);
const defaultWordCount = ref<number | null>(null);

watch(() => props.account, (acc) => {
  if (!acc) return;
  try {
    options.value = acc.word_count_options ? JSON.parse(acc.word_count_options) : [];
  } catch { options.value = []; }
  defaultWordCount.value = acc.word_count || null;
}, { immediate: true });

async function handleSave() {
  if (!props.account?.id) return;
  saving.value = true;
  try {
    const valid = options.value.filter(Boolean);
    await accountsApi.update(props.account.id, {
      word_count_options: valid.length ? JSON.stringify(valid) : null,
      word_count: defaultWordCount.value || null,
    } as any);
    ElMessage.success("字数配置已保存");
    visible.value = false;
    emit("saved");
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || "保存失败");
  } finally {
    saving.value = false;
  }
}
</script>
```

### Step 8.3: Commit

```bash
git add src/components/accounts/BasicInfoDialog.vue src/components/accounts/WordCountDialog.vue
git commit -m "feat: add BasicInfoDialog and WordCountDialog components"
```

---

## Task 9: Frontend — AccountWizard Component

**Files:**
- Create: `src/components/accounts/AccountWizard.vue`

### Step 9.1: Create three-step wizard

```vue
<template>
  <el-dialog v-model="visible" title="新增账号" width="720px" :close-on-click-modal="false" @close="handleClose">
    <!-- Step indicator -->
    <el-steps :active="step" align-center style="margin-bottom: 32px;">
      <el-step title="基本信息" />
      <el-step title="参考文章" />
      <el-step title="确认并蒸馏" />
    </el-steps>

    <!-- Step 1: Basic Info -->
    <div v-if="step === 0">
      <el-form ref="formRef" :model="basicForm" :rules="rules" label-width="80px">
        <el-form-item label="平台" prop="platform">
          <el-input v-model="basicForm.platform" placeholder="公众号 / 小红书 / B站 / 知乎" />
        </el-form-item>
        <el-form-item label="账号名" prop="account_name">
          <el-input v-model="basicForm.account_name" placeholder="账号名称" />
        </el-form-item>
      </el-form>
      <div style="text-align:right;margin-top:24px;">
        <el-button @click="visible = false">取消</el-button>
        <el-button type="primary" @click="nextStep">下一步 →</el-button>
      </div>
    </div>

    <!-- Step 2: Reference Articles -->
    <div v-if="step === 1">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;">
        <span style="font-weight:600;">已添加 {{ wizardArticles.length }} 篇文章</span>
        <el-button size="small" @click="openArticleForm">＋ 添加文章</el-button>
      </div>
      <div v-if="wizardArticles.length" class="article-list">
        <div v-for="(a, i) in wizardArticles" :key="i" class="article-row">
          <div class="article-info">
            <span class="article-title">{{ a.title }}</span>
            <span v-if="a.is_benchmark" class="article-benchmark">代表篇</span>
          </div>
          <div class="article-actions">
            <el-button size="small" text @click="openArticleForm(i)">编辑</el-button>
            <el-button size="small" text type="danger" @click="wizardArticles.splice(i, 1)">删除</el-button>
          </div>
        </div>
      </div>
      <div v-else class="empty-hint">请添加至少一篇参考文章。建议 3~5 篇最具代表性的文章。</div>
      <div style="text-align:right;margin-top:24px;display:flex;justify-content:space-between;">
        <el-button @click="step = 0">← 上一步</el-button>
        <el-button type="primary" :disabled="!wizardArticles.length" @click="nextStep">
          下一步：确认并蒸馏 →
        </el-button>
      </div>
    </div>

    <!-- Step 3: Confirm & Distill -->
    <div v-if="step === 2">
      <div class="confirm-card">
        <h4 style="margin-bottom:12px;">确认信息</h4>
        <table style="width:100%;font-size:14px;">
          <tr><td style="padding:4px 0;color:var(--text-dim);">平台</td><td>{{ basicForm.platform }}</td></tr>
          <tr><td style="padding:4px 0;color:var(--text-dim);">账号</td><td>{{ basicForm.account_name }}</td></tr>
          <tr><td style="padding:4px 0;color:var(--text-dim);">参考文章</td><td>{{ wizardArticles.length }} 篇</td></tr>
        </table>
      </div>
      <p style="margin:16px 0;font-size:13px;color:var(--text-dim);">
        点击"开始蒸馏"后，系统将分析参考文章，提取 7 个维度的写作风格特征。预计耗时 30~60 秒。
      </p>
      <div style="text-align:right;display:flex;justify-content:space-between;">
        <el-button @click="step = 1">← 上一步</el-button>
        <el-button type="primary" :loading="submitting" size="large" @click="handleSubmit">
          🔥 开始蒸馏
        </el-button>
      </div>
    </div>

    <!-- Article form sub-dialog -->
    <el-dialog v-model="articleFormVisible" :title="editingIdx >= 0 ? '编辑文章' : '添加文章'" width="720px" append-to-body>
      <ReferenceArticleForm ref="articleFormRef" :article="editingArticle" />
      <template #footer>
        <el-button @click="articleFormVisible = false">取消</el-button>
        <el-button type="primary" @click="saveArticleForm">
          {{ editingIdx >= 0 ? '保存' : '添加' }}
        </el-button>
      </template>
    </el-dialog>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, reactive, computed } from "vue";
import { ElMessage } from "element-plus";
import { api } from "@/api/client";
import { accountsApi } from "@/api/modules/accounts";
import ReferenceArticleForm from "./ReferenceArticleForm.vue";

const emit = defineEmits<{ (e: "created"): void }>();

const visible = ref(false);
const step = ref(0);
const submitting = ref(false);

const basicForm = reactive({ platform: "", account_name: "" });

const rules = {
  platform: [{ required: true, message: "请选择平台", trigger: "blur" }],
  account_name: [{ required: true, message: "请输入账号名称", trigger: "blur" }],
};

const wizardArticles = ref<Array<{ title: string; content: string; source_url: string; is_benchmark: boolean }>>([]);

const articleFormVisible = ref(false);
const editingIdx = ref(-1);
const articleFormRef = ref<InstanceType<typeof ReferenceArticleForm>>();

const editingArticle = computed(() => {
  if (editingIdx.value >= 0 && wizardArticles.value[editingIdx.value]) {
    return wizardArticles.value[editingIdx.value];
  }
  return undefined;
});

function show() {
  basicForm.platform = "";
  basicForm.account_name = "";
  wizardArticles.value = [];
  step.value = 0;
  visible.value = true;
}

function nextStep() {
  if (step.value < 2) step.value++;
}

function openArticleForm(idx?: number) {
  editingIdx.value = idx ?? -1;
  articleFormVisible.value = true;
}

function saveArticleForm() {
  const data = articleFormRef.value?.getFormData();
  if (!data || !data.title || !data.content) {
    ElMessage.warning("标题和正文不能为空");
    return;
  }
  if (editingIdx.value >= 0) {
    wizardArticles.value[editingIdx.value] = { ...data };
  } else {
    wizardArticles.value.push({ ...data });
  }
  articleFormVisible.value = false;
  articleFormRef.value?.reset();
}

async function handleSubmit() {
  submitting.value = true;
  try {
    // Step 1: Create account
    const { data: account } = await accountsApi.create({
      platform: basicForm.platform,
      account_name: basicForm.account_name,
    });
    const accountId = account.id;

    // Step 2: Create reference articles
    for (const a of wizardArticles.value) {
      await api.createReferenceArticle(accountId, {
        account_id: accountId,
        title: a.title,
        content: a.content,
        source_url: a.source_url || undefined,
        is_benchmark: a.is_benchmark,
      });
    }

    // Step 3: Trigger distill
    await api.triggerDistill(accountId);
    ElMessage.success("账号创建完成，蒸馏任务已开始");
    visible.value = false;
    emit("created");
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || "创建失败");
  } finally {
    submitting.value = false;
  }
}

function handleClose() {
  basicForm.platform = "";
  basicForm.account_name = "";
  wizardArticles.value = [];
  step.value = 0;
}

defineExpose({ show });
</script>

<style scoped>
.confirm-card {
  background: var(--ink-surface);
  padding: 16px; border-radius: 8px;
}
.article-list { display: flex; flex-direction: column; gap: 6px; }
.article-row {
  display: flex; align-items: center; justify-content: space-between;
  padding: 10px 14px; background: var(--ink-surface); border-radius: var(--radius-md);
}
.article-info { display: flex; align-items: center; gap: 8px; }
.article-title { font-size: 14px; color: var(--text-on-dark); font-weight: 500; }
.article-benchmark {
  font-size: 10px; padding: 2px 8px; border-radius: 10px;
  background: var(--amber-glow); color: var(--amber-light); font-weight: 600;
}
.empty-hint { text-align: center; padding: 32px; color: var(--text-dim); font-size: 14px; }
</style>
```

### Step 9.2: Commit

```bash
git add src/components/accounts/AccountWizard.vue
git commit -m "feat: add AccountWizard 3-step component"
```

---

## Task 10: Frontend — DistillDialog Component

**Files:**
- Create: `src/components/accounts/DistillDialog.vue`

### Step 10.1: Create split-pane distill dialog with progress

```vue
<template>
  <el-dialog
    v-model="visible"
    :title="`风格蒸馏 · ${account?.account_name || ''}`"
    width="960px"
    :close-on-click-modal="false"
    @close="stopPolling"
  >
    <div class="distill-layout">
      <!-- Left: Reference Articles -->
      <div class="distill-left">
        <div class="distill-left-header">
          <h4>📄 参考文章</h4>
          <el-button v-if="!isRunning" size="small" @click="openArticleForm()">＋ 添加</el-button>
        </div>
        <div v-if="articles.length" class="distill-article-list" :class="{ readonly: isRunning }">
          <div v-for="a in articles" :key="a.id" class="distill-article-item">
            <div>
              <div class="distill-article-title">{{ a.title }}</div>
              <div class="distill-article-meta">
                {{ a.content ? a.content.length : 0 }} 字
                <span v-if="a.is_benchmark" class="article-benchmark">代表篇</span>
              </div>
            </div>
            <div v-if="!isRunning" class="distill-article-actions">
              <el-button size="small" text @click="openArticleForm(a)">编辑</el-button>
              <el-button size="small" text type="danger" @click="deleteArticle(a)">删除</el-button>
            </div>
          </div>
        </div>
        <div v-else class="empty-hint">暂无参考文章，请先添加</div>
      </div>

      <!-- Right: Style Profile + Progress -->
      <div class="distill-right">
        <div class="distill-right-header">
          <h4>🎨 风格画像</h4>
          <span v-if="status === 'completed'" class="status-tag ready">画像就绪 v{{ account?.style_profile_version }}</span>
          <span v-else-if="status === 'running'" class="status-tag running">蒸馏中...</span>
          <span v-else-if="status === 'failed'" class="status-tag failed">失败</span>
        </div>

        <!-- Idle / Empty -->
        <div v-if="status === 'idle'" class="distill-center">
          <p v-if="!articles.length" class="empty-hint">请先在左侧添加参考文章</p>
          <div v-else>
            <p class="empty-hint" v-if="!account?.style_profile_structured">点击下方按钮开始蒸馏</p>
            <!-- Show existing profile if available -->
            <div v-else class="profile-dimensions-grid">
              <div v-for="dim in styleDimensions" :key="dim.key" class="dimension-mini-card done">
                <span>{{ dim.icon }} {{ dim.label }}</span>
                <span class="check">✓</span>
              </div>
            </div>
          </div>
        </div>

        <!-- Running progress -->
        <div v-else-if="status === 'running'" class="distill-center">
          <div style="text-align:center;">
            <div class="spinner">⏳</div>
            <h4 style="margin:12px 0;">正在蒸馏风格...</h4>
            <div class="progress-bar">
              <div class="progress-fill" :style="{ width: progressPercent + '%' }"></div>
            </div>
            <p class="progress-text">已完成 {{ progress.completed }}/{{ progress.total }} 维度</p>
            <p class="progress-dim">正在分析：{{ progress.current_dimension }}</p>
            <p class="progress-eta">预计还需 {{ etaSeconds }} 秒</p>

            <!-- Per-dimension status -->
            <div class="dimension-status-grid">
              <div
                v-for="dim in dimensionStatusList"
                :key="dim.key"
                class="dim-status-item"
                :class="dim.state"
              >
                <span>{{ dim.icon }} {{ dim.label }}</span>
                <span v-if="dim.state === 'done'">✓</span>
                <span v-else-if="dim.state === 'active'" class="active-dot">●</span>
                <span v-else>○</span>
              </div>
            </div>
          </div>
        </div>

        <!-- Completed -->
        <div v-else-if="status === 'completed'" class="distill-center">
          <div class="profile-dimensions-grid">
            <div v-for="dim in styleDimensions" :key="dim.key" class="dimension-mini-card done">
              <span>{{ dim.icon }} {{ dim.label }}</span>
              <span class="check">✓</span>
            </div>
          </div>
        </div>

        <!-- Failed -->
        <div v-else-if="status === 'failed'" class="distill-center">
          <div style="text-align:center;">
            <div style="font-size:32px;">❌</div>
            <h4 style="color:#cf1322;margin:8px 0;">蒸馏失败</h4>
            <p style="font-size:13px;color:var(--text-dim);margin-bottom:8px;">{{ errorMessage }}</p>
            <el-button size="small" text @click="showDetail = !showDetail">
              {{ showDetail ? '收起' : '查看详情' }}
            </el-button>
            <pre v-if="showDetail" class="error-detail">{{ errorMessage }}</pre>
          </div>
        </div>

        <!-- Timeout -->
        <div v-else-if="status === 'timeout'" class="distill-center">
          <div style="text-align:center;">
            <div style="font-size:32px;">⏰</div>
            <h4 style="margin:8px 0;">蒸馏超时</h4>
            <p style="font-size:13px;color:var(--text-dim);">5 分钟内未完成，请稍后重试</p>
          </div>
        </div>

        <!-- Action button -->
        <div class="distill-action-bar">
          <el-button
            v-if="status !== 'running'"
            type="primary"
            :disabled="!articles.length"
            :loading="distillLoading"
            @click="triggerDistill"
          >
            {{ account?.style_profile_structured ? '🔄 重新蒸馏' : '🔥 开始蒸馏' }}
          </el-button>
          <el-button
            v-if="status === 'failed' || status === 'timeout'"
            type="primary"
            @click="retryDistill"
          >
            🔄 重试蒸馏
          </el-button>
        </div>
      </div>
    </div>

    <!-- Article sub-dialog -->
    <el-dialog v-model="articleFormVisible" :title="editingArticleId ? '编辑文章' : '添加文章'" width="720px" append-to-body>
      <ReferenceArticleForm ref="articleFormRef" :article="editingArticleData" />
      <template #footer>
        <el-button @click="articleFormVisible = false">取消</el-button>
        <el-button type="primary" :loading="savingArticle" @click="saveArticle">保存</el-button>
      </template>
    </el-dialog>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, computed, watch, onUnmounted } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { api, Account, ReferenceArticle } from "@/api/client";
import ReferenceArticleForm from "./ReferenceArticleForm.vue";

const props = defineProps<{ modelValue: boolean; account: Account | null }>();
const emit = defineEmits<{
  (e: "update:modelValue", v: boolean): void;
  (e: "profile-updated", account: Account): void;
}>();

const styleDimensions = [
  { key: "thinking_pattern", label: "思维特征", icon: "🧠" },
  { key: "structure_pattern", label: "结构模式", icon: "🏗️" },
  { key: "sentence_pattern", label: "句式特征", icon: "✍️" },
  { key: "vocabulary_pattern", label: "词汇偏好", icon: "📝" },
  { key: "evidence_type", label: "论据类型", icon: "📊" },
  { key: "taboos", label: "禁忌清单", icon: "🚫" },
  { key: "blank_leaving", label: "留白程度", icon: "💭" },
];

const visible = ref(props.modelValue);
watch(() => props.modelValue, (v) => { visible.value = v; if (v) onOpen(); });
watch(visible, (v) => { emit("update:modelValue", v); if (!v) stopPolling(); });

const articles = ref<ReferenceArticle[]>([]);
const status = ref<"idle" | "running" | "completed" | "failed" | "timeout">("idle");
const progress = ref({ completed: 0, total: 7, current_dimension: "" });
const errorMessage = ref("");
const distillLoading = ref(false);
const showDetail = ref(false);

let pollTimer: ReturnType<typeof setInterval> | null = null;
let startTime = 0;

const isRunning = computed(() => status.value === "running");
const progressPercent = computed(() => Math.round((progress.value.completed / progress.value.total) * 100));
const etaSeconds = computed(() => {
  if (progress.value.completed === 0) return 60;
  const elapsed = (Date.now() - startTime) / 1000;
  const rate = elapsed / progress.value.completed;
  return Math.max(0, Math.round(rate * (progress.value.total - progress.value.completed)));
});

const dimensionStatusList = computed(() => {
  return styleDimensions.map((dim, i) => ({
    ...dim,
    state: i < progress.value.completed ? "done" : i === progress.value.completed ? "active" : "pending",
  }));
});

// Article sub-form
const articleFormVisible = ref(false);
const editingArticleId = ref<number | null>(null);
const savingArticle = ref(false);
const articleFormRef = ref<InstanceType<typeof ReferenceArticleForm>>();
const editingArticleData = computed(() => {
  if (editingArticleId.value) {
    const a = articles.value.find(x => x.id === editingArticleId.value);
    if (a) return { title: a.title, content: a.content, source_url: a.source_url || "", is_benchmark: !!a.is_benchmark };
  }
  return undefined;
});

async function loadArticles() {
  if (!props.account?.id) return;
  try {
    const { data } = await api.getReferenceArticles(props.account.id);
    articles.value = data;
  } catch { articles.value = []; }
}

async function onOpen() {
  await loadArticles();
  await checkStatus();
  // If running, start polling
  if (status.value === "running") {
    startPolling();
  }
}

async function checkStatus() {
  if (!props.account?.id) return;
  try {
    const data = await api.getDistillStatus(props.account.id);
    if (data.status === "running") {
      status.value = "running";
      if (data.progress) progress.value = data.progress;
      startTime = Date.now();
    } else if (data.status === "completed") {
      status.value = "completed";
    } else if (data.status === "failed") {
      status.value = "failed";
      errorMessage.value = data.error || "未知错误";
    } else {
      status.value = "idle";
    }
  } catch {
    status.value = "idle";
  }
}

function startPolling() {
  stopPolling();
  startTime = Date.now();
  pollTimer = setInterval(async () => {
    await checkStatus();
    // Timeout check
    if (status.value === "running" && (Date.now() - startTime) > 300_000) {
      status.value = "timeout";
      stopPolling();
    }
    if (status.value !== "running") {
      stopPolling();
      if (status.value === "completed") {
        // Refresh account data
        emit("profile-updated", props.account!);
      }
    }
  }, 2000);
}

function stopPolling() {
  if (pollTimer) { clearInterval(pollTimer); pollTimer = null; }
}

async function triggerDistill() {
  if (!props.account?.id || !articles.value.length) return;
  distillLoading.value = true;
  try {
    await api.triggerDistill(props.account.id);
    ElMessage.success("蒸馏任务已开始");
    status.value = "running";
    progress.value = { completed: 0, total: 7, current_dimension: "准备中" };
    startPolling();
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || "蒸馏失败");
  } finally {
    distillLoading.value = false;
  }
}

function retryDistill() {
  errorMessage.value = "";
  showDetail.value = false;
  status.value = "idle";
  triggerDistill();
}

// Article CRUD in dialog
function openArticleForm(article?: ReferenceArticle) {
  editingArticleId.value = article?.id ?? null;
  articleFormVisible.value = true;
}

async function saveArticle() {
  if (!props.account?.id) return;
  const data = articleFormRef.value?.getFormData();
  if (!data || !data.title || !data.content) {
    ElMessage.warning("标题和正文不能为空");
    return;
  }
  savingArticle.value = true;
  try {
    if (editingArticleId.value) {
      await api.updateReferenceArticle(props.account.id, editingArticleId.value, {
        account_id: props.account.id, ...data,
      });
    } else {
      await api.createReferenceArticle(props.account.id, { account_id: props.account.id, ...data });
    }
    ElMessage.success(editingArticleId.value ? "已保存" : "已添加");
    articleFormVisible.value = false;
    await loadArticles();
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || "操作失败");
  } finally {
    savingArticle.value = false;
  }
}

async function deleteArticle(article: ReferenceArticle) {
  if (!props.account?.id) return;
  try {
    await ElMessageBox.confirm("确定删除此参考文章？", "确认", { type: "warning" });
    await api.deleteReferenceArticle(props.account.id, article.id);
    ElMessage.success("已删除");
    await loadArticles();
  } catch { /* cancelled */ }
}

onUnmounted(() => stopPolling());
</script>

<style scoped>
.distill-layout { display: flex; min-height: 480px; gap: 0; }
.distill-left {
  flex: 1; border-right: 1px solid var(--ink-border); padding: 16px;
  max-width: 40%;
}
.distill-right {
  flex: 1.5; padding: 16px; display: flex; flex-direction: column;
}
.distill-left-header, .distill-right-header {
  display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;
}
.distill-left-header h4, .distill-right-header h4 { margin: 0; }
.distill-article-list.readonly { opacity: 0.5; pointer-events: none; }
.distill-article-item {
  display: flex; justify-content: space-between; align-items: center;
  padding: 10px 12px; margin-bottom: 6px;
  background: var(--ink-surface); border-radius: 6px;
}
.distill-article-title { font-size: 13px; font-weight: 500; }
.distill-article-meta { font-size: 11px; color: var(--text-dim); }
.distill-center {
  flex: 1; display: flex; align-items: center; justify-content: center;
}
.distill-action-bar { text-align: center; padding-top: 16px; border-top: 1px solid var(--ink-border); }

.progress-bar {
  width: 100%; height: 8px; background: var(--ink-border); border-radius: 8px; overflow: hidden;
}
.progress-fill {
  height: 100%; background: var(--primary, #409eff); border-radius: 8px; transition: width 0.3s;
}
.progress-text { font-size: 13px; margin-top: 8px; color: var(--text-dim); }
.progress-dim { font-size: 13px; color: var(--text-on-dark); font-weight: 500; }
.progress-eta { font-size: 11px; color: var(--text-muted); }

.dimension-status-grid {
  display: grid; grid-template-columns: 1fr 1fr; gap: 4px; margin-top: 12px;
  text-align: left; font-size: 12px;
}
.dim-status-item { padding: 4px 8px; border-radius: 4px; }
.dim-status-item.done { color: var(--green-muted); }
.dim-status-item.active { color: var(--primary, #409eff); font-weight: 600; }
.dim-status-item.pending { color: var(--text-dim); }

.profile-dimensions-grid {
  display: grid; grid-template-columns: 1fr 1fr; gap: 8px; width: 100%;
}
.dimension-mini-card {
  display: flex; justify-content: space-between; align-items: center;
  padding: 8px 10px; background: var(--ink-surface); border-radius: 6px; font-size: 12px;
}
.dimension-mini-card.done .check { color: var(--green-muted); }

.status-tag { font-size: 11px; padding: 2px 8px; border-radius: 4px; }
.status-tag.ready { background: rgba(91,140,90,0.12); color: var(--green-muted); }
.status-tag.running { background: rgba(64,158,255,0.12); color: #409eff; }
.status-tag.failed { background: rgba(245,108,108,0.12); color: #f56c6c; }

.error-detail {
  background: var(--ink-surface); padding: 12px; border-radius: 6px;
  font-size: 12px; color: #cf1322; max-height: 200px; overflow-y: auto;
  text-align: left; white-space: pre-wrap;
}
.active-dot { color: var(--primary, #409eff); font-size: 10px; }
.empty-hint { text-align: center; color: var(--text-dim); font-size: 14px; padding: 32px 0; }
.spinner { font-size: 32px; animation: pulse 1.5s infinite; }
@keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.4; } }
</style>
```

### Step 10.2: Commit

```bash
git add src/components/accounts/DistillDialog.vue
git commit -m "feat: add DistillDialog with split layout, progress polling, error handling"
```

---

## Task 11: Frontend — Rewrite AccountsView

**Files:**
- Modify: `src/views/AccountsView.vue`

### Step 11.1: Rewrite AccountsView as card grid with entry points

Replace the entire content of `src/views/AccountsView.vue`:

```vue
<template>
  <div class="accounts-view">
    <header class="page-header">
      <div>
        <h1 class="page-title">账号风格</h1>
        <p class="page-subtitle">管理写作账号及其风格画像，蒸馏提取写作特征</p>
      </div>
      <el-button type="primary" size="large" @click="wizardRef?.show()">＋ 新增账号</el-button>
    </header>

    <!-- Account cards grid -->
    <div class="accounts-grid" v-loading="loading">
      <AccountCard
        v-for="acc in accounts"
        :key="acc.id"
        :account="acc"
        @edit-basic="openBasicInfo(acc)"
        @distill="openDistill(acc)"
        @word-count="openWordCount(acc)"
        @delete="handleDelete(acc)"
      />

      <!-- Add card placeholder -->
      <div class="add-card" @click="wizardRef?.show()">
        <span class="add-icon">＋</span>
        <span class="add-text">新增账号</span>
      </div>
    </div>

    <!-- Dialogs / Wizard -->
    <AccountWizard ref="wizardRef" @created="onAccountCreated" />
    <BasicInfoDialog v-model="basicVisible" :account="selectedAccount" @saved="onRefresh" />
    <DistillDialog v-model="distillVisible" :account="selectedAccount" @profile-updated="onRefresh" />
    <WordCountDialog v-model="wordCountVisible" :account="selectedAccount" @saved="onRefresh" />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { api, Account } from "@/api/client";
import { useAccountsStore } from "@/store/accounts";
import AccountCard from "@/components/accounts/AccountCard.vue";
import AccountWizard from "@/components/accounts/AccountWizard.vue";
import BasicInfoDialog from "@/components/accounts/BasicInfoDialog.vue";
import DistillDialog from "@/components/accounts/DistillDialog.vue";
import WordCountDialog from "@/components/accounts/WordCountDialog.vue";

const accountsStore = useAccountsStore();
const accounts = computed(() => accountsStore.accounts);
const loading = ref(false);

const selectedAccount = ref<Account | null>(null);
const basicVisible = ref(false);
const distillVisible = ref(false);
const wordCountVisible = ref(false);
const wizardRef = ref<InstanceType<typeof AccountWizard>>();

function openBasicInfo(acc: Account) { selectedAccount.value = acc; basicVisible.value = true; }
function openDistill(acc: Account) { selectedAccount.value = acc; distillVisible.value = true; }
function openWordCount(acc: Account) { selectedAccount.value = acc; wordCountVisible.value = true; }

async function onRefresh() {
  await accountsStore.invalidate();
  await accountsStore.fetch();
}

async function onAccountCreated() {
  await onRefresh();
}

async function handleDelete(acc: Account) {
  try {
    await ElMessageBox.confirm(`确定删除「${acc.account_name}」？`, "确认", { type: "warning" });
    await api.deleteAccount(acc.id);
    ElMessage.success("已删除");
    await onRefresh();
  } catch { /* cancelled */ }
}

onMounted(async () => {
  loading.value = true;
  await accountsStore.fetch();
  loading.value = false;
});
</script>

<style scoped>
/* Keep existing page header, grid, card styles from original AccountsView.vue */
.page-header {
  display: flex; justify-content: space-between; align-items: flex-start;
  margin-bottom: var(--space-xl);
}
.page-title {
  font-family: var(--font-serif); font-size: 28px; font-weight: 900;
  color: var(--text-on-dark); letter-spacing: 1px; margin-bottom: 4px;
}
.page-subtitle { font-size: 14px; color: var(--text-muted); }
.accounts-grid {
  display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 14px;
}
.add-card {
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  gap: 8px; border: 1px dashed var(--ink-border); border-radius: var(--radius-lg);
  min-height: 130px; cursor: pointer; transition: all var(--duration-fast) var(--ease-out);
}
.add-card:hover { border-color: var(--amber); }
.add-icon { font-size: 28px; color: var(--text-dim); font-weight: 300; }
.add-text { font-size: 13px; color: var(--text-muted); }
</style>
```

### Step 11.2: Remove old style blocks

The old AccountsView.vue styles (`.account-card`, `.card-avatar`, `.card-badge`, etc.) are now in `AccountCard.vue`. Delete those styles from AccountsView.vue. Keep only the styles shown above.

### Step 11.3: Commit

```bash
git add src/views/AccountsView.vue
git commit -m "refactor: rewrite AccountsView with card grid and separate dialogs"
```

---

## Task 12: E2E Testing — Backend Distill Flow

**Files:**
- Create: `tests/e2e/test_distill_flow.py`

### Step 12.1: Write backend E2E test

```python
"""E2E test: distill flow end to end"""
from fastapi.testclient import TestClient
from app.main import app
from app.database import Base, engine, SessionLocal
from app.models import Account, ReferenceArticle
import json


def test_full_distill_flow():
    """完整蒸馏流程：创建账号 → 添加文章 → 触发蒸馏 → 查询状态"""
    client = TestClient(app)
    Base.metadata.create_all(bind=engine)

    # 1. Create account
    resp = client.post("/accounts", json={"platform": "公众号", "account_name": "测试账号"})
    assert resp.status_code == 200
    acc_id = resp.json()["id"]

    # 2. Add reference articles
    resp = client.post(f"/accounts/{acc_id}/reference-articles", json={
        "account_id": acc_id,
        "title": "测试文章1",
        "content": "这是测试文章的内容。" * 50,
        "is_benchmark": True,
    })
    assert resp.status_code == 200

    # 3. Check initial status
    resp = client.get(f"/accounts/{acc_id}/distill/status")
    assert resp.status_code == 200
    assert resp.json()["status"] == "idle"

    # 4. Trigger distill (note: this test requires a running LLM service)
    #    Skip actual trigger in CI; test status endpoint independently
    resp = client.post(f"/accounts/{acc_id}/distill")
    assert resp.status_code in (200, 503)  # 200 if LLM is up, 503 if not

    Base.metadata.drop_all(bind=engine)
```

Run: `pytest tests/e2e/test_distill_flow.py -v`

### Step 12.2: Commit

```bash
git add tests/e2e/test_distill_flow.py
git commit -m "test: add e2e distill flow test"
```

---

## Task 13: Cleanup & Final Verification

**Files:**
- Check for unused code / dead paths

### Step 13.1: Remove unused code

Search for any remaining references to the old tab-based dialog pattern:
- The `activeTab` ref and `el-tabs` in old `AccountsView.vue` — already replaced in Task 11
- Verify no imports reference removed functions

### Step 13.2: Run all tests

```bash
pytest tests/ -v
```

Expected: All existing tests + new tests pass.

### Step 13.3: Start dev server and manually verify

```bash
# Terminal 1: Backend
cd ArticleGeneratorService && python -m uvicorn app.main:app --reload --port 8200

# Terminal 2: Frontend
cd ArticleGeneratorAdm && npm run dev
```

Manual verification checklist:
- [ ] Visit `/accounts` — card grid displays with status badges
- [ ] Click "新增账号" — 3-step wizard opens
- [ ] Complete wizard — account card appears with "蒸馏中..." badge
- [ ] After distill completes — badge shows "画像就绪 v1"
- [ ] Click "基本信息" — edit dialog opens
- [ ] Click "风格蒸馏" — split dialog opens with articles + profile
- [ ] Click "蒸馏风格" — progress bar + per-dimension status shows
- [ ] Click "字数配置" — word count dialog opens
- [ ] Delete account — confirmation + card removed + grid refresh

### Step 13.4: Commit final cleanup

```bash
git add -A
git commit -m "chore: cleanup and finalize account style UX redesign"
```

---

## Summary

| Task | Description | Dependencies |
|------|-------------|--------------|
| 1 | Backend: Model + Schema fixes (word_count) | None |
| 2 | Backend: Distill status endpoint + tests | Task 1 |
| 3 | Backend: Rewrite distill task (7 calls) | Task 1 |
| 4 | Backend: word_count CRUD tests | Task 1 |
| 5 | Frontend: API types + client updates | None |
| 6 | Frontend: AccountCard component | Task 5 |
| 7 | Frontend: ReferenceArticleForm component | None |
| 8 | Frontend: BasicInfoDialog + WordCountDialog | Task 5 |
| 9 | Frontend: AccountWizard component | Task 6, 7 |
| 10 | Frontend: DistillDialog component | Task 5, 7 |
| 11 | Frontend: Rewrite AccountsView | Tasks 6, 8, 9, 10 |
| 12 | E2E tests | Tasks 2, 3 |
| 13 | Cleanup + final verification | All |
