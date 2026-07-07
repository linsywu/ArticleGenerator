# 风格蒸馏特征清单持久化 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 持久化蒸馏 Stage 1 的特征清单（带原文引证的证据）到新字段 `style_features`，并在蒸馏弹窗以折叠面板展示，下游生成注入零改动。

**Architecture:** Stage 1 产出 features（证据，给人）和 Stage 2 产出 guide（指令，给 LLM）服务不同对象，分离存储：`style_profile`=guide（继续注入 `{{style_profile}}`），`style_features`=features（新字段，仅展示/审计，不注入任何生成任务）。弹窗用折叠面板——指南为主、证据可折叠。

**Tech Stack:** FastAPI + SQLAlchemy + Celery（后端）/ Vue 3 + Element Plus（前端）/ SQL 迁移脚本

## Global Constraints

- 注释/回复语言：中文
- 提交格式：语义化（`feat:`/`refactor:`/`docs:`）
- 后端测试从 `ArticleGeneratorService/` 目录运行（SQLite CWD 依赖——`pytest` 和 `python` 必须在该目录执行，否则命中错误的 db 文件）
- 前端变更必须浏览器验证，禁止仅 build+test 即声称通过（前端验证铁律）
- 禁止未经授权删除业务数据；本计划只 ADD COLUMN（不删数据）
- CrazyRouter 当前可用模型：`deepseek-v4-flash`（若蒸馏报 model_not_found，把 `scenario_configs` 中 distill-extract/distill-synthesize 的 model 改为此值）

**设计文档:** `docs/superpowers/specs/2026-07-07-distill-features-persistence-design.md`

**分支:** `feature/distill-quality-redesign`（本计划延续该分支，前置工作 Task 1-7 已合入）

---

## File Structure

| 文件 | 责任 | 操作 |
|------|------|------|
| `ArticleGeneratorService/app/models.py` | `Account` 模型，新增 `style_features` 列 | 修改 |
| `ArticleGeneratorService/app/schemas.py` | `AccountResponse`，新增 `style_features` 字段 | 修改 |
| `ArticleGeneratorService/app/tasks.py` | `trigger_distill` Stage 1 后落库 `style_features` | 修改 |
| `ArticleGeneratorService/tests/test_distill_task.py` | 新增 `style_features` 填充断言 | 修改 |
| `ArticleGeneratorDatabase/migrations/021_add_style_features.sql` | ADD COLUMN 迁移 | 新建 |
| `ArticleGeneratorAdm/src/api/types.ts` | `Account` 接口新增 `style_features` | 修改 |
| `ArticleGeneratorAdm/src/components/accounts/DistillDialog.vue` | 折叠面板展示证据清单 | 修改 |

---

### Task 1: 后端 — 新增 style_features 字段 + trigger_distill 落库 + 测试

**Files:**
- Modify: `ArticleGeneratorService/app/models.py`（`Account` 类，`style_profile` 列之后）
- Modify: `ArticleGeneratorService/app/schemas.py`（`AccountResponse`，`style_profile` 字段之后）
- Modify: `ArticleGeneratorService/app/tasks.py`（`trigger_distill` 的"标记 synthesizing"块，约 410-414 行）
- Test: `ArticleGeneratorService/tests/test_distill_task.py`（`test_distill_task_two_llm_calls_and_stores_guide` 测试）

**Interfaces:**
- Consumes: `trigger_distill` Stage 1 的局部变量 `features`（已存在，约 tasks.py:411）
- Produces: `Account.style_features` 列（TEXT，可空）；`AccountResponse.style_features` 字段（API 响应包含）；`trigger_distill` 在 Stage 1 成功后写入该列

- [ ] **Step 1: 写失败测试——在 test_distill_task.py 的现有测试中加 style_features 断言**

打开 `ArticleGeneratorService/tests/test_distill_task.py`，找到 `test_distill_task_two_llm_calls_and_stores_guide` 函数。在该函数末尾的 `db.close()` 之前，已有的断言块之后，追加一行断言：

```python
    db = SessionLocal()
    account = db.query(Account).filter(Account.id == acc_id).first()
    assert account.style_profile_status == "ready"
    assert "写作风格指南" in (account.style_profile or "")
    assert account.style_profile_version >= 1
    assert account.style_features == stage1_output  # NEW：Stage 1 证据已持久化
    db.close()
```

注意：`stage1_output` 是该测试顶部已定义的 Stage 1 mock 输出变量。

- [ ] **Step 2: 跑测试确认 RED**

