# ArticleGenerator v2 — 半自动化重构实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 ArticleGenerator 从全自动化系统重构为半自动写作辅助系统，核心价值从"自动抓取→生成→发布"转变为"蒸馏作者风格→多步骤创作→评审微调循环→高质量文章产出"

**Architecture:** 保持现有 FastAPI 后端 + Celery 异步任务 + LLM Gateway + Vue 3 前端的架构不变。主要改动集中在：(1) Account 模型新增结构化风格画像字段，(2) 蒸馏任务输出从自由文本改为 7 维度 JSON，(3) 前端管理后台页面重组，(4) 新增文章创作多步骤流程，(5) 新增评审微调循环 API

**Tech Stack:** Python 3.10 + FastAPI + SQLAlchemy + Celery + Vue 3 + Element Plus + TypeScript

---

## Phase B — 结构化风格画像（当前阶段）

### 文件结构

| 操作 | 文件 | 职责 |
|------|------|------|
| 新增 | `ArticleGeneratorDatabase/migrations/004_structured_style_profile.sql` | 数据库迁移 SQL |
| 修改 | `ArticleGeneratorService/app/models.py:24-40` | Account 模型新增 3 列 |
| 修改 | `ArticleGeneratorService/app/schemas.py:10-35` | AccountResponse 新增结构化画像字段 |
| 修改 | `ArticleGeneratorService/app/tasks.py:240-272` | trigger_distill 解析 JSON 并存结构化字段 |
| 修改 | `ArticleGeneratorService/app/api/distill.py` | distill 端点无需改动（仅触发 Celery） |
| 修改 | `LLMService/.../scenario_configs` 表 distill 行 | system_prompt_template 要求 JSON 输出 |
| 修改 | `ArticleGeneratorAdm/src/api/client.ts` | Account 接口新增字段 |
| 修改 | `ArticleGeneratorAdm/src/views/AccountsView.vue` | 风格画像 Tab 改为维度卡片 |
| 修改 | `ArticleGeneratorAdm/src/views/DistillView.vue` | 风格画像 Tab 改为维度卡片 |

---

### Task 1: 数据库迁移 + 模型更新

**Files:**
- Create: `ArticleGeneratorDatabase/migrations/004_structured_style_profile.sql`
- Modify: `ArticleGeneratorService/app/models.py:34-37`

- [ ] **Step 1: 创建迁移 SQL 文件**

```sql
-- 004_structured_style_profile.sql
-- 新增结构化风格画像字段

ALTER TABLE accounts ADD COLUMN style_profile_structured TEXT;
ALTER TABLE accounts ADD COLUMN style_profile_version INTEGER DEFAULT 1;
ALTER TABLE accounts ADD COLUMN style_profile_status VARCHAR(20) DEFAULT 'none';
```

- [ ] **Step 2: 更新 Account 模型**

在 `ArticleGeneratorService/app/models.py` 的 `Account` 类中，`style_profile_updated_at` 之后新增：

```python
    style_profile_structured = Column(Text)  # JSON: 7维度结构化画像
    style_profile_version = Column(Integer, default=1)
    style_profile_status = Column(String(20), default="none")  # none/pending/ready/outdated
```

最终 Account 模型字段顺序：

```python
class Account(Base):
    __tablename__ = "accounts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    platform = Column(String(50), nullable=False)
    account_name = Column(String(100), nullable=False)
    lora_path = Column(String(500))
    sample_articles = Column(Text)
    style_profile = Column(Text)
    style_profile_updated_at = Column(DateTime)
    style_profile_structured = Column(Text)  # JSON: 7维度结构化画像
    style_profile_version = Column(Integer, default=1)
    style_profile_status = Column(String(20), default="none")  # none/pending/ready/outdated
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    articles = relationship("Article", back_populates="account")
```

- [ ] **Step 3: 应用迁移到本地 SQLite**

```bash
cd ArticleGeneratorService
python3 -c "
from app.database import engine
from sqlalchemy import text
# 检查列是否已存在，不存在则添加
with engine.connect() as conn:
    cols = [row[1] for row in conn.execute(text('PRAGMA table_info(accounts)'))]
    if 'style_profile_structured' not in cols:
        conn.execute(text('ALTER TABLE accounts ADD COLUMN style_profile_structured TEXT'))
    if 'style_profile_version' not in cols:
        conn.execute(text('ALTER TABLE accounts ADD COLUMN style_profile_version INTEGER DEFAULT 1'))
    if 'style_profile_status' not in cols:
        conn.execute(text('ALTER TABLE accounts ADD COLUMN style_profile_status VARCHAR(20) DEFAULT \"none\"'))
    conn.commit()
    print('Migration applied successfully')
"
```

- [ ] **Step 4: 验证模型可正常导入**

```bash
cd ArticleGeneratorService
python3 -c "from app.models import Account; print('Account columns:', [c.name for c in Account.__table__.columns])"
```

预期输出包含 `style_profile_structured`, `style_profile_version`, `style_profile_status`

- [ ] **Step 5: Commit**

```bash
git add ArticleGeneratorDatabase/migrations/004_structured_style_profile.sql ArticleGeneratorService/app/models.py
git commit -m "feat: 新增结构化风格画像字段 — style_profile_structured/style_profile_version/style_profile_status"
```

---

### Task 2: Schema + API 更新

**Files:**
- Modify: `ArticleGeneratorService/app/schemas.py:28-35`

- [ ] **Step 1: 更新 AccountResponse schema**

在 `schemas.py` 中，替换 `AccountResponse`：

```python
class AccountResponse(AccountBase):
    id: int
    style_profile: Optional[str] = None
    style_profile_updated_at: Optional[datetime] = None
    style_profile_structured: Optional[dict] = None
    style_profile_version: Optional[int] = None
    style_profile_status: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True
```

- [ ] **Step 2: 验证 API 返回新字段**

启动后端后：

```bash
curl -s http://localhost:8000/api/accounts/1 | python3 -m json.tool | grep -E "style_profile_structured|style_profile_version|style_profile_status"
```

预期能看到这些字段（值可能为 null）。

- [ ] **Step 3: Commit**

```bash
git add ArticleGeneratorService/app/schemas.py
git commit -m "feat: AccountResponse 新增结构化画像字段"
```

---

### Task 3: 蒸馏 Prompt 改造 — 要求 JSON 输出

**Files:**
- Modify: 数据库中 `scenario_configs` 表 `scenario='distill'` 的 `system_prompt_template`

- [ ] **Step 1: 编写新的 distill 系统提示词模板**

通过管理后台或直接 SQL 更新（需确认现有 distill 模板的 provider_id 和 model）：

```sql
-- 先查看当前 distill 配置
SELECT id, scenario, model, system_prompt_template FROM scenario_configs WHERE scenario='distill';
```

新模板内容（替换旧的 `system_prompt_template`）：

```
你是一个写作风格分析专家。根据以下参考文章，提炼出该账号的结构化写作风格画像。

参考文章数量：{{num_articles}} 篇
参考文章内容：
{{articles_content}}

请严格输出以下 JSON 格式（不要包含 markdown 代码块标记，只输出纯 JSON）：

{
  "thinking_pattern": "论证习惯的描述（归纳/演绎/类比），常用逻辑框架，思考深度",
  "structure_pattern": "开头偏好（观点直出/故事切入/数据开场/对话开头），段落组织方式，结尾风格",
  "sentence_pattern": "句子长度分布（短句/长句/参差），常用修辞手法，标点偏好，段落节奏",
  "vocabulary_pattern": "高频词汇列表（10-20个），禁用词/避免的表达，语气词使用频率",
  "evidence_type": "偏好论据类型（个人经历/数据统计/案例分析/引用权威），论据使用密度",
  "taboos": "该账号绝不会写的内容清单（如：道德说教、过度抒情、模板化总结、总的来说...）",
  "blank_leaving": "留白程度描述（道理讲几分满、是否留悬念、是否刻意不解释、戛然而止的频率）"
}
```

- [ ] **Step 2: 通过 API 更新场景配置**