Run:
```bash
cd ArticleGeneratorService && pytest tests/test_distill_task.py::test_distill_task_two_llm_calls_and_stores_guide -v
```
Expected: FAIL — `AttributeError: 'Account' object has no attribute 'style_features'`（模型还没这列）。

- [ ] **Step 3: models.py 新增 style_features 列**

在 `ArticleGeneratorService/app/models.py` 的 `Account` 类中，`style_profile = Column(Text)` 这一行之后插入新列：

```python
    style_profile = Column(Text)
    style_features = Column(Text)  # Stage1 证据清单（带原文引证），仅展示/审计用，不注入生成
    style_profile_updated_at = Column(DateTime)
```

- [ ] **Step 4: schemas.py 新增 style_features 字段**

在 `ArticleGeneratorService/app/schemas.py` 的 `AccountResponse` 类中，`style_profile` 字段之后插入：

```python
    style_profile: Optional[str] = None
    style_features: Optional[str] = None
    style_profile_updated_at: Optional[CstDateTime] = None
```

- [ ] **Step 5: tasks.py trigger_distill 落库 style_features**

在 `ArticleGeneratorService/app/tasks.py` 的 `trigger_distill` 函数中，找到"标记 synthesizing"块（Stage 1 成功后、Stage 2 调用前）：

```python
        # 标记 synthesizing
        account = db.query(Account).filter(Account.id == account_id).first()
        if account:
            account.style_profile_status = "synthesizing"
            db.commit()
```

替换为（加入 `style_features` 持久化——Stage 2 失败也保留证据供调试）：

```python
        # 标记 synthesizing + 持久化 Stage 1 证据（Stage 2 失败也保留供调试）
        account = db.query(Account).filter(Account.id == account_id).first()
        if account:
            account.style_features = features
            account.style_profile_status = "synthesizing"
            db.commit()
```

- [ ] **Step 6: 跑测试确认 GREEN**

Run:
```bash
cd ArticleGeneratorService && pytest tests/test_distill_task.py -v
```
Expected: PASS（5 个测试全过，含新增的 style_features 断言）。

- [ ] **Step 7: 跑全量后端测试确认无回归**

Run:
```bash
cd ArticleGeneratorService && pytest tests/ 2>&1 | tail -5
```
Expected: 除已知 1 个 pre-existing 失败（`test_account_word_count::test_update_word_count`，与本变更无关）外全部 PASS。

- [ ] **Step 8: Commit**

```bash
git add ArticleGeneratorService/app/models.py ArticleGeneratorService/app/schemas.py ArticleGeneratorService/app/tasks.py ArticleGeneratorService/tests/test_distill_task.py
git commit -m "feat: 新增 style_features 字段，trigger_distill 持久化 Stage1 证据清单"
```

---

### Task 2: DB 迁移 021_add_style_features

**Files:**
- Create: `ArticleGeneratorDatabase/migrations/021_add_style_features.sql`

**Interfaces:**
- Produces: dev DB `accounts` 表新增 `style_features TEXT` 列。Task 3 前端展示依赖 API 返回该字段（需后端 + DB 都就绪）。

- [ ] **Step 1: 创建迁移文件**

创建 `ArticleGeneratorDatabase/migrations/021_add_style_features.sql`：

```sql
-- 021: 新增 style_features 列
-- 存储蒸馏 Stage 1 的特征清单（带原文引证的证据），仅展示/审计用，不注入生成任务
ALTER TABLE accounts ADD COLUMN style_features TEXT;
```

- [ ] **Step 2: 在 dev DB 上执行迁移**

Run（从 ArticleGeneratorService 目录，命中真实 dev DB）:
```bash
cd ArticleGeneratorService && sqlite3 article_generator.db "ALTER TABLE accounts ADD COLUMN style_features TEXT;"
```
Expected: 无输出（成功）。若报 `duplicate column name: style_features`，说明已存在，跳过即可。

- [ ] **Step 3: 验证列已添加**

Run:
```bash
cd ArticleGeneratorService && sqlite3 article_generator.db "PRAGMA table_info(accounts);" | grep style_features
```
Expected: 输出一行，含 `style_features|TEXT|0||0`。

- [ ] **Step 4: Commit**

```bash
git add ArticleGeneratorDatabase/migrations/021_add_style_features.sql
git commit -m "feat: 021 迁移新增 style_features 列"
```

---

### Task 3: 前端 — types.ts 加字段 + DistillDialog 折叠面板展示

**Files:**
- Modify: `ArticleGeneratorAdm/src/api/types.ts`（`Account` 接口，`style_profile` 之后）
- Modify: `ArticleGeneratorAdm/src/components/accounts/DistillDialog.vue`（idle + completed 两个分支的 `.profile-content-area` 区，约 44-50、70-74 行）