```bash
# 先获取 distill 配置的 ID
curl -s http://localhost:8000/api/scenario-configs/by-scenario/distill | python3 -m json.tool

# 更新（假设 id=1）
curl -s -X PUT http://localhost:8000/api/scenario-configs/1 \
  -H "Content-Type: application/json" \
  -d '{"system_prompt_template": "你是一个写作风格分析专家。根据以下参考文章，提炼出该账号的结构化写作风格画像。\n\n参考文章数量：{{num_articles}} 篇\n参考文章内容：\n{{articles_content}}\n\n请严格输出以下 JSON 格式（不要包含 markdown 代码块标记，只输出纯 JSON）：\n\n{\n  \"thinking_pattern\": \"论证习惯的描述（归纳/演绎/类比），常用逻辑框架，思考深度\",\n  \"structure_pattern\": \"开头偏好（观点直出/故事切入/数据开场/对话开头），段落组织方式，结尾风格\",\n  \"sentence_pattern\": \"句子长度分布（短句/长句/参差），常用修辞手法，标点偏好，段落节奏\",\n  \"vocabulary_pattern\": \"高频词汇列表（10-20个），禁用词/避免的表达，语气词使用频率\",\n  \"evidence_type\": \"偏好论据类型（个人经历/数据统计/案例分析/引用权威），论据使用密度\",\n  \"taboos\": \"该账号绝不会写的内容清单（如：道德说教、过度抒情、模板化总结、总的来说...）\",\n  \"blank_leaving\": \"留白程度描述（道理讲几分满、是否留悬念、是否刻意不解释、戛然而止的频率）\"\n}"}' | python3 -m json.tool
```

- [ ] **Step 3: Commit (可选，场景配置通过 DB seed 管理)**

如果项目有 seed 脚本，同步更新 `scripts/seed_providers.py` 中的 distill 模板。

---

### Task 4: 蒸馏任务改造 — 解析 JSON 存入结构化字段

**Files:**
- Modify: `ArticleGeneratorService/app/tasks.py:240-272`

- [ ] **Step 1: 改写 trigger_distill 任务**

在 `tasks.py` 顶部新增 import：

```python
import json
import re
```

替换 `trigger_distill` 函数体（第 240-272 行）：

```python
@celery_app.task(bind=True)
def trigger_distill(self, account_id: int, articles_content: list, num_articles: int):
    """异步蒸馏：参考文章 → 结构化风格画像"""
    db = SessionLocal()
    try:
        llm_url = settings.llm_service_url.rstrip("/")
        with httpx.Client(timeout=300.0) as client:
            resp = client.post(f"{llm_url}/chat", json={
                "scenario": "distill",
                "account_id": account_id,
                "variables": {
                    "num_articles": str(num_articles),
                    "articles_content": "\n\n---\n\n".join(articles_content),
                },
            })
            resp.raise_for_status()
            data = resp.json()

        content = data.get("content", "")
        if not content:
            raise ValueError("蒸馏返回内容为空")

        # 解析 LLM 返回的结构化 JSON
        structured = None
        try:
            # 尝试直接解析
            structured = json.loads(content)
        except json.JSONDecodeError:
            # 尝试提取 markdown 代码块中的 JSON
            match = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', content, re.DOTALL)
            if match:
                try:
                    structured = json.loads(match.group(1))
                except json.JSONDecodeError:
                    pass

        # 生成兼容旧版的摘要文本
        summary_text = content  # 回退：使用原始返回内容
        if structured:
            parts = []
            dim_labels = {
                "thinking_pattern": "思维特征",
                "structure_pattern": "结构模式",
                "sentence_pattern": "句式特征",
                "vocabulary_pattern": "词汇偏好",
                "evidence_type": "论据类型",
                "taboos": "禁忌清单",
                "blank_leaving": "留白程度",
            }
            for key, label in dim_labels.items():
                if structured.get(key):
                    parts.append(f"【{label}】\n{structured[key]}")
            summary_text = "\n\n".join(parts)

        account = db.query(Account).filter(Account.id == account_id).first()
        if account:
            account.style_profile = summary_text  # 兼容旧版文本画像
            account.style_profile_structured = json.dumps(structured, ensure_ascii=False) if structured else None
            account.style_profile_status = "ready" if structured else "failed"
            account.style_profile_version = (account.style_profile_version or 0) + 1
            account.style_profile_updated_at = datetime.utcnow()
            db.commit()

        return {"account_id": account_id, "status": account.style_profile_status if account else "error"}
    except Exception as e:
        # 标记失败
        account = db.query(Account).filter(Account.id == account_id).first()
        if account:
            account.style_profile_status = "failed"
            db.commit()
        raise
    finally:
        db.close()
```

- [ ] **Step 2: 重启 Celery Worker**

```bash
# 停止旧 worker
pkill -f "celery -A app.tasks"

# 启动新 worker
cd ArticleGeneratorService
celery -A app.tasks:celery_app worker -l info &
```

- [ ] **Step 3: 端到端验证**

触发蒸馏并检查结果：

```bash
# 触发蒸馏（选择有参考文章的账号，比如 account_id=1）
curl -s -X POST http://localhost:8000/api/accounts/1/distill | python3 -m json.tool

# 等待任务完成（约 30-60 秒），然后检查结果
curl -s http://localhost:8000/api/accounts/1 | python3 -c "
import sys, json
data = json.load(sys.stdin)
print('status:', data.get('style_profile_status'))
structured = data.get('style_profile_structured')
if structured:
    for k, v in structured.items():
        print(f'  {k}: {str(v)[:80]}...' if len(str(v))>80 else f'  {k}: {v}')
else:
    print('structured is None')
"
```

预期：`style_profile_status` 为 `ready`，`style_profile_structured` 包含 7 个维度。

- [ ] **Step 4: Commit**

```bash
git add ArticleGeneratorService/app/tasks.py
git commit -m "feat: trigger_distill 解析结构化 JSON 并存入 style_profile_structured 字段"
```

---

### Task 5: 前端 API Client + 画像展示

**Files:**
- Modify: `ArticleGeneratorAdm/src/api/client.ts` — Account 类型
- Modify: `ArticleGeneratorAdm/src/views/AccountsView.vue` — 风格画像 Tab
- Modify: `ArticleGeneratorAdm/src/views/DistillView.vue` — 风格画像 Tab

- [ ] **Step 1: 更新前端 Account 类型定义**

在 `client.ts` 的 `Account` 接口中新增：

```typescript
export interface Account {
  id: number
  platform: string
  account_name: string
  lora_path?: string
  sample_articles?: string
  style_profile?: string
  style_profile_updated_at?: string
  style_profile_structured?: StyleProfile | null
  style_profile_version?: number
  style_profile_status?: string
  created_at: string
}

// 新增结构化画像类型
export interface StyleProfile {
  thinking_pattern: string
  structure_pattern: string
  sentence_pattern: string
  vocabulary_pattern: string
  evidence_type: string
  taboos: string
  blank_leaving: string
}
```

- [ ] **Step 2: 改造 AccountsView 风格画像 Tab**

在 `AccountsView.vue` 的风格画像 Tab（第三个 Tab）中，用 `v-if="account.style_profile_structured"` 切换展示：

```vue
<!-- 结构化画像展示 -->
<template v-if="account.style_profile_structured">
  <div class="style-profile-cards">
    <el-card v-for="dim in styleDimensions" :key="dim.key" class="dim-card">
      <template #header>
        <div class="dim-header">
          <span>{{ dim.icon }}</span>
          <span>{{ dim.label }}</span>
        </div>
      </template>
      <p class="dim-content">{{ account.style_profile_structured[dim.key] || '未定义' }}</p>
    </el-card>
  </div>
  <el-tag type="success" v-if="account.style_profile_status === 'ready'">画像就绪</el-tag>
  <el-tag type="warning" v-if="account.style_profile_status === 'outdated'">画像待更新</el-tag>
</template>

<!-- 旧版文本画像（降级展示） -->
<template v-else-if="account.style_profile">
  <el-input type="textarea" :model-value="account.style_profile" readonly rows="20" />
</template>

<!-- 未生成 -->
<el-empty v-else description="尚未生成风格画像，请先添加参考文章并触发蒸馏" />
```

对应的 script 部分新增：

```typescript
const styleDimensions = [
  { key: 'thinking_pattern', label: '思维特征', icon: '🧠' },
  { key: 'structure_pattern', label: '结构模式', icon: '🏗️' },
  { key: 'sentence_pattern', label: '句式特征', icon: '✍️' },
  { key: 'vocabulary_pattern', label: '词汇偏好', icon: '📝' },
  { key: 'evidence_type', label: '论据类型', icon: '📊' },
  { key: 'taboos', label: '禁忌清单', icon: '🚫' },
  { key: 'blank_leaving', label: '留白程度', icon: '💭' },
]
```

样式：

```css
.style-profile-cards {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 16px;
}
.dim-card {
  border-left: 3px solid #409EFF;
}
.dim-header {
  font-weight: bold;
  display: flex;
  align-items: center;
  gap: 8px;
}
.dim-content {
  white-space: pre-wrap;
  font-size: 14px;
  line-height: 1.6;
}
```

- [ ] **Step 3: 同样改造 DistillView 风格画像 Tab**