**Interfaces:**
- Consumes: 后端 `AccountResponse.style_features`（Task 1 产出）
- Produces: 弹窗展示指南（主）+ 可折叠证据清单（辅）；`style_features` 为空时隐藏折叠区

**背景:** 当前 idle 和 completed 两个分支都只有一个 `.guide-text` 展示 `style_profile`。改为：主区展示指南，下方加 `<el-collapse>` 折叠证据清单（仅当 `account.style_features` 非空时渲染）。

- [ ] **Step 1: types.ts 加 style_features 字段**

在 `ArticleGeneratorAdm/src/api/types.ts` 的 `Account` 接口中，`style_profile?: string;` 之后插入：

```typescript
  style_profile?: string;
  style_features?: string;
  style_profile_updated_at?: string;
```

- [ ] **Step 2: DistillDialog idle 分支加折叠证据区**

在 `ArticleGeneratorAdm/src/components/accounts/DistillDialog.vue` 的 idle 分支，把：

```vue
          <div v-else-if="account?.style_profile" class="profile-content-area">
            <div class="guide-text">{{ account.style_profile }}</div>
          </div>
```

替换为（主指南 + 折叠证据）：

```vue
          <div v-else-if="account?.style_profile" class="profile-content-area">
            <div class="guide-text">{{ account.style_profile }}</div>
            <el-collapse v-if="account?.style_features" class="features-collapse">
              <el-collapse-item title="▸ 查看证据清单（作者类型 + 引证特征）" name="features">
                <div class="features-text">{{ account.style_features }}</div>
              </el-collapse-item>
            </el-collapse>
          </div>
```

- [ ] **Step 3: DistillDialog completed 分支加折叠证据区**

把 completed 分支：

```vue
        <div v-else-if="status === 'completed'" class="distill-center">
          <div class="profile-content-area">
            <div class="guide-text">{{ account?.style_profile || '（无指南内容）' }}</div>
          </div>
        </div>
```

替换为：

```vue
        <div v-else-if="status === 'completed'" class="distill-center">
          <div class="profile-content-area">
            <div class="guide-text">{{ account?.style_profile || '（无指南内容）' }}</div>
            <el-collapse v-if="account?.style_features" class="features-collapse">
              <el-collapse-item title="▸ 查看证据清单（作者类型 + 引证特征）" name="features">
                <div class="features-text">{{ account.style_features }}</div>
              </el-collapse-item>
            </el-collapse>
          </div>
        </div>
```

- [ ] **Step 4: 加折叠区样式**

在 `<style scoped>` 中，`.guide-text { ... }` 块之后追加：

```css
.features-collapse { width: 100%; margin-top: 12px; border-top: 1px dashed var(--ink-border); padding-top: 8px; }
.features-collapse :deep(.el-collapse-item__header) { font-size: 12px; color: var(--text-dim); font-weight: 500; }
.features-text {
  font-size: 12px; line-height: 1.7; color: var(--text-dim);
  white-space: pre-wrap; background: var(--ink-surface);
  border-radius: var(--radius-md); padding: 10px 12px; margin: 0;
}
```

- [ ] **Step 5: Build 验证无编译错误**

Run:
```bash
cd ArticleGeneratorAdm && npm run build 2>&1 | tail -3
```
Expected: `✓ built in` 无错误。

- [ ] **Step 6: 全局搜索确认 style_features 引用闭合**

Run:
```bash
cd ArticleGeneratorAdm && grep -rn "style_features" src/
```
Expected: 命中 `types.ts`（字段定义）+ `DistillDialog.vue`（2 处 v-if + 2 处插值）。无其他残留。

- [ ] **Step 7: Commit**

```bash
git add ArticleGeneratorAdm/src/api/types.ts ArticleGeneratorAdm/src/components/accounts/DistillDialog.vue
git commit -m "feat: DistillDialog 折叠面板展示证据清单 + types 加 style_features"
```

---

### Task 4: 重新蒸馏陆拾一 + 端到端验证

**Files:** 无代码改动（验证任务）

**目标:** 重新蒸馏陆拾一（id=1）让 `style_features` 填充，验证弹窗折叠面板正确展示证据清单。

**前提:** 全栈服务运行（Redis + Backend :8000 + Celery + LLM Gateway :8001 + Frontend :5173）。若 LLM 报 `model_not_found`，把 `scenario_configs` 中 distill-extract/distill-synthesize 的 model 改为 `deepseek-v4-flash`。

- [ ] **Step 1: 确保服务运行 + Celery worker 在**