`DistillView.vue` 中的风格画像 Tab 做同样改造（复用相同的 `styleDimensions` 和卡片布局）。如果蒸馏轮询检测到 `style_profile_status === 'ready'`，自动切换到结构化展示。

- [ ] **Step 4: 验证前端展示**

```bash
cd ArticleGeneratorAdm
npm run dev
```

浏览器打开 http://localhost:5173/accounts → 选择有结构化画像的账号 → 点击"风格画像"Tab → 确认看到 7 张维度卡片。

- [ ] **Step 5: Commit**

```bash
git add ArticleGeneratorAdm/src/api/client.ts ArticleGeneratorAdm/src/views/AccountsView.vue ArticleGeneratorAdm/src/views/DistillView.vue
git commit -m "feat: 前端结构化风格画像展示 — 7维度卡片替代自由文本"
```

---

## Phase H — 管理后台重组

### 文件结构

| 操作 | 文件 | 职责 |
|------|------|------|
| 新建 | `ArticleGeneratorAdm/src/views/CreateView.vue` | 文章创作页（多步骤流程） |
| 修改 | `ArticleGeneratorAdm/src/App.vue:1-56` | 侧边栏菜单重组 |
| 修改 | `ArticleGeneratorAdm/src/router/index.ts` | 路由调整：新增 /create + /inspiration，移除 /distill + /generate |
| 修改 | `ArticleGeneratorAdm/src/views/HotspotsView.vue` | 降级为灵感墙（后续 Phase F 深入改造） |

---

### Task 6: 路由 + 导航重组

- [ ] **Step 1: 更新路由配置**

替换 `router/index.ts` 中的路由配置（保留 Tasks/Review/Publish/HotspotSources/Providers/ScenarioConfigs/Accounts 不变，新增 Create 和 Inspiration，移除 Distill 和 Generate）：

```typescript
export const routes: RouteRecordRaw[] = [
  { path: "/", redirect: "/create" },
  { path: "/create", name: "Create", component: () => import("@/views/CreateView.vue"), meta: { title: "文章创作" } },
  { path: "/review", name: "Review", component: () => import("@/views/ReviewView.vue"), meta: { title: "评审队列" } },
  { path: "/publish", name: "Publish", component: () => import("@/views/PublishView.vue"), meta: { title: "文章发布" } },
  { path: "/accounts", name: "Accounts", component: () => import("@/views/AccountsView.vue"), meta: { title: "账号风格" } },
  { path: "/inspiration", name: "Inspiration", component: () => import("@/views/HotspotsView.vue"), meta: { title: "灵感墙" } },
  { path: "/tasks", name: "Tasks", component: () => import("@/views/TasksView.vue"), meta: { title: "任务记录" } },
  { path: "/hotspot-sources", name: "HotspotSources", component: () => import("@/views/HotspotSourcesView.vue"), meta: { title: "热点源管理" } },
  { path: "/providers", name: "Providers", component: () => import("@/views/ProvidersView.vue"), meta: { title: "API供应商" } },
  { path: "/scenario-configs", name: "ScenarioConfigs", component: () => import("@/views/ScenarioConfigsView.vue"), meta: { title: "场景配置" } },
];
```

- [ ] **Step 2: 更新侧边栏菜单**

替换 `App.vue` 中的 `<el-menu>`：

```vue
<el-menu
  :default-active="$route.path"
  router
  background-color="#304156"
  text-color="#bfcbd9"
  active-text-color="#409EFF"
>
  <el-menu-item index="/create">📝 文章创作</el-menu-item>
  <el-menu-item index="/review">📋 评审队列</el-menu-item>
  <el-menu-item index="/publish">📤 文章发布</el-menu-item>
  <el-menu-item index="/accounts">👤 账号风格</el-menu-item>
  <el-menu-item index="/inspiration">💡 灵感墙</el-menu-item>
  <el-menu-item index="/tasks">📋 任务记录</el-menu-item>
  <el-sub-menu index="settings">
    <template #title>⚙️ 系统配置</template>
    <el-menu-item index="/hotspot-sources">热点源管理</el-menu-item>
    <el-menu-item index="/providers">API 供应商</el-menu-item>
    <el-menu-item index="/scenario-configs">场景配置</el-menu-item>
  </el-sub-menu>
</el-menu>
```

- [ ] **Step 3: 解决 import.meta 热更新 (HMR) 边界情况**

Vite 未知模块的 HMR 属于正常行为。路由验证直接通过浏览器操作：
1. 访问 http://localhost:5173 → 应重定向到 /create
2. 点击各菜单项 → 确认路由跳转正常
3. /distill 和 /generate 返回 404（预期行为）

- [ ] **Step 4: Commit**

```bash
git add ArticleGeneratorAdm/src/router/index.ts ArticleGeneratorAdm/src/App.vue
git commit -m "feat: 管理后台导航重组 — 创作页/评审/发布/账号/灵感墙/系统配置"
```

---

### Task 7: 文章创作页骨架 CreateView.vue

- [ ] **Step 1: 创建 CreateView.vue 骨架**

```bash
touch ArticleGeneratorAdm/src/views/CreateView.vue
```

- [ ] **Step 2: 实现多步骤流程骨架**

```vue
<template>
  <div class="create-view">
    <el-steps :active="currentStep" align-center finish-status="success">
      <el-step title="选择账号" />
      <el-step title="输入想法" />
      <el-step title="写作方向" />
      <el-step title="确认大纲" />
      <el-step title="生成全文" />
    </el-steps>

    <div class="step-content">
      <!-- 步骤 1: 选择账号 -->
      <div v-if="currentStep === 0" class="step-panel">
        <h3>选择写作账号</h3>
        <el-select v-model="selectedAccountId" placeholder="请选择账号风格" style="width: 400px" @change="onAccountSelected">
          <el-option
            v-for="acc in accounts"
            :key="acc.id"
            :label="`${acc.account_name} (${acc.platform})`"
            :value="acc.id"
          />
        </el-select>
        <div v-if="selectedAccount" class="account-preview">
          <el-descriptions :column="2" border>
            <el-descriptions-item label="平台">{{ selectedAccount.platform }}</el-descriptions-item>
            <el-descriptions-item label="画像状态">
              <el-tag :type="selectedAccount.style_profile_status === 'ready' ? 'success' : 'info'">
                {{ selectedAccount.style_profile_status === 'ready' ? '已就绪' : '未生成' }}
              </el-tag>
            </el-descriptions-item>
          </el-descriptions>
        </div>
        <el-button type="primary" :disabled="!selectedAccountId" @click="currentStep = 1">
          下一步：输入想法
        </el-button>
      </div>

      <!-- 步骤 2: 输入想法 -->
      <div v-else-if="currentStep === 1" class="step-panel">
        <h3>输入你的创作想法</h3>
        <el-input
          v-model="idea"
          type="textarea"
          :rows="5"
          placeholder="输入你想写的主题或想法，一两句话即可..."
        />
        <div class="step-actions">
          <el-button @click="currentStep = 0">上一步</el-button>
          <el-button type="primary" :disabled="!idea.trim()" @click="generateDirections">
            生成写作方向
          </el-button>
        </div>
      </div>

      <!-- 步骤 3-5 占位（Phase A 实现） -->
      <div v-else class="step-panel">
        <el-empty description="此步骤将在下一阶段实现" />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { api, type Account } from '@/api/client'

const currentStep = ref(0)
const accounts = ref<Account[]>([])
const selectedAccountId = ref<number | null>(null)
const idea = ref('')

const selectedAccount = computed(() =>
  accounts.value.find(a => a.id === selectedAccountId.value) || null
)

function onAccountSelected() {
  // 账号切换时不做额外操作
}

async function generateDirections() {
  // Phase A 实现：调用方向生成 API
  currentStep.value = 2
}

onMounted(async () => {
  try {
    const resp = await api.getAccounts()
    accounts.value = resp.data
    if (accounts.value.length > 0) {
      selectedAccountId.value = accounts.value[0].id
    }
  } catch (e) {
    console.error('加载账号失败', e)
  }
})
</script>

<style scoped>
.create-view {
  max-width: 900px;
  margin: 0 auto;
}
.step-content {
  margin-top: 40px;
}
.step-panel {
  max-width: 600px;
  margin: 0 auto;
}
.step-panel h3 {
  margin-bottom: 20px;
}
.account-preview {
  margin-top: 20px;
}
.step-actions {
  margin-top: 20px;
  display: flex;
  gap: 12px;
}
</style>
```

- [ ] **Step 3: 验证骨架页面**