Run:
```bash
redis-cli ping                    # PONG
curl -s http://localhost:8001/    # {"message":"LLM Gateway",...}
curl -s http://localhost:8000/api/accounts/1 -H "Authorization: Bearer <token>" | head -c 80   # 有响应
ps aux | grep celery | grep -v grep | head -1   # celery worker 进程在
```
若 Celery 未起：`cd ArticleGeneratorService && celery -A app.tasks:celery_app worker -l info &`
若后端代码已改但进程未重载：重启 uvicorn。

- [ ] **Step 2: 登录拿 token**

Run:
```bash
curl -s -X POST http://localhost:8000/api/auth/login -H "Content-Type: application/json" -d '{"username":"admin","password":"admin123"}' | python3 -c "import sys,json;print(json.load(sys.stdin)['access_token'])" > /tmp/jwt.txt
echo "token: $(head -c 20 /tmp/jwt.txt)..."
```

- [ ] **Step 3: 触发陆拾一蒸馏**

Run:
```bash
curl -s -X POST http://localhost:8000/api/accounts/1/distill -H "Authorization: Bearer $(cat /tmp/jwt.txt)"
```
Expected: `{"message":"蒸馏任务已提交","task_id":"..."}`

- [ ] **Step 4: 轮询直到 completed**

Run:
```bash
for i in $(seq 1 24); do RESP=$(curl -s "http://localhost:8000/api/accounts/1/distill/status" -H "Authorization: Bearer $(cat /tmp/jwt.txt)"); echo "$(date +%H:%M:%S) $RESP"; echo "$RESP" | grep -q '"completed"' && echo "=== DONE ===" && break; sleep 15; done
```
Expected: `running stage:1` → `running stage:2` → `completed style_profile_version:N+1`。

- [ ] **Step 5: 验证 style_features 已填充**

Run:
```bash
curl -s "http://localhost:8000/api/accounts/1" -H "Authorization: Bearer $(cat /tmp/jwt.txt)" | python3 -c "import sys,json; d=json.load(sys.stdin); f=d.get('style_features',''); print('style_features exists:', bool(f)); print('length:', len(f or '')); print('---preview---'); print((f or '')[:300])"
```
Expected: `style_features exists: True`，内容含"作者类型"和「原文引证」格式。

- [ ] **Step 6: 浏览器验证（前端验证铁律——不可绕过）**

刷新 `http://localhost:5173/accounts` → 陆拾一 → 蒸馏弹窗：
1. 右侧主区展示写作风格指南（"# 写作风格指南"开头）
2. 指南下方有"▸ 查看证据清单（作者类型 + 引证特征）"折叠条
3. 点击展开 → 显示特征清单（含「原文引证」）
4. 控制台无报错
5. （可选）查一个未蒸馏的老账号，确认 `style_features` 为空时折叠条不显示

- [ ] **Step 7: 无需 commit（验证任务）**

---

## Self-Review

**1. Spec coverage（设计文档 → 任务映射）:**
- 新列 `style_features` → Task 1 Step 3（models）✓
- 迁移 021 → Task 2 ✓
- `AccountResponse.style_features` → Task 1 Step 4（schemas）✓
- `trigger_distill` Stage 1 后存 features → Task 1 Step 5 ✓
- 下游注入零改动 → 无需任务（设计明确不注入）✓
- types.ts 字段 → Task 3 Step 1 ✓
- 折叠面板展示（指南为主、证据可折叠、空时隐藏）→ Task 3 Step 2-4 ✓
- 测试断言 → Task 1 Step 1 ✓
- 端到端验证 → Task 4 ✓
- 边界（老账号 NULL 隐藏）→ Task 3 Step 2 的 `v-if="account?.style_features"` ✓；Task 4 Step 6 验证 ✓

**2. Placeholder scan:** 无 TBD/TODO；每个代码步骤含完整代码。✓

**3. Type consistency:**
- `Account.style_features` 列（models）↔ `AccountResponse.style_features`（schemas）↔ TS `Account.style_features?: string`（types）↔ `account?.style_features`（DistillDialog）✓
- `trigger_distill` 写入 `account.style_features = features`（`features` 是 Stage 1 已存在的局部变量）✓
- 测试断言 `account.style_features == stage1_output`（`stage1_output` 是测试顶部定义的 mock）✓

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-07-07-distill-features-persistence.md`.

**注：** 当前会话模型的 subagent 派发不可用（Unknown Model 错误）。若在新会话/新模型下执行，可选：

**1. Subagent-Driven** — 每 Task 派独立 subagent + 两阶段审查（subagent 可用时推荐）

**2. Inline Execution** — 当前会话顺序执行，每 Task 后 checkpoint 确认（subagent 不可用时的选择）