浏览器访问 http://localhost:5173/create → 确认：
1. 步骤条显示 5 个步骤，当前在"选择账号"
2. 账号下拉可选择
3. 选账号后可点"下一步"进入想法输入
4. 输入文字后"生成写作方向"按钮可点击（跳转到步骤 3 占位）

- [ ] **Step 4: Commit**

```bash
git add ArticleGeneratorAdm/src/views/CreateView.vue
git commit -m "feat: 文章创作页 CreateView 骨架 — 5步骤流程 el-steps + 选账号 + 输入想法"
```

---

## Phase A — 文章创作流程（后续阶段）

### 文件结构

| 操作 | 文件 | 职责 |
|------|------|------|
| 新建 | `ArticleGeneratorService/app/api/directions.py` | 方向生成端点 |
| 修改 | `ArticleGeneratorService/app/api/generate.py` | 全文生成改造：新增 outline 参数 |
| 修改 | `ArticleGeneratorService/app/tasks.py` | 新增方向生成/大纲生成 Celery 任务 |
| 修改 | `ArticleGeneratorService/app/schemas.py` | 新增 DirectionsRequest/OutlineRequest 等 schema |
| 修改 | `ArticleGeneratorService/app/main.py` | 注册新路由 |
| 修改 | `ArticleGeneratorAdm/src/views/CreateView.vue` | 步骤 3-5 完整实现 |
| 新增 | `scenario_configs` 表 rows | `direction` + `outline` 场景配置（通过 seed_providers.py 或管理后台） |

### Task 8-12 概要

**Task 8: 方向生成 API + Celery 任务**
- `POST /api/generate/directions` 端点，接收 `{account_id, idea}`，返回 `{directions: [{id, title}]}`
- Celery 任务 `trigger_direction_generation` 调用 LLM `scenario="direction"`
- System prompt 引用 `thinking_pattern` + `structure_pattern`
- 输出 JSON 数组 `[{id: "1", title: "从个人学编程经历切入..."}]`

**Task 9: 大纲生成 API + Celery 任务**
- `POST /api/generate/outline` 端点，接收 `{account_id, idea, direction}`
- System prompt 引用 `structure_pattern`
- 返回 `{outline: [{order: 1, point: "..."}]}` (5-8 个要点)

**Task 10: 全文生成改造**
- `POST /api/generate/trigger` 新增 `outline: List[str]` 可选字段
- Celery task 将 outline 注入 user_prompt
- System prompt 精确引用画像字段：`{{sentence_pattern}}`、`{{vocabulary_pattern}}`、`{{taboos}}`、`{{blank_leaving}}`

**Task 11: 前端 CreateView 步骤 3-5**
- 步骤 3：方向卡片网格，单选
- 步骤 4：大纲要点列表，可编辑/排序
- 步骤 5：生成进度 + 文章展示 + "提交评审"按钮

**Task 12: 种子数据 — direction + outline 场景配置**
- `scripts/seed_providers.py` 新增两个 scenario
- direction: `deepseek-v4-pro`, temp=0.8
- outline: `deepseek-v4-pro`, temp=0.7

---

## Phase C — 评审微调循环

### 文件结构

| 操作 | 文件 | 职责 |
|------|------|------|
| 新建 | `ArticleGeneratorService/app/api/review_loop.py` | 评审循环端点 (start/continue/stop/status) |
| 修改 | `ArticleGeneratorService/app/tasks.py` | 新增 trigger_unified_review + trigger_auto_refine |
| 修改 | `ArticleGeneratorService/app/schemas.py` | 新增 ReviewResult/ReviewLoopStatus schema |
| 修改 | `ArticleGeneratorService/app/main.py` | 注册新路由 |
| 修改 | `ArticleGeneratorService/app/models.py` | Article 新增 review_loop_round/review_loop_status 字段 |
| 修改 | `ArticleGeneratorAdm/src/views/ReviewView.vue` | 分维度评分展示 + 微调循环控制 |
| 新增 | `scenario_configs` 表 row | `review` 场景配置（合并 quality_review + compliance_review） |

### Task 13-17 概要

**Task 13: 数据库 — Article 新增循环状态字段**
- `ALTER TABLE articles ADD COLUMN review_loop_round INTEGER DEFAULT 0`
- `ALTER TABLE articles ADD COLUMN review_loop_status VARCHAR(20) DEFAULT 'idle'` (idle/reviewing/waiting_confirm/passed/stopped)

**Task 14: 统一评审任务 + 场景配置**
- 新增 `trigger_unified_review` Celery 任务
- 新建 `scenario="review"` 场景，model=`deepseek-v4-pro`
- 输出 JSON: `{total_score, dimensions: {logic, style_match, readability, originality}, comments, refine_instruction}`
- System prompt 引用账号全量结构化画像作为对比基准

**Task 15: 评审循环 API**
- `POST /api/review/start/{article_id}` — 首轮评审
- `POST /api/review/continue/{article_id}` — 执行微调 + 再评审（循环体）
- `POST /api/review/stop/{article_id}` — 手动终止
- `GET /api/review/status/{article_id}` — 当前轮次/评分/历史
- 循环逻辑: `score >= 85? 通过 : 等待用户确认 → 微调 → 再评审`
- 每轮都停，用户必须点"继续"才进入下一轮

**Task 16: 自动微调任务**
- `trigger_auto_refine` Celery 任务
- 从评审结果的 `refine_instruction` + `dimensions` 构造修改指令
- 调用 `scenario="refine"`，传入画像字段
- 每轮结果追加到 `refine_history` JSON

**Task 17: 前端评审页改造**
- 新增"循环状态"列：待评审 / 评审中 / 等待确认 / 已通过 / 已停止
- 评审详情对话框：4 维度评分卡片（≥85 绿/70-84 黄/<70 红）+ 评语 + 修改建议
- 操作按钮：开始评审 / 继续微调 / 加指令后微调 / 停止 / 直接通过

---

## Phase D — URL 输入解析

### Task 18-19 概要

**Task 18: URL 解析端点**
- `POST /api/parse/url` 接收 `{url}`
- 后端用 `httpx` 抓取 URL 内容 → 送 LLM `scenario="url_parse"` → 提取核心论点 + 可反驳点
- 返回 `{title, core_argument, counter_points: [...]}`

**Task 19: 前端集成**
- CreateView 步骤 2 增加 URL 输入框 + "解析"按钮
- 解析结果展示 → 自动带入方向生成

---

## Phase F — 灵感墙

### Task 20 概要

**Task 20: 热点降级为灵感墙**
- HotspotsView.vue 改为卡片式展示
- 移除自动抓取 → 改"手动刷新"
- 每张卡片增加"带入创作"按钮 → 跳转 /create 并自动填入想法

---

## Phase G — 发布辅助

### Task 21-22 概要

**Task 21: 平台格式适配 API**
- `POST /api/articles/{id}/format` 接收 `{platform: "wechat"|"xiaohongshu"|"zhihu"}`
- LLM 根据平台特征生成格式化版本

**Task 22: 前端发布页改造**
- 终稿列表 + 状态追踪
- 复制全文 / 选择平台格式后复制 / 标记已发布

---

## Phase E — 动态风格进化

### Task 23-25 概要

**Task 23: 反馈收集**
- 通过文章的分维度评分自动记录到画像进化数据

**Task 24: 画像进化计算**
- 新增 `trigger_style_evolution` Celery 任务
- 累积 5 篇通过后触发 → 计算各维度调整建议
- 存入 `style_profile_structured.suggested_updates`

**Task 25: 前端进化提示**
- 账号列表显示"有更新建议"标记
- diff 式对比（旧值 → 新值），逐项确认/拒绝
- 手动"重新蒸馏"按钮

---

## 附加修复项

| 事项 | 穿插时机 | 说明 |
|------|---------|------|
| `humanize` 场景配置缺失 | Phase A 前 | `seed_providers.py` 新增 humanize 行 |
| Celery humanize chain 调度 bug | Phase A 前 | `tasks.py` chain 回调修复 |
| 前端轮询清理 (`onUnmounted`) | Phase H/A | `setInterval` 加清理逻辑 |
| 删除 `LLMService/app/generator.py` 死代码 | 任意 | 未被调用的 mock 函数 |
| 前端组件抽取（文章查看/编辑对话框） | Phase H | 抽取为 `components/ArticleDialog.vue` |

---

## 验证策略

每个 Phase 完成后执行以下检查：

1. **后端 API 测试**：`cd ArticleGeneratorService && pytest tests/ -v`（确保无回归）
2. **前端编译检查**：`cd ArticleGeneratorAdm && npx vue-tsc --noEmit`（TypeScript 类型检查）
3. **端到端验证**：浏览器手动走通当前阶段实现的用户流程
4. **Git commit**：每个 Task 完成后 commit，保持小步提交
